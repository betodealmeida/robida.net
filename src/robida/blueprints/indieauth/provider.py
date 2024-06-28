"""
IndieAuth provider.
"""

from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup
from quart import Blueprint, Response, session
from quart.helpers import make_response, redirect, url_for
from quart_schema import validate_querystring

from robida.blueprints.auth.providers.base import Provider
from robida.blueprints.wellknown.models import ServerMetadataResponse
from robida.helpers import compute_challenge

blueprint = Blueprint("indieauth_client", __name__, url_prefix="/auth/indieauth")


@dataclass
class AuthorizationResponse:
    """
    Authorization response from the IndieAuth server.
    """

    code: str
    state: str
    iss: str


async def get_server_metadata(
    metadata_endpoint: str,
    client: httpx.AsyncClient,
) -> ServerMetadataResponse | None:
    """
    Get the authorization endpoint from the metadata endpoint.
    """
    try:
        response = await client.get(metadata_endpoint)
        response.raise_for_status()
    except httpx.HTTPStatusError:
        return None

    try:
        payload = response.json()
    except json.decoder.JSONDecodeError:
        return None

    return ServerMetadataResponse(**payload)


class IndieAuthProvider(Provider):
    """
    IndieAuth provider.

    This allows users to login to the website using IndieAuth in their sites.

    https://indieauth.spec.indieweb.org/
    """

    name = "IndieAuth"
    description = 'Login using <a href="https://indieweb.org/IndieAuth">IndieAuth</a>.'

    blueprint = blueprint
    login_endpoint = f"{blueprint.name}.login"

    @classmethod
    # pylint: disable=too-many-return-statements
    async def match(
        cls,
        me: str,
        client: httpx.AsyncClient,
    ) -> IndieAuthProvider | None:
        """
        Try to find an IndieAuth provider for the given URL.

        https://indieauth.spec.indieweb.org/#discovery-by-clients
        """
        # We can't use IndieAuth to login ourselves, since we need to be logged in to use
        # our IndieAuth endpoint.
        if me == url_for("homepage.index", _external=True):
            return None

        try:
            response = await client.head(me)
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return None

        if link := response.links.get("indieauth-metadata"):
            return await cls.from_metadata(me, link["url"], client)

        try:
            response = await client.get(me)
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        if element := soup.find("link", rel="indieauth-metadata"):
            return await cls.from_metadata(me, element["href"], client)

        # try `authorization_endpoint` for compatibility with previous revisions
        if link := response.links.get("authorization_endpoint"):
            return cls(me, link["url"])

        if element := soup.find("link", rel="authorization_endpoint"):
            return cls(me, element["href"])

        return None

    @classmethod
    async def from_metadata(
        cls,
        me: str,
        metadata_endpoint: str,
        client: httpx.AsyncClient,
    ) -> IndieAuthProvider | None:
        """
        Build provider from the metadata response.
        """
        server_metadata = await get_server_metadata(metadata_endpoint, client)
        if not server_metadata:
            return None

        # "The identifier MUST be a prefix of the indieauth-metadata URL."
        if not metadata_endpoint.startswith(str(server_metadata.issuer)):
            return None

        scope = (
            "profile"
            if server_metadata.scopes_supported
            and "profile" in server_metadata.scopes_supported
            else None
        )

        # use PKCE if possible
        supported_methods = set(server_metadata.code_challenge_methods_supported)
        for method in ["S256", "plain"]:
            if method in supported_methods:
                code_challenge_method = method
                break
        else:
            code_challenge_method = None

        return cls(
            me,
            str(server_metadata.authorization_endpoint),
            scope,
            code_challenge_method,
        )

    def __init__(
        self,
        me: str,
        profile: str,
        scope: str | None = None,
        code_challenge_method: str | None = None,
    ) -> None:
        self.scope = scope
        self.code_challenge_method = code_challenge_method

        super().__init__(me, profile)

    def get_scope(self) -> dict[str, str | None]:
        """
        Store scope for verification.
        """

        return {
            "indieauth.client.me": self.me,
            "indieauth.client.authorization_endpoint": self.profile,
            "indieauth.client.state": uuid4().hex,
            "indieauth.client.scope": self.scope,
            "indieauth.client.code_verifier": uuid4().hex,
            "indieauth.client.code_challenge_method": self.code_challenge_method,
        }


@blueprint.route("/login", methods=["GET"])
async def login() -> Response:
    """
    IndieAuth login endpoint.
    """
    query = {
        "response_type": "code",
        "client_id": url_for("homepage.index", _external=True),
        "redirect_uri": url_for("indieauth_client.callback", _external=True),
        "state": session["indieauth.client.state"],
        "me": session["indieauth.client.me"],
    }

    # ask for the `profile` scope if available
    if session["indieauth.client.scope"]:
        query["scope"] = session["indieauth.client.scope"]

    # use PKCE if possible
    if session["indieauth.client.code_challenge_method"]:
        code_challenge = compute_challenge(
            session["indieauth.client.code_verifier"],
            session["indieauth.client.code_challenge_method"],
        )
        query["code_challenge"] = code_challenge
        query["code_challenge_method"] = session[
            "indieauth.client.code_challenge_method"
        ]

    url = urllib.parse.urlparse(
        session["indieauth.client.authorization_endpoint"]
    )._replace(query=urllib.parse.urlencode(query))

    return redirect(url.geturl())


@blueprint.route("/callback", methods=["GET"])
@validate_querystring(AuthorizationResponse)
async def callback(query_args: AuthorizationResponse) -> Response:
    """
    Receive the authorization code and exchange it for an access token.
    """
    data = {
        "grant_type": "authorization_code",
        "code": query_args.code,
        "client_id": url_for("homepage.index", _external=True),
        "redirect_uri": url_for("indieauth_client.callback", _external=True),
    }

    # use PKCE if possible
    if session["indieauth.client.code_challenge_method"]:
        data["code_verifier"] = session["indieauth.client.code_verifier"]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            session["indieauth.client.authorization_endpoint"],
            data=data,
        )
        response.raise_for_status()
        payload = response.json()

    if payload.get("me") != session["indieauth.client.me"]:
        return await make_response("Unauthorized", 401)

    session["me"] = session["indieauth.client.me"]

    if next_ := session.pop("next", None):
        return redirect(next_)

    return redirect(url_for("homepage.index"))
