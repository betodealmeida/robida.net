"""
RelMeAuth implementation.

https://microformats.org/wiki/RelMeAuth
"""

import httpx
from quart import Blueprint, Response, render_template, session
from quart.helpers import make_response, redirect, url_for
from quart_schema import DataSource, validate_request

from robida.blueprints.relmeauth.providers.asf import ASFProvider
from robida.blueprints.relmeauth.providers.email import EmailProvider

from .models import LoginRequest

blueprint = Blueprint("auth", __name__, url_prefix="/")

providers = [
    ASFProvider,
    EmailProvider,
]


@blueprint.route("/login", methods=["GET"])
async def login() -> Response:
    """
    Show a login form.
    """
    return await render_template("auth/login.html", providers=providers)


@blueprint.route("/logout", methods=["GET"])
async def logout() -> Response:
    """
    Logout the user.
    """
    session.pop("me", None)
    return redirect(url_for("homepage.index"))


@blueprint.route("/login", methods=["POST"])
@validate_request(LoginRequest, source=DataSource.FORM)
async def submit(data: LoginRequest) -> Response:
    """
    Process the login form.

    This endpoint receives the `me` parameter, and tries to find a link in the page that
    has a `rel="me"` attribute supported by one of the providers.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(data.me)
        response.raise_for_status()

    for provider in providers:
        if provider.match(response):
            return provider(data.me, response).login()

    return await make_response("No provider found", 400)
