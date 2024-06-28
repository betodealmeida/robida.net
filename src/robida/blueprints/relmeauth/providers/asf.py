"""
Apache Software Foundation (ASF) OAuth provider
"""

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

blueprint = Blueprint("asf", __name__, url_prefix="/relmeauth/asf")

PEOPLE_URL = "https://home.apache.org/public/public_ldap_people.json"


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


def is_phonebook_url(href: str) -> bool:
    """
    Check if the URL is the ASF phonebook.
    """
    parsed = urllib.parse.urlparse(href)
    return (
        parsed.netloc == "home.apache.org"
        and parsed.path == "/phonebook.html"
        and "uid" in urllib.parse.parse_qs(parsed.query)
    )


def get_profile(html: str) -> str | None:
    """
    Get the profile URL from the response.
    """
    soup = BeautifulSoup(html, "html.parser")
    element = soup.find("a", rel="me", href=is_phonebook_url)
    profile = element["href"] if element else None

    return profile


class ASFProvider(Provider):
    """
    Apache Software Foundation (ASF) OAuth provider

    https://oauth.apache.org/api.html
    """

    name = "Apache Software Foundation phonebook"
    description = (
        'For <abbr title="Apache Software Foundation" data-tooltip="Apache Software '
        'Foundation">ASF</abbr> committers. Requires a <code>rel="me"</code> link on '
        'your site pointing to your entry in the <abbr title="Apache Software Foundation" '
        'data-tooltip="Apache Software Foundation">ASF</abbr> '
        '<a href="https://home.apache.org/phonebook.html">phonebook</a>.'
    )

    blueprint = blueprint
    login_endpoint = f"{blueprint.name}.login"

    @classmethod
    # pylint: disable=too-many-return-statements
    async def match(cls, me: str, client: httpx.AsyncClient) -> Provider | None:
        """
        Match `rel="me"` links pointing to the ASF phonebook.

        https://home.apache.org/phonebook.html?uid=beto
        """
        try:
            response = await client.get(me)
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return None

        profile = get_profile(response.text)
        if profile is None:
            return None

        parsed = urllib.parse.urlparse(profile)
        uid = urllib.parse.parse_qs(parsed.query)["uid"][0]

        # check that UID is valid and links back
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(PEOPLE_URL)
                response.raise_for_status()
            except httpx.HTTPStatusError:
                return None

        try:
            payload = response.json()
        except json.decoder.JSONDecodeError:
            return None

        try:
            urls = payload["people"][uid]["urls"]
        except KeyError:
            return None

        if me not in urls:
            return None

        return cls(me, profile)

    def get_scope(self) -> dict[str, str | None]:
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
