"""
Email provider.
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from email.message import EmailMessage

import aiosmtplib
import httpx
from bs4 import BeautifulSoup
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from quart import Blueprint, Response, current_app, render_template, session
from quart.helpers import make_response, redirect, url_for
from quart_schema import validate_querystring

from robida.blueprints.auth.providers.base import Provider

blueprint = Blueprint("email", __name__, url_prefix="/relmeauth/email")


async def send_email(email: str, subject: str, body: str) -> None:
    """
    Send an email.
    """
    message = EmailMessage()
    message["From"] = current_app.config["SMTP_FROM"]
    message["To"] = email
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=current_app.config["SMTP_HOSTNAME"],
        port=int(current_app.config["SMTP_PORT"]),
        username=current_app.config["SMTP_USERNAME"],
        password=current_app.config["SMTP_PASSWORD"],
    )


def get_profile(html: str) -> str | None:
    """
    Get email from profile.
    """
    soup = BeautifulSoup(html, "html.parser")
    element = soup.find("a", rel="me", href=re.compile("^mailto:"))
    profile = element["href"] if element else None

    return profile


@dataclass
class TokenRequest:
    """
    Token request.
    """

    token: str


class EmailProvider(Provider):
    """
    Email-based authentication.
    """

    name = "Email"
    description = (
        'Login with your email. Requires a <code>rel="me"</code> link on your site '
        "pointing to your email address."
    )

    blueprint = blueprint
    login_endpoint = f"{blueprint.name}.login"

    @classmethod
    async def match(cls, me: str, client: httpx.AsyncClient) -> EmailProvider | None:
        """
        Match emails.
        """
        try:
            response = await client.get(me)
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return None

        profile = get_profile(response.text)
        if profile is None:
            return None

        return cls(me, profile)

    def get_scope(self) -> dict[str, str | None]:
        return {
            "relmeauth.email.me": self.me,
            "relmeauth.email.address": urllib.parse.urlparse(self.profile).path,
        }


@blueprint.route("/login", methods=["GET"])
async def login() -> Response:
    """
    Login with email.
    """
    email = session["relmeauth.email.address"]

    # create token
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    token = serializer.dumps(email, salt="email-login")
    link = url_for("email.verify", token=token, _external=True)

    # create email
    subject = f'Login to {current_app.config["SITE_NAME"]}'
    body = f"Please click the link below to login to the site.\n\n{link}"

    await send_email(email, subject, body)

    return await render_template("relmeauth/email.html", email=email)


@blueprint.route("/verify", methods=["GET"])
@validate_querystring(TokenRequest)
async def verify(query_args: TokenRequest) -> Response:
    """
    Verify token from email.
    """
    serializer = URLSafeTimedSerializer(current_app.secret_key)

    try:
        email = serializer.loads(query_args.token, salt="email-login", max_age=3600)
    except SignatureExpired:
        return await make_response("Token expired", 400)
    except BadSignature:
        return await make_response("Invalid token", 400)

    if email != session["relmeauth.email.address"]:
        return await make_response("Invalid email", 400)

    session["me"] = session["relmeauth.email.me"]

    if next_ := session.pop("next", None):
        return redirect(next_)

    return redirect(url_for("homepage.index"))
