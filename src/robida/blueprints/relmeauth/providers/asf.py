"""
Apache Software Foundation (ASF) OAuth provider
"""

import urllib.parse
from dataclasses import dataclass
from uuid import uuid4

import httpx
from quart import Blueprint, Response, session
from quart.helpers import make_response, redirect, url_for
from quart_schema import validate_querystring

from .base import Provider


blueprint = Blueprint("asf", __name__, url_prefix="/relmeauth/asf")


@dataclass
class CodeRequest:
    """
    Code request.
    """

    code: str


@dataclass
class ProfileResponse:  # pylint: disable=too-many-instance-attributes
    """
    The response with the profile content.
    """

    # pylint: disable=invalid-name
    uid: str
    email: str
    fullname: str
    isMember: bool
    isChair: bool
    isRoot: bool
    projects: list[str]
    pmcs: list[str]
    state: str


class ASFProvider(Provider):
    """
    Apache Software Foundation (ASF) OAuth provider

    https://oauth.apache.org/api.html
    """

    blueprint = blueprint
    login_endpoint = f"{blueprint.name}.login"

    @classmethod
    def match(cls, url: str) -> bool:
        """
        Match `rel="me"` links pointing to the ASF phonebook.

        https://home.apache.org/phonebook.html?uid=beto
        """
        parsed = urllib.parse.urlparse(url)

        return (
            parsed.netloc == "home.apache.org"
            and parsed.path == "/phonebook.html"
            and "uid" in urllib.parse.parse_qs(parsed.query)
        )

    def get_scope(self) -> dict[str, str]:
        """
        Store scope for verification.
        """
        parsed = urllib.parse.urlparse(self.profile)

        return {
            "relmeauth.asf.me": self.me,
            "relmeauth.asf.url": self.profile,
            "relmeauth.asf.uid": urllib.parse.parse_qs(parsed.query)["uid"][0],
            "relmeauth.asf.state": uuid4().hex,
        }


@blueprint.route("/login", methods=["GET"])
async def login() -> Response:
    """
    Redirect to ASF for authentication.
    """
    query = urllib.parse.urlencode(
        {
            "redirect_uri": url_for("asf.callback", _external=True),
            "state": session["relmeauth.asf.state"],
        },
    )
    url = urllib.parse.urlparse("https://oauth.apache.org/auth")._replace(query=query)

    return redirect(url.geturl())


@blueprint.route("/callback", methods=["GET"])
@validate_querystring(CodeRequest)
async def callback(query_args: CodeRequest) -> Response:
    """
    Receive the authorization code and exchange it for an access token.
    """
    query = urllib.parse.urlencode({"code": query_args.code})
    url = urllib.parse.urlparse("https://oauth.apache.org/token")._replace(query=query)

    async with httpx.AsyncClient() as client:
        response = await client.get(url.geturl())
        payload = response.json()

    profile = ProfileResponse(**payload)

    if (
        profile.uid != session["relmeauth.asf.uid"]
        or profile.state != session["relmeauth.asf.state"]
    ):
        return await make_response("Unauthorized", 401)

    session["me"] = session["relmeauth.asf.me"]

    if next_ := session.pop("next", None):
        return redirect(next_)

    return redirect(url_for("homepage.index"))
