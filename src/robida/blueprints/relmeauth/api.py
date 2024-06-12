"""
RelMeAuth implementation.

https://microformats.org/wiki/RelMeAuth
"""

from quart import Blueprint, Response, render_template, session
from quart.helpers import make_response
from quart_schema import DataSource, validate_request

from .helpers import get_profiles
from .models import LoginRequest
from .providers.asf import ASFProvider
from .providers.email import EmailProvider

blueprint = Blueprint("relmeauth", __name__, url_prefix="/")

providers = [
    ASFProvider,
    EmailProvider,
]


@blueprint.route("/login", methods=["GET"])
async def login() -> Response:
    """
    Show a login form.
    """
    return await render_template("relmeauth/login.html")


@blueprint.route("/logout", methods=["GET"])
async def logout() -> Response:
    """
    Logout the user.
    """
    session.pop("me", None)
    return await render_template("relmeauth/login.html")


@blueprint.route("/login", methods=["POST"])
@validate_request(LoginRequest, source=DataSource.FORM)
async def submit(data: LoginRequest) -> Response:
    """
    Process the login form.

    This endpoint receives the `me` parameter, and tries to find a link in the page that
    has a `rel="me"` attribute supported by one of the providers.
    """
    profiles = await get_profiles(data.me)

    for provider in providers:
        for profile in profiles:
            if provider.match(profile):
                return provider(data.me, profile).login()

    return await make_response("No provider found", 400)
