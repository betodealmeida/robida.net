"""
Tests for the email provider.
"""

# pylint: disable=redefined-outer-name, invalid-name

import httpx
from itsdangerous import SignatureExpired, BadSignature
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture
from quart import Quart, session, testing

from robida.blueprints.relmeauth.providers.email import EmailProvider, send_email


async def test_email_provider_match(httpx_mock: HTTPXMock, current_app: Quart) -> None:
    """
    Test the Email provider `match` method.
    """
    httpx_mock.add_response(
        url="https://me.example.com/",
        html='<a rel="me" href="mailto:me@example.com">me</a>',
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://invalid.example.com",
        html='<a href="mailto:me@example.com">me</a>',
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://error.example.com",
        status_code=400,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert await EmailProvider.match("https://me.example.com/", client)
            assert not await EmailProvider.match("https://invalid.example.com", client)
            assert not await EmailProvider.match("https://error.example.com", client)


async def test_email_provider(current_app: Quart) -> None:
    """
    Test the Email provider.
    """
    async with current_app.test_request_context("/", method="GET"):
        provider = EmailProvider(
            "https://me.example.com/",
            "mailto:me@example.com",
        )

        response = provider.login()
        assert response.status_code == 302
        assert response.headers["Location"] == "/relmeauth/email/login"

        assert session["relmeauth.email.me"] == "https://me.example.com/"
        assert session["relmeauth.email.address"] == "me@example.com"

    assert current_app.blueprints["email"] == provider.blueprint


async def test_email_provider_login(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
) -> None:
    """
    Test the Email provider login.
    """
    send_email = mocker.patch("robida.blueprints.relmeauth.providers.email.send_email")
    URLSafeTimedSerializer = mocker.patch(
        "robida.blueprints.relmeauth.providers.email.URLSafeTimedSerializer"
    )
    URLSafeTimedSerializer().dumps.return_value = "XXX"

    async with current_app.app_context():
        EmailProvider.register()

    mocker.patch(
        "robida.blueprints.relmeauth.providers.email.session",
        new={"relmeauth.email.address": "me@example.com"},
    )

    response = await client.get("/relmeauth/email/login")

    assert response.status_code == 200
    send_email.assert_called_with(
        "me@example.com",
        "Login to Robida",
        "Please click the link below to login to the site.\n\n"
        "http://example.com/relmeauth/email/verify?token=XXX",
    )


async def test_email_provider_callback(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
) -> None:
    """
    Test the Email callback request.
    """
    async with current_app.app_context():
        EmailProvider.register()

    session = {
        "relmeauth.email.me": "https://me.example.com/",
        "relmeauth.email.address": "me@example.com",
    }

    mocker.patch(
        "robida.blueprints.relmeauth.providers.email.session",
        new=session,
    )
    URLSafeTimedSerializer = mocker.patch(
        "robida.blueprints.relmeauth.providers.email.URLSafeTimedSerializer"
    )
    URLSafeTimedSerializer().loads.return_value = "me@example.com"

    response = await client.get(
        "/relmeauth/email/verify",
        query_string={"token": "12345"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert session["me"] == "https://me.example.com/"


async def test_email_provider_callback_next(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
) -> None:
    """
    Test the Email callback request when `next` is set in the session.
    """
    async with current_app.app_context():
        EmailProvider.register()

    session = {
        "relmeauth.email.me": "https://me.example.com/",
        "relmeauth.email.address": "me@example.com",
        "next": "/continue",
    }

    mocker.patch(
        "robida.blueprints.relmeauth.providers.email.session",
        new=session,
    )
    URLSafeTimedSerializer = mocker.patch(
        "robida.blueprints.relmeauth.providers.email.URLSafeTimedSerializer"
    )
    URLSafeTimedSerializer().loads.return_value = "me@example.com"

    response = await client.get(
        "/relmeauth/email/verify",
        query_string={"token": "12345"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/continue"
    assert session["me"] == "https://me.example.com/"


async def test_email_provider_callback_invalid_email(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
) -> None:
    """
    Test the Email callback request when the email doesn't match.
    """
    async with current_app.app_context():
        EmailProvider.register()

    session = {
        "relmeauth.email.me": "https://me.example.com/",
        "relmeauth.email.address": "me@example.com",
    }

    mocker.patch(
        "robida.blueprints.relmeauth.providers.email.session",
        new=session,
    )
    URLSafeTimedSerializer = mocker.patch(
        "robida.blueprints.relmeauth.providers.email.URLSafeTimedSerializer"
    )
    URLSafeTimedSerializer().loads.return_value = "alice@example.com"

    response = await client.get(
        "/relmeauth/email/verify",
        query_string={"token": "12345"},
    )

    assert response.status_code == 400
    assert await response.get_data() == b"Invalid email"
    assert "me" not in session


async def test_email_provider_callback_expired_token(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
) -> None:
    """
    Test the Email callback request when the token expired.
    """
    async with current_app.app_context():
        EmailProvider.register()

    session = {
        "relmeauth.email.me": "https://me.example.com/",
        "relmeauth.email.address": "me@example.com",
    }

    mocker.patch(
        "robida.blueprints.relmeauth.providers.email.session",
        new=session,
    )
    URLSafeTimedSerializer = mocker.patch(
        "robida.blueprints.relmeauth.providers.email.URLSafeTimedSerializer"
    )
    URLSafeTimedSerializer().loads.side_effect = SignatureExpired("Token expired")

    response = await client.get(
        "/relmeauth/email/verify",
        query_string={"token": "12345"},
    )

    assert response.status_code == 400
    assert await response.data == b"Token expired"
    assert "me" not in session


async def test_email_provider_callback_invalid_token(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
) -> None:
    """
    Test the Email callback request when the token is invalid.
    """
    async with current_app.app_context():
        EmailProvider.register()

    session = {
        "relmeauth.email.me": "https://me.example.com/",
        "relmeauth.email.address": "me@example.com",
    }
    mocker.patch(
        "robida.blueprints.relmeauth.providers.email.session",
        new=session,
    )
    URLSafeTimedSerializer = mocker.patch(
        "robida.blueprints.relmeauth.providers.email.URLSafeTimedSerializer"
    )
    URLSafeTimedSerializer().loads.side_effect = BadSignature("Invalid token")

    response = await client.get(
        "/relmeauth/email/verify",
        query_string={"token": "12345"},
    )

    assert response.status_code == 400
    assert await response.data == b"Invalid token"
    assert "me" not in session


async def test_send_email(mocker: MockerFixture, current_app: Quart) -> None:
    """
    Test the send_email function.
    """
    aiosmtplib = mocker.AsyncMock()
    mocker.patch("robida.blueprints.relmeauth.providers.email.aiosmtplib", aiosmtplib)
    EmailMessage = mocker.patch(
        "robida.blueprints.relmeauth.providers.email.EmailMessage"
    )

    async with current_app.app_context():
        await send_email("me@example.com", "Subject", "Body")

    aiosmtplib.send.assert_called_with(
        EmailMessage(),
        hostname="mail.example.com",
        port=587,
        username="noreply",
        password="XXX",
    )
