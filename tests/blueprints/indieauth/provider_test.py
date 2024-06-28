"""
Tests for the IndieAuth provider.
"""

# pylint: disable=redefined-outer-name

from uuid import UUID

import httpx
from pydantic import HttpUrl
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture
from quart import Quart, session, testing

from robida.blueprints.indieauth.provider import (
    IndieAuthProvider,
    ServerMetadataResponse,
    get_server_metadata,
)


metadata_response = {
    "authorization_endpoint": "https://me.example.com/auth",
    "authorization_response_iss_parameter_supported": True,
    "code_challenge_methods_supported": ["S256"],
    "grant_types_supported": ["authorization_code", "refresh_token"],
    "introspection_endpoint": "https://me.example.com/introspect",
    "introspection_endpoint_auth_methods_supported": ["client_secret_basic"],
    "issuer": "https://me.example.com/.well-known/oauth-authorization-server",
    "response_types_supported": ["code", "id"],
    "revocation_endpoint": "https://me.example.com/revoke",
    "revocation_endpoint_auth_methods_supported": ["none"],
    "scopes_supported": [
        "create",
        "draft",
        "update",
        "delete",
        "undelete",
        "media",
        "read",
        "follow",
        "mute",
        "block",
        "channels",
        "profile",
        "email",
    ],
    "service_documentation": "https://indieauth.spec.indieweb.org/",
    "token_endpoint": "https://me.example.com/token",
    "userinfo_endpoint": "https://me.example.com/userinfo",
}


async def test_get_server_metadata(httpx_mock: HTTPXMock) -> None:
    """
    Test the `get_server_metadata` function.
    """
    httpx_mock.add_response(
        url="http://example.com/.well-known/oauth-authorization-server",
        json=metadata_response,
    )

    async with httpx.AsyncClient() as client:
        assert await get_server_metadata(
            "http://example.com/.well-known/oauth-authorization-server",
            client,
        ) == ServerMetadataResponse(
            issuer=HttpUrl(
                "https://me.example.com/.well-known/oauth-authorization-server"
            ),
            authorization_endpoint=HttpUrl("https://me.example.com/auth"),
            token_endpoint=HttpUrl("https://me.example.com/token"),
            introspection_endpoint=HttpUrl("https://me.example.com/introspect"),
            introspection_endpoint_auth_methods_supported=["client_secret_basic"],
            revocation_endpoint=HttpUrl("https://me.example.com/revoke"),
            revocation_endpoint_auth_methods_supported=["none"],
            scopes_supported=[
                "create",
                "draft",
                "update",
                "delete",
                "undelete",
                "media",
                "read",
                "follow",
                "mute",
                "block",
                "channels",
                "profile",
                "email",
            ],
            response_types_supported=["code", "id"],
            grant_types_supported=["authorization_code", "refresh_token"],
            service_documentation=HttpUrl("https://indieauth.spec.indieweb.org/"),
            code_challenge_methods_supported=["S256"],
            authorization_response_iss_parameter_supported=True,
            userinfo_endpoint=HttpUrl("https://me.example.com/userinfo"),
        )


async def test_get_server_metadata_error(httpx_mock: HTTPXMock) -> None:
    """
    Test the `get_server_metadata` function errorring.
    """
    httpx_mock.add_response(
        url="http://example.com/.well-known/oauth-authorization-server",
        status_code=400,
    )

    async with httpx.AsyncClient() as client:
        assert (
            await get_server_metadata(
                "http://example.com/.well-known/oauth-authorization-server",
                client,
            )
            is None
        )


async def test_get_server_metadata_no_json(httpx_mock: HTTPXMock) -> None:
    """
    Test the `get_server_metadata` function not returning JSON.
    """
    httpx_mock.add_response(
        url="http://example.com/.well-known/oauth-authorization-server",
        html="<html></html>",
        status_code=200,
    )

    async with httpx.AsyncClient() as client:
        assert (
            await get_server_metadata(
                "http://example.com/.well-known/oauth-authorization-server",
                client,
            )
            is None
        )


async def test_indieauth_provider_match(
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the IndieAuth provider `match` method.
    """
    httpx_mock.add_response(
        url="https://me.example.com/",
        headers={
            "Link": (
                "<https://me.example.com/.well-known/oauth-authorization-server>; "
                'rel="indieauth-metadata"'
            ),
        },
    )
    httpx_mock.add_response(
        url="https://me.example.com/.well-known/oauth-authorization-server",
        json=metadata_response,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert await IndieAuthProvider.match("https://me.example.com/", client)


async def test_indieauth_provider_match_self(current_app: Quart) -> None:
    """
    Test the IndieAuth provider doesn't match the main application.
    """
    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert not await IndieAuthProvider.match("http://example.com/", client)


async def test_indieauth_provider_match_head_error(
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the IndieAuth provider `match` method when the profile `HEAD` request errors.
    """
    httpx_mock.add_response(
        url="https://me.example.com/",
        status_code=400,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert not await IndieAuthProvider.match("https://me.example.com/", client)


async def test_indieauth_provider_match_get_error(
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the IndieAuth provider `match` method when the profile `GET` request errors.
    """
    httpx_mock.add_response(
        method="HEAD",
        url="https://me.example.com/",
    )
    httpx_mock.add_response(
        method="GET",
        url="https://me.example.com/",
        status_code=400,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert not await IndieAuthProvider.match("https://me.example.com/", client)


async def test_indieauth_provider_match_link(
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the IndieAuth provider `match` method with a `<Link/>`.
    """
    httpx_mock.add_response(
        url="https://me.example.com/",
        html="""
<link
    rel="indieauth-metadata"
    href="https://me.example.com/.well-known/oauth-authorization-server"
/>
        """,
    )
    httpx_mock.add_response(
        url="https://me.example.com/.well-known/oauth-authorization-server",
        json=metadata_response,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert await IndieAuthProvider.match("https://me.example.com/", client)


async def test_indieauth_provider_match_head_old(
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the IndieAuth provider `match` method with an `authorization_endpoint` header.
    """
    httpx_mock.add_response(
        url="https://me.example.com/",
        headers={
            "Link": (
                "<https://me.example.com/.well-known/oauth-authorization-server>; "
                'rel="authorization_endpoint"'
            ),
        },
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert await IndieAuthProvider.match("https://me.example.com/", client)


async def test_indieauth_provider_match_get_old(
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the IndieAuth provider `match` method with an `authorization_endpoint` `<Link/>`.
    """
    httpx_mock.add_response(
        url="https://me.example.com/",
        html="""
<link
    rel="authorization_endpoint"
    href="https://me.example.com/.well-known/oauth-authorization-server"
/>
        """,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert await IndieAuthProvider.match("https://me.example.com/", client)


async def test_from_metadata(httpx_mock: HTTPXMock, current_app: Quart) -> None:
    """
    Test the `from_metadata` method.
    """
    httpx_mock.add_response(
        url="https://me.example.com/.well-known/oauth-authorization-server",
        json=metadata_response,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            provider = await IndieAuthProvider.from_metadata(
                "https://me.example.com/",
                "https://me.example.com/.well-known/oauth-authorization-server",
                client,
            )

            assert provider
            assert provider.me == "https://me.example.com/"
            assert provider.profile == "https://me.example.com/auth"
            assert provider.scope == "profile"
            assert provider.code_challenge_method == "S256"


async def test_from_metadata_error(httpx_mock: HTTPXMock, current_app: Quart) -> None:
    """
    Test the `from_metadata` method when the metadata request fails.
    """
    httpx_mock.add_response(
        url="https://me.example.com/.well-known/oauth-authorization-server",
        status_code=400,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert not await IndieAuthProvider.from_metadata(
                "https://me.example.com/",
                "https://me.example.com/.well-known/oauth-authorization-server",
                client,
            )


async def test_from_metadata_invalid_issuer(
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the `from_metadata` method when the issuer is invalid.
    """
    bad_metadata_response = metadata_response.copy()
    bad_metadata_response["issuer"] = "https://evil.example.com/"

    httpx_mock.add_response(
        url="https://me.example.com/.well-known/oauth-authorization-server",
        json=bad_metadata_response,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            assert not await IndieAuthProvider.from_metadata(
                "https://me.example.com/",
                "https://me.example.com/.well-known/oauth-authorization-server",
                client,
            )


async def test_from_metadata_no_code_challenge(
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the `from_metadata` method when PKCE is not supported.
    """
    old_metadata_response = metadata_response.copy()
    old_metadata_response["code_challenge_methods_supported"] = []

    httpx_mock.add_response(
        url="https://me.example.com/.well-known/oauth-authorization-server",
        json=old_metadata_response,
    )

    async with current_app.test_request_context("/", method="GET"):
        async with httpx.AsyncClient() as client:
            provider = await IndieAuthProvider.from_metadata(
                "https://me.example.com/",
                "https://me.example.com/.well-known/oauth-authorization-server",
                client,
            )

            assert provider
            assert provider.code_challenge_method is None


async def test_indieauth_provider(mocker: MockerFixture, current_app: Quart) -> None:
    """
    Test the IndieAuth provider.
    """
    mocker.patch(
        "robida.blueprints.indieauth.provider.uuid4",
        side_effect=[
            UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            UUID("5abcee45-844c-4d44-8a4b-fbc83b71efe8"),
        ],
    )

    async with current_app.test_request_context("/", method="GET"):
        provider = IndieAuthProvider(
            "https://me.example.com/",
            "https://me.example.com/auth",
            "profile",
            "S256",
        )

        response = provider.login()
        assert response.status_code == 302
        assert response.headers["Location"] == "/auth/indieauth/login"

        assert session["indieauth.client.me"] == "https://me.example.com/"
        assert (
            session["indieauth.client.authorization_endpoint"]
            == "https://me.example.com/auth"
        )
        assert session["indieauth.client.state"] == "92cdeabd827843ad871d0214dcb2d12e"
        assert session["indieauth.client.scope"] == "profile"
        assert (
            session["indieauth.client.code_verifier"]
            == "5abcee45844c4d448a4bfbc83b71efe8"
        )
        assert session["indieauth.client.code_challenge_method"] == "S256"


async def test_indieauth_provider_login(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
) -> None:
    """
    Test the IndieAuth provider flow.
    """
    async with current_app.app_context():
        IndieAuthProvider.register()

    mocker.patch(
        "robida.blueprints.indieauth.provider.session",
        new={
            "indieauth.client.me": "https://me.example.com/",
            "indieauth.client.authorization_endpoint": "https://me.example.com/auth",
            "indieauth.client.state": "92cdeabd827843ad871d0214dcb2d12e",
            "indieauth.client.scope": "profile",
            "indieauth.client.code_verifier": "5abcee45844c4d448a4bfbc83b71efe8",
            "indieauth.client.code_challenge_method": "S256",
        },
    )

    response = await client.get("/auth/indieauth/login")

    assert response.status_code == 302
    assert response.headers["Location"] == (
        "https://me.example.com/auth?"
        "response_type=code&"
        "client_id=http%3A%2F%2Fexample.com%2F&"
        "redirect_uri=http%3A%2F%2Fexample.com%2Fauth%2Findieauth%2Fcallback&"
        "state=92cdeabd827843ad871d0214dcb2d12e&"
        "me=https%3A%2F%2Fme.example.com%2F&"
        "scope=profile&"
        "code_challenge=8wZ5DLLn5dsR60neg4Wrj1bz5N0objeCk6-GRRcaPAM&"
        "code_challenge_method=S256"
    )


async def test_indieauth_provider_callback(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the IndieAuth callback request.
    """
    async with current_app.app_context():
        IndieAuthProvider.register()

    session = {
        "indieauth.client.me": "https://me.example.com/",
        "indieauth.client.authorization_endpoint": "https://me.example.com/auth",
        "indieauth.client.state": "92cdeabd827843ad871d0214dcb2d12e",
        "indieauth.client.scope": "profile",
        "indieauth.client.code_verifier": "5abcee45844c4d448a4bfbc83b71efe8",
        "indieauth.client.code_challenge_method": "S256",
    }

    mocker.patch(
        "robida.blueprints.indieauth.provider.session",
        new=session,
    )

    httpx_mock.add_response(
        url="https://me.example.com/auth",
        json={"me": "https://me.example.com/"},
    )

    response = await client.get(
        "/auth/indieauth/callback",
        query_string={
            "code": "123456",
            "state": "92cdeabd827843ad871d0214dcb2d12e",
            "iss": "https://me.example.com/",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert session["me"] == "https://me.example.com/"


async def test_indieauth_provider_callback_next(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the IndieAuth callback request when `next` is set in the session.
    """
    async with current_app.app_context():
        IndieAuthProvider.register()

    session = {
        "indieauth.client.me": "https://me.example.com/",
        "indieauth.client.authorization_endpoint": "https://me.example.com/auth",
        "indieauth.client.state": "92cdeabd827843ad871d0214dcb2d12e",
        "indieauth.client.scope": "profile",
        "indieauth.client.code_verifier": "5abcee45844c4d448a4bfbc83b71efe8",
        "indieauth.client.code_challenge_method": "S256",
        "next": "/continue",
    }

    mocker.patch(
        "robida.blueprints.indieauth.provider.session",
        new=session,
    )

    httpx_mock.add_response(
        url="https://me.example.com/auth",
        json={"me": "https://me.example.com/"},
    )

    response = await client.get(
        "/auth/indieauth/callback",
        query_string={
            "code": "123456",
            "state": "92cdeabd827843ad871d0214dcb2d12e",
            "iss": "https://me.example.com/",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/continue"
    assert session["me"] == "https://me.example.com/"


async def test_indieauth_provider_callback_unauthorized(
    mocker: MockerFixture,
    client: testing.QuartClient,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the IndieAuth callback request when `me` doesn't match.
    """
    async with current_app.app_context():
        IndieAuthProvider.register()

    session = {
        "indieauth.client.me": "https://me.example.com/",
        "indieauth.client.authorization_endpoint": "https://me.example.com/auth",
        "indieauth.client.state": "92cdeabd827843ad871d0214dcb2d12e",
        "indieauth.client.scope": "profile",
        "indieauth.client.code_verifier": "5abcee45844c4d448a4bfbc83b71efe8",
        "indieauth.client.code_challenge_method": "S256",
    }

    mocker.patch(
        "robida.blueprints.indieauth.provider.session",
        new=session,
    )

    httpx_mock.add_response(
        url="https://me.example.com/auth",
        json={"me": "https://evil.example.com/"},
    )

    response = await client.get(
        "/auth/indieauth/callback",
        query_string={
            "code": "123456",
            "state": "92cdeabd827843ad871d0214dcb2d12e",
            "iss": "https://me.example.com/",
        },
    )

    assert response.status_code == 401
    assert await response.data == b"Unauthorized"
