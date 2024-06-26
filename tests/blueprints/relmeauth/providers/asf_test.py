"""
Tests for the ASF provider.
"""

# pylint: disable=redefined-outer-name

from uuid import UUID

import httpx
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture
from quart import Quart, session, testing

from robida.blueprints.relmeauth.providers.asf import ASFProvider


async def test_asf_provider_match(
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the ASF provider `match` method.
    """
    httpx_mock.add_response(
        url="https://me.example.com",
        html='<a rel="me" href="https://home.apache.org/phonebook.html?uid=me">me</a>',
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://invalid.example.com",
        html='<a href="https://home.apache.org/phonebook.html?uid=me">me</a>',
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://error.example.com",
        status_code=400,
    )
    httpx_mock.add_response(
        url="https://home.apache.org/public/public_ldap_people.json",
        json={
            "people": {
                "me": {
                    "uid": "me",
                    "urls": ["https://me.example.com"],
                },
            },
        },
        status_code=200,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert await ASFProvider.match("https://me.example.com", client)
            assert not await ASFProvider.match("https://invalid.example.com", client)
            assert not await ASFProvider.match("https://error.example.com", client)


async def test_asf_provider(mocker: MockerFixture, current_app: Quart) -> None:
    """
    Test the ASF provider.
    """
    mocker.patch(
        "robida.blueprints.relmeauth.providers.asf.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )

    async with current_app.test_request_context("/", method="GET"):
        provider = ASFProvider(
            "https://me.example.com",
            "https://home.apache.org/phonebook.html?uid=me",
        )

        response = provider.login()
        assert response.status_code == 302
        assert response.headers["Location"] == "/relmeauth/asf/login"

        assert session["relmeauth.asf.me"] == "https://me.example.com"
        assert (
            session["relmeauth.asf.url"]
            == "https://home.apache.org/phonebook.html?uid=me"
        )
        assert session["relmeauth.asf.uid"] == "me"
        assert session["relmeauth.asf.state"] == "92cdeabd827843ad871d0214dcb2d12e"

    assert current_app.blueprints["asf"] == provider.blueprint


async def test_asf_provider_no_people(
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the ASF provider when the people endpoint fails.
    """
    httpx_mock.add_response(
        url="https://me.example.com",
        html='<a rel="me" href="https://home.apache.org/phonebook.html?uid=me">me</a>',
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://home.apache.org/public/public_ldap_people.json",
        status_code=400,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert not await ASFProvider.match("https://me.example.com", client)


async def test_asf_provider_not_json(
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the ASF provider when the people endpoint is not JSON.
    """
    httpx_mock.add_response(
        url="https://me.example.com",
        html='<a rel="me" href="https://home.apache.org/phonebook.html?uid=me">me</a>',
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://home.apache.org/public/public_ldap_people.json",
        html="<html></html>",
        status_code=200,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert not await ASFProvider.match("https://me.example.com", client)


async def test_asf_provider_no_user(
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the ASF provider when the people endpoint doesn't have the user.
    """
    httpx_mock.add_response(
        url="https://me.example.com",
        html='<a rel="me" href="https://home.apache.org/phonebook.html?uid=me">me</a>',
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://home.apache.org/public/public_ldap_people.json",
        json={"people": {}},
        status_code=200,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert not await ASFProvider.match("https://me.example.com", client)


async def test_asf_provider_no_url(
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the ASF provider when the people endpoint doesn't have the URL.
    """
    httpx_mock.add_response(
        url="https://me.example.com",
        html='<a rel="me" href="https://home.apache.org/phonebook.html?uid=me">me</a>',
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://home.apache.org/public/public_ldap_people.json",
        json={"people": {"me": {"urls": []}}},
        status_code=200,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert not await ASFProvider.match("https://me.example.com", client)


async def test_asf_provider_login(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
) -> None:
    """
    Test the ASF provider login.
    """
    async with current_app.app_context():
        ASFProvider.register()

    mocker.patch(
        "robida.blueprints.relmeauth.providers.asf.session",
        new={
            "relmeauth.asf.state": "92cdeabd827843ad871d0214dcb2d12e",
            "relmeauth.asf.uid": "me",
            "relmeauth.asf.url": "https://home.apache.org/phonebook.html?uid=me",
        },
    )

    response = await client.get("/relmeauth/asf/login")

    assert response.status_code == 302
    assert response.headers["Location"] == (
        "https://oauth.apache.org/auth?"
        "redirect_uri=http%3A%2F%2Fexample.com%2Frelmeauth%2Fasf%2Fcallback&"
        "state=92cdeabd827843ad871d0214dcb2d12e"
    )


async def test_asf_provider_callback(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the ASF callback request.
    """
    async with current_app.app_context():
        ASFProvider.register()

    session = {
        "relmeauth.asf.me": "https://me.example.com",
        "relmeauth.asf.url": "https://home.apache.org/phonebook.html?uid=me",
        "relmeauth.asf.uid": "me",
        "relmeauth.asf.state": "92cdeabd827843ad871d0214dcb2d12e",
    }

    mocker.patch(
        "robida.blueprints.relmeauth.providers.asf.session",
        new=session,
    )

    httpx_mock.add_response(
        url="https://oauth.apache.org/token?code=12345",
        json={
            "uid": "me",
            "email": "me@example.com",
            "fullname": "Alice Doe",
            "isMember": True,
            "isChair": False,
            "isRoot": False,
            "projects": ["superset"],
            "pmcs": ["superset"],
            "state": "92cdeabd827843ad871d0214dcb2d12e",
        },
    )

    response = await client.get(
        "/relmeauth/asf/callback",
        query_string={"code": "12345"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert session["me"] == "https://me.example.com"


async def test_asf_provider_callback_next(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the ASF callback request when `next` is set in the session.
    """
    async with current_app.app_context():
        ASFProvider.register()

    session = {
        "relmeauth.asf.me": "https://me.example.com",
        "relmeauth.asf.url": "https://home.apache.org/phonebook.html?uid=me",
        "relmeauth.asf.uid": "me",
        "relmeauth.asf.state": "92cdeabd827843ad871d0214dcb2d12e",
        "next": "/continue",
    }

    mocker.patch(
        "robida.blueprints.relmeauth.providers.asf.session",
        new=session,
    )

    httpx_mock.add_response(
        url="https://oauth.apache.org/token?code=12345",
        json={
            "uid": "me",
            "email": "me@example.com",
            "fullname": "Alice Doe",
            "isMember": True,
            "isChair": False,
            "isRoot": False,
            "projects": ["superset"],
            "pmcs": ["superset"],
            "state": "92cdeabd827843ad871d0214dcb2d12e",
        },
    )

    response = await client.get(
        "/relmeauth/asf/callback",
        query_string={"code": "12345"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/continue"
    assert session["me"] == "https://me.example.com"


async def test_asf_provider_callback_uid_mismatch(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the ASF callback request when `uid` doesn't match.
    """
    async with current_app.app_context():
        ASFProvider.register()

    session = {
        "relmeauth.asf.me": "https://me.example.com",
        "relmeauth.asf.url": "https://home.apache.org/phonebook.html?uid=me",
        "relmeauth.asf.uid": "me",
        "relmeauth.asf.state": "92cdeabd827843ad871d0214dcb2d12e",
    }

    mocker.patch(
        "robida.blueprints.relmeauth.providers.asf.session",
        new=session,
    )

    httpx_mock.add_response(
        url="https://oauth.apache.org/token?code=12345",
        json={
            "uid": "alice",
            "email": "me@example.com",
            "fullname": "Alice Doe",
            "isMember": True,
            "isChair": False,
            "isRoot": False,
            "projects": ["superset"],
            "pmcs": ["superset"],
            "state": "92cdeabd827843ad871d0214dcb2d12e",
        },
    )

    response = await client.get(
        "/relmeauth/asf/callback",
        query_string={"code": "12345"},
    )

    assert response.status_code == 401
    assert await response.data == b"Unauthorized"
    assert "me" not in session


async def test_asf_provider_callback_state_mismatch(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the ASF callback request when `state` doesn't match.
    """
    async with current_app.app_context():
        ASFProvider.register()

    session = {
        "relmeauth.asf.me": "https://me.example.com",
        "relmeauth.asf.url": "https://home.apache.org/phonebook.html?uid=me",
        "relmeauth.asf.uid": "me",
        "relmeauth.asf.state": "92cdeabd827843ad871d0214dcb2d12e",
    }

    mocker.patch(
        "robida.blueprints.relmeauth.providers.asf.session",
        new=session,
    )

    httpx_mock.add_response(
        url="https://oauth.apache.org/token?code=12345",
        json={
            "uid": "me",
            "email": "me@example.com",
            "fullname": "Alice Doe",
            "isMember": True,
            "isChair": False,
            "isRoot": False,
            "projects": ["superset"],
            "pmcs": ["superset"],
            "state": "tampered",
        },
    )

    response = await client.get(
        "/relmeauth/asf/callback",
        query_string={"code": "12345"},
    )

    assert response.status_code == 401
    assert await response.data == b"Unauthorized"
    assert "me" not in session
