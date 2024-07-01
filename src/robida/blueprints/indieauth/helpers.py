"""
Helper functions.
"""

import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from typing import Any
from collections.abc import Callable

import httpx
import mf2py
from bs4 import BeautifulSoup
from quart import Response, current_app, g, make_response

from robida.db import get_db
from robida.helpers import compute_s256_challenge


VERIFICATION_METHODS = {
    "S256": compute_s256_challenge,
}


@dataclass
class ClientInfo:
    """
    Dataclass to store information about the IndieAuth client.
    """

    url: str
    name: str
    logo: str | None
    summary: str | None
    author: str | None
    redirect_uris: set[str]


async def get_client_info(client_id: str) -> ClientInfo:
    """
    Get information about the IndieAuth client.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(client_id)
        html = response.text

    app_info: dict[str, list[Any]] = {
        "name": [client_id],
        "url": [""],
        "logo": [None],
        "summary": [None],
        "author": [None],
    }
    metadata = mf2py.parse(html, url=client_id)
    for item in metadata["items"]:
        if "h-app" in item["type"] or "h-x-app" in item["type"]:
            app_info.update(item["properties"])
            break

    name = app_info["name"][0]

    logo = None
    if property_ := app_info["logo"][0]:
        logo = property_.get("value") if isinstance(property_, dict) else property_

    summary = None
    if property_ := app_info["summary"][0]:
        summary = property_.get("value") if isinstance(property_, dict) else property_

    author = None
    if property_ := app_info["author"][0]:
        author = property_.get("value") if isinstance(property_, dict) else property_

    # find redirect URIs
    redirect_uris = {
        link["url"] for link in response.links.values() if link["rel"] == "redirect_uri"
    }

    soup = BeautifulSoup(html, "html.parser")
    redirect_uris.update(
        link["href"] for link in soup.find_all("link", rel="redirect_uri")
    )

    return ClientInfo(
        url=client_id,
        name=name,
        logo=logo,
        summary=summary,
        author=author,
        redirect_uris=redirect_uris,
    )


def redirect_match(url1: str, url2: str) -> bool:
    """
    Check two URLs share the same scheme, hostname, and port.

    From the spec:

        If the URL scheme, host or port of the redirect_uri in the request do not match
        that of the client_id, then the authorization endpoint SHOULD verify that the
        requested redirect_uri matches one of the redirect URLs published by the client,
        and SHOULD block the request from proceeding if not.

    """
    parsed1 = urllib.parse.urlparse(url1)
    parsed2 = urllib.parse.urlparse(url2)
    return (
        parsed1.scheme == parsed2.scheme
        and parsed1.hostname == parsed2.hostname
        and parsed1.port == parsed2.port
    )


def verify_code_challenge(
    code_challenge: str | None,
    code_challenge_method: str | None,
    code_verifier: str | None,
) -> bool:
    """
    PKCE verification.

    "If a `code_challenge` is provided in an authorization request, don't allow the
    authorization code to be used unless the corresponding `code_verifier` is present in
    the request using the authorization code. For backwards compatibility, if no
    `code_challenge` is provided in the request, make sure the request to use the
    authorization code does not contain a `code_verifier`."
    """
    if code_challenge is None:
        return code_verifier is None

    if code_verifier is None or code_challenge_method is None:
        return False

    verification_method = VERIFICATION_METHODS.get(code_challenge_method)
    if verification_method is None:
        return False

    return code_challenge == verification_method(code_verifier)


async def get_scopes(token: str | None) -> set[str]:
    """
    Return all scopes for a given token.
    """
    if not token:
        return set()

    async with get_db(current_app) as db:
        async with db.execute(
            """
SELECT
    scope
FROM
    oauth_tokens
WHERE
    access_token = ? AND
    expires_at > ?
            """,
            (token, datetime.now(timezone.utc)),
        ) as cursor:
            row = await cursor.fetchone()

    return set(row["scope"].split(" ")) if row else set()


def requires_scope(
    *required_scopes: str,
) -> Callable[[Callable[..., Response]], Callable[..., Response]]:
    """
    Decorator that checks if the request has the required scope.
    """

    def decorator(f: Callable[..., Response]) -> Callable[..., Response]:
        @wraps(f)
        async def decorated_function(*args: Any, **kwargs: Any) -> Response:
            available_scopes = await get_scopes(g.access_token)
            if not available_scopes:
                return await make_response("invalid_token", 401)

            if not set(required_scopes) <= available_scopes:
                return await make_response("insufficient_scope", 403)

            return await f(*args, **kwargs)

        return decorated_function

    return decorator
