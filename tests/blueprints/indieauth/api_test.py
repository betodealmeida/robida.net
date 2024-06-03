"""
Tests for the IndieAuth API.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from aiosqlite.core import Connection
from bs4 import BeautifulSoup
from freezegun import freeze_time
from pytest_mock import MockerFixture
from quart import testing

from robida.blueprints.indieauth.helpers import ClientInfo


async def test_authorization(
    mocker: MockerFixture,
    client: testing.QuartClient,
) -> None:
    """
    Test the authorization endpoint.
    """
    mocker.patch(
        "robida.blueprints.indieauth.api.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    mocker.patch(
        "robida.blueprints.indieauth.api.get_client_info",
        return_value=ClientInfo(
            name="Example App",
            url="https://example.com/",
            image="https://example.com/logo.png",
            redirect_uris={
                "https://example.com/redirect2",
                "https://example.com/redirect",
            },
        ),
    )

    response = await client.get(
        "/auth",
        query_string={
            "response_type": "code",
            "client_id": "https://app.example.com/",
            "redirect_uri": "https://app.example.com/redirect",
            "state": "1234567890",
            "code_challenge": "OfYAxt8zU2dAPDWQxTAUIteRzMsoj9QBdMIVEDOErUo",
            "code_challenge_method": "S256",
            "scope": "profile+create+update+delete",
            "me": "https://user.example.net/",
        },
    )

    assert response.status_code == 200

    soup = BeautifulSoup(await response.data, "html.parser")
    assert soup.find("a", {"class": "button"})["href"] == (
        "https://app.example.com/redirect?"
        "code=92cdeabd827843ad871d0214dcb2d12e&"
        "state=1234567890&"
        "iss=http%3A%2F%2Frobida.net%2F.well-known%2Foauth-authorization-server"
    )


async def test_authorization_invalid_response_type(client: testing.QuartClient) -> None:
    """
    Test the authorization endpoint with an invalid response type.
    """
    response = await client.get(
        "/auth",
        query_string={
            "response_type": "query",
            "client_id": "https://app.example.com/",
            "redirect_uri": "https://app.example.com/redirect",
            "state": "1234567890",
            "code_challenge": "OfYAxt8zU2dAPDWQxTAUIteRzMsoj9QBdMIVEDOErUo",
            "code_challenge_method": "S256",
            "scope": "profile+create+update+delete",
            "me": "https://user.example.net/",
        },
    )

    assert response.status_code == 400
    assert await response.data == b"invalid_request"


async def test_authorization_invalid_code_challenge_method(
    client: testing.QuartClient,
) -> None:
    """
    Test the authorization endpoint with an invalid code challenge method.
    """
    response = await client.get(
        "/auth",
        query_string={
            "response_type": "code",
            "client_id": "https://app.example.com/",
            "redirect_uri": "https://app.example.com/redirect",
            "state": "1234567890",
            "code_challenge": "OfYAxt8zU2dAPDWQxTAUIteRzMsoj9QBdMIVEDOErUo",
            "code_challenge_method": "plain",
            "scope": "profile+create+update+delete",
            "me": "https://user.example.net/",
        },
    )

    assert response.status_code == 400
    assert await response.data == b"invalid_request"


async def test_authorization_invalid_redirect(
    mocker: MockerFixture,
    client: testing.QuartClient,
) -> None:
    """
    Test validating the authorization redirect URI.
    """
    mocker.patch(
        "robida.blueprints.indieauth.api.get_client_info",
        return_value=ClientInfo(
            name="Example App",
            url="https://example.com/",
            image="https://example.com/logo.png",
            redirect_uris={
                "https://example.com/redirect2",
                "https://example.com/redirect",
            },
        ),
    )

    response = await client.get(
        "/auth",
        query_string={
            "response_type": "code",
            "client_id": "https://example.com/",
            "redirect_uri": "https://app.example.com/redirect",
            "state": "1234567890",
            "code_challenge": "OfYAxt8zU2dAPDWQxTAUIteRzMsoj9QBdMIVEDOErUo",
            "code_challenge_method": "S256",
            "scope": "profile+create+update+delete",
            "me": "https://user.example.net/",
        },
    )

    assert response.status_code == 400
    assert await response.data == b"invalid_request"


@freeze_time("2024-01-01 00:00:00")
async def test_profile_url(client: testing.QuartClient, db: Connection) -> None:
    """
    Test the profile URL endpoint happy path.
    """
    created_at = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO oauth_authorization_codes "
        "(code, client_id, redirect_uri, scope, code_challenge, "
        "code_challenge_method, used, expires_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "abcdef123456",
            "https://app.example.com/",
            "https://app.example.com/redirect",
            None,
            "hjooUY_1tBlE_dBuCKGUK8XuSRrc_zNByH-roC5sIXA",
            "S256",
            False,
            created_at + timedelta(minutes=10),
            created_at,
        ),
    )
    await db.commit()

    response = await client.post(
        "/auth",
        form={
            "grant_type": "authorization_code",
            "code": "abcdef123456",
            "client_id": "https://app.example.com/",
            "redirect_uri": "https://app.example.com/redirect",
            "code_verifier": "zo6yP8H9te4I0lk2Uclcry47yPbTT9jRbdnIZPdMUfazH5iD8vkNw",
        },
    )

    assert response.status_code == 200
    assert await response.json == {"me": "http://robida.net/"}


@freeze_time("2024-01-01 00:00:00")
async def test_profile_url_expired(
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test the profile URL endpoint when the code has expired.
    """
    created_at = datetime.now(timezone.utc) - timedelta(minutes=20)

    await db.execute(
        "INSERT INTO oauth_authorization_codes "
        "(code, client_id, redirect_uri, scope, code_challenge, "
        "code_challenge_method, used, expires_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "abcdef123456",
            "https://app.example.com/",
            "https://app.example.com/redirect",
            None,
            "hjooUY_1tBlE_dBuCKGUK8XuSRrc_zNByH-roC5sIXA",
            "S256",
            False,
            created_at + timedelta(minutes=10),
            created_at,
        ),
    )
    await db.commit()

    response = await client.post(
        "/auth",
        form={
            "grant_type": "authorization_code",
            "code": "abcdef123456",
            "client_id": "https://app.example.com/",
            "redirect_uri": "https://app.example.com/redirect",
            "code_verifier": "zo6yP8H9te4I0lk2Uclcry47yPbTT9jRbdnIZPdMUfazH5iD8vkNw",
        },
    )

    assert response.status_code == 400
    assert await response.data == b"invalid_grant"


@freeze_time("2024-01-01 00:00:00")
async def test_profile_invalid_grant(client: testing.QuartClient) -> None:
    """
    Test the profile URL endpoint with an invalid grant.
    """
    response = await client.post(
        "/auth",
        form={
            "grant_type": "something_else",
            "code": "abcdef123456",
            "client_id": "https://app.example.com/",
            "redirect_uri": "https://app.example.com/redirect",
            "code_verifier": "zo6yP8H9te4I0lk2Uclcry47yPbTT9jRbdnIZPdMUfazH5iD8vkNw",
        },
    )

    assert response.status_code == 400
    assert await response.data == b"invalid_request"


@freeze_time("2024-01-01 00:00:00")
async def test_access_token(
    mocker: MockerFixture,
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test the access token endpoint happy path.
    """
    mocker.patch(
        "robida.blueprints.indieauth.api.uuid4",
        side_effect=[
            UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            UUID("c35ad471-6c6c-488b-9ffc-8854607192f0"),
        ],
    )

    created_at = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO oauth_authorization_codes "
        "(code, client_id, redirect_uri, scope, code_challenge, "
        "code_challenge_method, used, expires_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "abcdef123456",
            "https://app.example.com/",
            "https://app.example.com/redirect",
            "read email profile",
            "hjooUY_1tBlE_dBuCKGUK8XuSRrc_zNByH-roC5sIXA",
            "S256",
            False,
            created_at + timedelta(minutes=10),
            created_at,
        ),
    )
    await db.commit()

    response = await client.post(
        "/token",
        form={
            "grant_type": "authorization_code",
            "code": "abcdef123456",
            "client_id": "https://app.example.com/",
            "redirect_uri": "https://app.example.com/redirect",
            "code_verifier": "zo6yP8H9te4I0lk2Uclcry47yPbTT9jRbdnIZPdMUfazH5iD8vkNw",
        },
    )

    assert response.status_code == 200
    assert await response.json == {
        "access_token": "ra_92cdeabd827843ad871d0214dcb2d12e",
        "expires_in": 3600,
        "me": "http://robida.net/",
        "profile": {
            "email": "robida@example.com",
            "name": "Robida",
            "photo": "http://robida.net/static/photo.jpg",
            "url": "http://robida.net/",
        },
        "refresh_token": "rr_c35ad4716c6c488b9ffc8854607192f0",
        "scope": "read email profile",
        "token_type": "Bearer",
    }

    async with db.execute("SELECT * FROM oauth_tokens") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "client_id": "https://app.example.com/",
        "token_type": "Bearer",
        "access_token": "ra_92cdeabd827843ad871d0214dcb2d12e",
        "refresh_token": "rr_c35ad4716c6c488b9ffc8854607192f0",
        "scope": "read email profile",
        "expires_at": "2024-01-01 01:00:00+00:00",
        "last_refresh_at": "2024-01-01 00:00:00+00:00",
        "created_at": "2024-01-01 00:00:00+00:00",
    }


@freeze_time("2024-01-01 00:00:00")
async def test_access_token_email_without_profile(
    mocker: MockerFixture,
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test the access token endpoint with email scope but no profile.
    """
    mocker.patch(
        "robida.blueprints.indieauth.api.uuid4",
        side_effect=[
            UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            UUID("c35ad471-6c6c-488b-9ffc-8854607192f0"),
        ],
    )

    created_at = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO oauth_authorization_codes "
        "(code, client_id, redirect_uri, scope, code_challenge, "
        "code_challenge_method, used, expires_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "abcdef123456",
            "https://app.example.com/",
            "https://app.example.com/redirect",
            "read email",
            "hjooUY_1tBlE_dBuCKGUK8XuSRrc_zNByH-roC5sIXA",
            "S256",
            False,
            created_at + timedelta(minutes=10),
            created_at,
        ),
    )
    await db.commit()

    response = await client.post(
        "/token",
        form={
            "grant_type": "authorization_code",
            "code": "abcdef123456",
            "client_id": "https://app.example.com/",
            "redirect_uri": "https://app.example.com/redirect",
            "code_verifier": "zo6yP8H9te4I0lk2Uclcry47yPbTT9jRbdnIZPdMUfazH5iD8vkNw",
        },
    )

    assert response.status_code == 200
    assert await response.json == {
        "access_token": "ra_92cdeabd827843ad871d0214dcb2d12e",
        "expires_in": 3600,
        "me": "http://robida.net/",
        "refresh_token": "rr_c35ad4716c6c488b9ffc8854607192f0",
        "scope": "read email",
        "token_type": "Bearer",
    }


@freeze_time("2024-01-01 00:00:00")
async def test_access_token_no_scope(
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test the access token endpoint when no scope is passed.
    """
    created_at = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO oauth_authorization_codes "
        "(code, client_id, redirect_uri, scope, code_challenge, "
        "code_challenge_method, used, expires_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "abcdef123456",
            "https://app.example.com/",
            "https://app.example.com/redirect",
            None,
            "hjooUY_1tBlE_dBuCKGUK8XuSRrc_zNByH-roC5sIXA",
            "S256",
            False,
            created_at + timedelta(minutes=10),
            created_at,
        ),
    )
    await db.commit()

    response = await client.post(
        "/token",
        form={
            "grant_type": "authorization_code",
            "code": "abcdef123456",
            "client_id": "https://app.example.com/",
            "redirect_uri": "https://app.example.com/redirect",
            "code_verifier": "zo6yP8H9te4I0lk2Uclcry47yPbTT9jRbdnIZPdMUfazH5iD8vkNw",
        },
    )

    assert response.status_code == 400
    assert await response.data == b"invalid_request"


async def test_refresh_token(
    mocker: MockerFixture,
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test the refresh token endpoint happy path.
    """
    mocker.patch(
        "robida.blueprints.indieauth.api.uuid4",
        side_effect=[
            UUID("a90b76ce-0e97-48e7-bdb4-7c91dba4751c"),
            UUID("47166383-9885-4b55-8d25-c77533bad940"),
        ],
    )

    with freeze_time("2024-01-01 00:00:00"):
        created_at = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO oauth_tokens"
        "(client_id, token_type, access_token, refresh_token, scope, expires_at, "
        "last_refresh_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "https://app.example.com/",
            "Bearer",
            "ra_92cdeabd827843ad871d0214dcb2d12e",
            "rr_c35ad4716c6c488b9ffc8854607192f0",
            "read email profile",
            created_at + timedelta(minutes=10),
            created_at,
            created_at,
        ),
    )
    await db.commit()

    with freeze_time("2024-01-02 00:00:00"):
        response = await client.post(
            "/token",
            form={
                "grant_type": "refresh_token",
                "client_id": "https://app.example.com/",
                "refresh_token": "rr_c35ad4716c6c488b9ffc8854607192f0",
            },
        )

    assert response.status_code == 200
    assert await response.json == {
        "access_token": "ra_a90b76ce0e9748e7bdb47c91dba4751c",
        "expires_in": 3600,
        "refresh_token": "rr_4716638398854b558d25c77533bad940",
        "scope": "read email profile",
        "token_type": "Bearer",
    }

    async with db.execute("SELECT * FROM oauth_tokens") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "client_id": "https://app.example.com/",
        "token_type": "Bearer",
        "access_token": "ra_a90b76ce0e9748e7bdb47c91dba4751c",
        "refresh_token": "rr_4716638398854b558d25c77533bad940",
        "scope": "read email profile",
        "expires_at": "2024-01-02 01:00:00+00:00",
        "last_refresh_at": "2024-01-02 00:00:00+00:00",
        "created_at": "2024-01-01 00:00:00+00:00",
    }


async def test_refresh_token_reduce_scope(
    mocker: MockerFixture,
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test the refresh token endpoint reducing the scope.
    """
    mocker.patch(
        "robida.blueprints.indieauth.api.uuid4",
        side_effect=[
            UUID("a90b76ce-0e97-48e7-bdb4-7c91dba4751c"),
            UUID("47166383-9885-4b55-8d25-c77533bad940"),
        ],
    )

    with freeze_time("2024-01-01 00:00:00"):
        created_at = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO oauth_tokens"
        "(client_id, token_type, access_token, refresh_token, scope, expires_at, "
        "last_refresh_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "https://app.example.com/",
            "Bearer",
            "ra_92cdeabd827843ad871d0214dcb2d12e",
            "rr_c35ad4716c6c488b9ffc8854607192f0",
            "read email profile",
            created_at + timedelta(minutes=10),
            created_at,
            created_at,
        ),
    )
    await db.commit()

    with freeze_time("2024-01-02 00:00:00"):
        response = await client.post(
            "/token",
            form={
                "grant_type": "refresh_token",
                "client_id": "https://app.example.com/",
                "refresh_token": "rr_c35ad4716c6c488b9ffc8854607192f0",
                "scope": "read",
            },
        )

    assert response.status_code == 200
    assert await response.json == {
        "access_token": "ra_a90b76ce0e9748e7bdb47c91dba4751c",
        "expires_in": 3600,
        "refresh_token": "rr_4716638398854b558d25c77533bad940",
        "scope": "read",
        "token_type": "Bearer",
    }

    async with db.execute("SELECT scope FROM oauth_tokens") as cursor:
        row = await cursor.fetchone()

    assert row["scope"] == "read"


async def test_refresh_token_increase_scope(
    mocker: MockerFixture,
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test the refresh token endpoint increasing the scope.
    """
    mocker.patch(
        "robida.blueprints.indieauth.api.uuid4",
        side_effect=[
            UUID("a90b76ce-0e97-48e7-bdb4-7c91dba4751c"),
            UUID("47166383-9885-4b55-8d25-c77533bad940"),
        ],
    )

    with freeze_time("2024-01-01 00:00:00"):
        created_at = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO oauth_tokens"
        "(client_id, token_type, access_token, refresh_token, scope, expires_at, "
        "last_refresh_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "https://app.example.com/",
            "Bearer",
            "ra_92cdeabd827843ad871d0214dcb2d12e",
            "rr_c35ad4716c6c488b9ffc8854607192f0",
            "read email profile",
            created_at + timedelta(minutes=10),
            created_at,
            created_at,
        ),
    )
    await db.commit()

    with freeze_time("2024-01-02 00:00:00"):
        response = await client.post(
            "/token",
            form={
                "grant_type": "refresh_token",
                "client_id": "https://app.example.com/",
                "refresh_token": "rr_c35ad4716c6c488b9ffc8854607192f0",
                "scope": "read write update",
            },
        )

    assert response.status_code == 400
    assert await response.data == b"invalid_scope"


async def test_refresh_token_expired(
    mocker: MockerFixture,
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test the refresh token endpoint when it has expired.
    """
    mocker.patch(
        "robida.blueprints.indieauth.api.uuid4",
        side_effect=[
            UUID("a90b76ce-0e97-48e7-bdb4-7c91dba4751c"),
            UUID("47166383-9885-4b55-8d25-c77533bad940"),
        ],
    )

    with freeze_time("2024-01-01 00:00:00"):
        created_at = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO oauth_tokens"
        "(client_id, token_type, access_token, refresh_token, scope, expires_at, "
        "last_refresh_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "https://app.example.com/",
            "Bearer",
            "ra_92cdeabd827843ad871d0214dcb2d12e",
            "rr_c35ad4716c6c488b9ffc8854607192f0",
            "read email profile",
            created_at + timedelta(minutes=10),
            created_at,
            created_at,
        ),
    )
    await db.commit()

    with freeze_time("2025-01-02 00:00:00"):
        response = await client.post(
            "/token",
            form={
                "grant_type": "refresh_token",
                "client_id": "https://app.example.com/",
                "refresh_token": "rr_c35ad4716c6c488b9ffc8854607192f0",
                "scope": "read email profile",
            },
        )

    assert response.status_code == 400
    assert await response.data == b"invalid_grant"


async def test_token_dispatching(
    mocker: MockerFixture, client: testing.QuartClient
) -> None:
    """
    Test the token endpoint dispatching.
    """
    mocker.patch(
        "robida.blueprints.indieauth.api.GRANT_TYPES_SUPPORTED",
        new={"authorization_code", "refresh_token", "magic_link"},
    )

    response = await client.post(
        "/token",
        form={
            "grant_type": "magic_link",
            "code": "abcdef123456",
            "client_id": "https://app.example.com/",
            "redirect_uri": "https://app.example.com/redirect",
            "code_verifier": "zo6yP8H9te4I0lk2Uclcry47yPbTT9jRbdnIZPdMUfazH5iD8vkNw",
        },
    )
    assert response.status_code == 400
    assert await response.data == b"unsupported_grant_type"

    response = await client.post(
        "/token",
        form={
            "grant_type": "unkown_grant_type",
            "code": "abcdef123456",
            "client_id": "https://app.example.com/",
            "redirect_uri": "https://app.example.com/redirect",
            "code_verifier": "zo6yP8H9te4I0lk2Uclcry47yPbTT9jRbdnIZPdMUfazH5iD8vkNw",
        },
    )
    assert response.status_code == 400
    assert await response.data == b"invalid_request"


@freeze_time("2024-01-01 00:00:00")
async def test_userinfo(client: testing.QuartClient, db: Connection) -> None:
    """
    Test the user information endpoint happy path.
    """
    created_at = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO oauth_tokens"
        "(client_id, token_type, access_token, refresh_token, scope, expires_at, "
        "last_refresh_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "https://app.example.com/",
            "Bearer",
            "ra_92cdeabd827843ad871d0214dcb2d12e",
            "rr_c35ad4716c6c488b9ffc8854607192f0",
            "read email profile",
            created_at + timedelta(minutes=10),
            created_at,
            created_at,
        ),
    )
    await db.commit()

    response = await client.get(
        "/userinfo",
        headers={"Authorization": "Bearer ra_92cdeabd827843ad871d0214dcb2d12e"},
    )

    assert response.status_code == 200
    assert await response.json == {
        "email": "robida@example.com",
        "name": "Robida",
        "photo": "http://robida.net/static/photo.jpg",
        "url": "http://robida.net/",
    }


async def test_userinfo_expired_token(
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test the user information endpoint when the token has expired.
    """
    with freeze_time("2024-01-01 00:00:00"):
        created_at = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO oauth_tokens"
        "(client_id, token_type, access_token, refresh_token, scope, expires_at, "
        "last_refresh_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "https://app.example.com/",
            "Bearer",
            "ra_92cdeabd827843ad871d0214dcb2d12e",
            "rr_c35ad4716c6c488b9ffc8854607192f0",
            "read email profile",
            created_at + timedelta(minutes=10),
            created_at,
            created_at,
        ),
    )
    await db.commit()

    with freeze_time("2024-02-01 00:00:00"):
        response = await client.get(
            "/userinfo",
            headers={"Authorization": "Bearer ra_92cdeabd827843ad871d0214dcb2d12e"},
        )

    assert response.status_code == 401
    assert await response.data == b"invalid_token"


@freeze_time("2024-01-01 00:00:00")
async def test_userinfo_invalid_scope(
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test the user information endpoint when the token doesn't have the required scope.
    """
    created_at = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO oauth_tokens"
        "(client_id, token_type, access_token, refresh_token, scope, expires_at, "
        "last_refresh_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "https://app.example.com/",
            "Bearer",
            "ra_92cdeabd827843ad871d0214dcb2d12e",
            "rr_c35ad4716c6c488b9ffc8854607192f0",
            "read",
            created_at + timedelta(minutes=10),
            created_at,
            created_at,
        ),
    )
    await db.commit()

    response = await client.get(
        "/userinfo",
        headers={"Authorization": "Bearer ra_92cdeabd827843ad871d0214dcb2d12e"},
    )

    assert response.status_code == 403
    assert await response.data == b"insufficient_scope"


async def test_userinfo_without_auth(client: testing.QuartClient) -> None:
    """
    Test the user information endpoint without authentication.
    """
    response = await client.get("/userinfo")

    assert response.status_code == 401
    assert await response.data == b"invalid_token"


@freeze_time("2024-01-01 00:00:00")
async def test_revoke_token(client: testing.QuartClient, db: Connection) -> None:
    """
    Test the token revocation endpoint.
    """
    created_at = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO oauth_tokens"
        "(client_id, token_type, access_token, refresh_token, scope, expires_at, "
        "last_refresh_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "https://app.example.com/",
            "Bearer",
            "ra_92cdeabd827843ad871d0214dcb2d12e",
            "rr_c35ad4716c6c488b9ffc8854607192f0",
            "read",
            created_at + timedelta(minutes=10),
            created_at,
            created_at,
        ),
    )
    await db.commit()

    async with db.execute(
        "SELECT expires_at FROM oauth_tokens WHERE access_token = ?",
        ("ra_92cdeabd827843ad871d0214dcb2d12e",),
    ) as cursor:
        row = await cursor.fetchone()

    assert row["expires_at"] == "2024-01-01 00:10:00+00:00"

    response = await client.post(
        "/revoke",
        form={"token": "ra_92cdeabd827843ad871d0214dcb2d12e"},
    )

    assert response.status_code == 200

    async with db.execute(
        "SELECT expires_at FROM oauth_tokens WHERE access_token = ?",
        ("ra_92cdeabd827843ad871d0214dcb2d12e",),
    ) as cursor:
        row = await cursor.fetchone()

    assert row["expires_at"] == "2024-01-01 00:00:00+00:00"


async def test_revoke_invalid_token(client: testing.QuartClient) -> None:
    """
    Test revoking an invalid token.

    Per the spec, "the revocation endpoint responds with HTTP 200 for both the case
    where the token was successfully revoked, or if the submitted token was invalid."
    """
    response = await client.post("/revoke", form={"token": "hello!"})

    assert response.status_code == 200


async def test_revoke_qyery_parameter(client: testing.QuartClient) -> None:
    """
    Test passing `action=revoke` as a query parameter for older clients.
    """
    response = await client.post("/revoke?action=revoke", form={"token": "hello!"})

    assert response.status_code == 200


@freeze_time("2024-01-01 00:00:00")
async def test_introspect_token(client: testing.QuartClient, db: Connection) -> None:
    """
    Test the token introspection endpoint.
    """
    created_at = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO oauth_tokens"
        "(client_id, token_type, access_token, refresh_token, scope, expires_at, "
        "last_refresh_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "https://app.example.com/",
            "Bearer",
            "ra_92cdeabd827843ad871d0214dcb2d12e",
            "rr_c35ad4716c6c488b9ffc8854607192f0",
            "read",
            created_at + timedelta(minutes=10),
            created_at,
            created_at,
        ),
    )
    await db.commit()

    response = await client.post(
        "/introspect",
        form={"token": "ra_92cdeabd827843ad871d0214dcb2d12e"},
    )

    assert response.status_code == 200
    assert await response.json == {
        "active": True,
        "me": "http://robida.net/",
        "client_id": "https://app.example.com/",
        "scope": "read",
        "exp": 1704067800,
        "iat": 1704067200,
    }


async def test_introspect_token_expired(
    client: testing.QuartClient, db: Connection
) -> None:
    """
    Test the token introspection endpoint.
    """
    with freeze_time("2024-01-01 00:00:00"):
        created_at = datetime.now(timezone.utc)

    await db.execute(
        "INSERT INTO oauth_tokens"
        "(client_id, token_type, access_token, refresh_token, scope, expires_at, "
        "last_refresh_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "https://app.example.com/",
            "Bearer",
            "ra_92cdeabd827843ad871d0214dcb2d12e",
            "rr_c35ad4716c6c488b9ffc8854607192f0",
            "read",
            created_at + timedelta(minutes=10),
            created_at,
            created_at,
        ),
    )
    await db.commit()

    with freeze_time("2024-02-01 00:00:00"):
        response = await client.post(
            "/introspect",
            form={"token": "ra_92cdeabd827843ad871d0214dcb2d12e"},
        )

    assert response.status_code == 200
    assert await response.json == {"active": False}
