"""
Helper functions.
"""

import base64
import hashlib
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable

import httpx
import mf2py
from bs4 import BeautifulSoup
from quart import Response, current_app, g, make_response

from robida.db import get_db


VERIFICATION_METHODS = {
    "S256": hashlib.sha256,
}


@dataclass
class ClientInfo:
    """
    Dataclass to store information about the IndieAuth client.
    """

    name: str
    url: str
    image: str | None
    redirect_uris: set[str]


async def get_client_info(client_id: str) -> ClientInfo:
    """
    Get information about the IndieAuth client.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(client_id)
        html = response.text

    app_info = {}
    metadata = mf2py.parse(doc=html)
    for item in metadata["items"]:
        if "h-app" in item["type"]:
            app_info = item["properties"]
            break

    name = app_info.get("name", [client_id])[0]
    url = urllib.parse.urljoin(client_id, app_info.get("url", [""])[0])
    image = None
    if logo := app_info.get("logo"):
        image = logo[0].get("value") if isinstance(image, dict) else logo[0]
        image = urllib.parse.urljoin(client_id, image)

    # find redirect URIs
    redirect_uris = {
        link["url"] for link in response.links.values() if link["rel"] == "redirect_uri"
    }

    soup = BeautifulSoup(html, "html.parser")
    redirect_uris.update(
        urllib.parse.urljoin(client_id, link["href"])
        for link in soup.find_all("link", rel="redirect_uri")
    )

    return ClientInfo(name=name, url=url, image=image, redirect_uris=redirect_uris)


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
    code_challenge: str,
    code_challenge_method: str,
    code_verifier: str,
) -> bool:
    """
    PKCE verification.
    """
    verification_method = VERIFICATION_METHODS.get(code_challenge_method)
    if verification_method is None:
        return False

    digest = verification_method(code_verifier.encode("utf-8")).digest()
    encoded = base64.urlsafe_b64encode(digest)
    calculated_challenge = encoded.rstrip(b"=").decode("utf-8")

    return code_challenge == calculated_challenge


async def get_scopes(token: str | None) -> set[str]:
    """
    Return all scopes for a given token.
    """
    if not token:
        return set()

    async with get_db(current_app) as db:
        async with db.execute(
            "SELECT scope FROM oauth_tokens WHERE access_token = ? AND expires_at > ?",
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
