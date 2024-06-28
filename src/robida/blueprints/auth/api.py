"""
RelMeAuth implementation.

https://microformats.org/wiki/RelMeAuth
"""

from typing import Type

import httpx
from quart import Blueprint, Response, render_template, session
from quart.helpers import make_response, redirect, url_for
from quart_schema import DataSource, validate_request

from robida.blueprints.auth.providers.base import Provider
from robida.blueprints.indieauth.provider import IndieAuthProvider
from robida.blueprints.relmeauth.providers.asf import ASFProvider
from robida.blueprints.relmeauth.providers.email import EmailProvider
from robida.helpers import canonicalize_url

from .models import LoginRequest

blueprint = Blueprint("auth", __name__, url_prefix="/")

providers: list[Type[Provider]] = [
    ASFProvider,
    EmailProvider,
    IndieAuthProvider,
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
    me = canonicalize_url(data.me)

    async with httpx.AsyncClient() as client:
        for class_ in providers:
            if provider := await class_.match(me, client):
                return provider.login()

    return await make_response("No provider found", 400)
