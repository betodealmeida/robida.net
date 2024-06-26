"""
Tests for the WebSub helper functions.
"""

from uuid import UUID

from aiosqlite import Connection
from freezegun import freeze_time
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture
from quart import Quart

from robida.blueprints.websub.helpers import (
    apply_parameters_to_url,
    distribute_content,
    send_to_subscriber,
    validate_subscription,
)
from robida.blueprints.websub.models import SubscriptionRequest


@freeze_time("2024-01-01 00:00:00")
async def test_subscribe(
    mocker: MockerFixture,
    db: Connection,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the subscribe function.
    """
    mocker.patch(
        "robida.blueprints.websub.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    httpx_mock.add_response(
        url=(
            "http://example.com/callback?"
            "hub.mode=subscribe&"
            "hub.topic=http%3A%2F%2Fexample.com%2Ffeed%2F1&"
            "hub.challenge=92cdeabd827843ad871d0214dcb2d12e&"
            "hub.lease_seconds=3600"
        ),
        content=b"92cdeabd827843ad871d0214dcb2d12e",
    )

    data = SubscriptionRequest(
        **{
            "hub.mode": "subscribe",
            "hub.topic": "http://example.com/feed/1",
            "hub.callback": "http://example.com/callback",
            "hub.lease_seconds": "3600",
            "hub.secret": "secret",
        }
    )

    async with current_app.app_context():
        await validate_subscription(data)

    async with db.execute("SELECT * FROM websub_publisher") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "callback": "http://example.com/callback",
        "topic": "http://example.com/feed/1",
        "expires_at": "2024-01-01 01:00:00+00:00",
        "secret": "secret",
        "last_delivery_at": "2024-01-01 00:00:00+00:00",
    }


@freeze_time("2024-01-01 00:00:00")
async def test_subscribe_no_lease(
    mocker: MockerFixture,
    db: Connection,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the subscribe function when no lease is specified.
    """
    mocker.patch(
        "robida.blueprints.websub.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    httpx_mock.add_response(
        url=(
            "http://example.com/callback?"
            "hub.mode=subscribe&"
            "hub.topic=http%3A%2F%2Fexample.com%2Ffeed%2F1&"
            "hub.challenge=92cdeabd827843ad871d0214dcb2d12e&"
            "hub.lease_seconds=31536000"
        ),
        content=b"92cdeabd827843ad871d0214dcb2d12e",
    )

    data = SubscriptionRequest(
        **{
            "hub.mode": "subscribe",
            "hub.topic": "http://example.com/feed/1",
            "hub.callback": "http://example.com/callback",
            "hub.secret": "secret",
        }
    )

    async with current_app.app_context():
        await validate_subscription(data)

    async with db.execute("SELECT * FROM websub_publisher") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "callback": "http://example.com/callback",
        "topic": "http://example.com/feed/1",
        "expires_at": "2024-12-31 00:00:00+00:00",
        "secret": "secret",
        "last_delivery_at": "2024-01-01 00:00:00+00:00",
    }


@freeze_time("2024-01-01 00:00:00")
async def test_subscribe_extra_parameters(
    mocker: MockerFixture,
    db: Connection,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the subscribe function with unknown extra parameters.

    "Hubs MUST ignore additional request parameters they do not understand."
    """
    mocker.patch(
        "robida.blueprints.websub.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    httpx_mock.add_response(
        url=(
            "http://example.com/callback?"
            "hub.mode=subscribe&"
            "hub.topic=http%3A%2F%2Fexample.com%2Ffeed%2F1&"
            "hub.challenge=92cdeabd827843ad871d0214dcb2d12e&"
            "hub.lease_seconds=3600"
        ),
        content=b"92cdeabd827843ad871d0214dcb2d12e",
    )

    data = SubscriptionRequest(
        **{
            "hub.mode": "subscribe",
            "hub.topic": "http://example.com/feed/1",
            "hub.callback": "http://example.com/callback",
            "hub.lease_seconds": "3600",
            "hub.secret": "secret",
            "hub.extra": "extra",
        }
    )

    async with current_app.app_context():
        await validate_subscription(data)

    async with db.execute("SELECT * FROM websub_publisher") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "callback": "http://example.com/callback",
        "topic": "http://example.com/feed/1",
        "expires_at": "2024-01-01 01:00:00+00:00",
        "secret": "secret",
        "last_delivery_at": "2024-01-01 00:00:00+00:00",
    }


@freeze_time("2024-01-01 00:00:00")
async def test_subscribe_invalid_request(
    mocker: MockerFixture,
    db: Connection,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the subscribe function when the subscriber doesn't confirm the request.
    """
    mocker.patch(
        "robida.blueprints.websub.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    httpx_mock.add_response(
        url=(
            "http://example.com/callback?"
            "hub.mode=subscribe&"
            "hub.topic=http%3A%2F%2Fexample.com%2Ffeed%2F1&"
            "hub.challenge=92cdeabd827843ad871d0214dcb2d12e&"
            "hub.lease_seconds=3600"
        ),
        status_code=400,
    )

    data = SubscriptionRequest(
        **{
            "hub.mode": "subscribe",
            "hub.topic": "http://example.com/feed/1",
            "hub.callback": "http://example.com/callback",
            "hub.lease_seconds": "3600",
            "hub.secret": "secret",
        }
    )

    async with current_app.app_context():
        await validate_subscription(data)

    async with db.execute("SELECT * FROM websub_publisher") as cursor:
        row = await cursor.fetchone()

    assert row is None


@freeze_time("2024-01-01 00:00:00")
async def test_subscribe_challenge_mismatch(
    mocker: MockerFixture,
    db: Connection,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the subscribe function when the subscriber returns a different challenge.
    """
    mocker.patch(
        "robida.blueprints.websub.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    httpx_mock.add_response(
        url=(
            "http://example.com/callback?"
            "hub.mode=subscribe&"
            "hub.topic=http%3A%2F%2Fexample.com%2Ffeed%2F1&"
            "hub.challenge=92cdeabd827843ad871d0214dcb2d12e&"
            "hub.lease_seconds=3600"
        ),
        content=b"some other challenge",
    )

    data = SubscriptionRequest(
        **{
            "hub.mode": "subscribe",
            "hub.topic": "http://example.com/feed/1",
            "hub.callback": "http://example.com/callback",
            "hub.lease_seconds": "3600",
            "hub.secret": "secret",
        }
    )

    async with current_app.app_context():
        await validate_subscription(data)

    async with db.execute("SELECT * FROM websub_publisher") as cursor:
        row = await cursor.fetchone()

    assert row is None


async def test_subscribe_resubscribe(
    mocker: MockerFixture,
    db: Connection,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test renewing a subscription.
    """
    mocker.patch(
        "robida.blueprints.websub.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    httpx_mock.add_response(
        url=(
            "http://example.com/callback?"
            "hub.mode=subscribe&"
            "hub.topic=http%3A%2F%2Fexample.com%2Ffeed%2F1&"
            "hub.challenge=92cdeabd827843ad871d0214dcb2d12e&"
            "hub.lease_seconds=172800"
        ),
        content=b"92cdeabd827843ad871d0214dcb2d12e",
    )

    data = SubscriptionRequest(
        **{
            "hub.mode": "subscribe",
            "hub.topic": "http://example.com/feed/1",
            "hub.callback": "http://example.com/callback",
            "hub.lease_seconds": "172800",  # 2 days
            "hub.secret": "secret",
        }
    )

    async with current_app.app_context():
        with freeze_time("2024-01-01 00:00:00"):
            await validate_subscription(data)

    async with db.execute("SELECT * FROM websub_publisher") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "callback": "http://example.com/callback",
        "topic": "http://example.com/feed/1",
        "expires_at": "2024-01-03 00:00:00+00:00",
        "secret": "secret",
        "last_delivery_at": "2024-01-01 00:00:00+00:00",
    }

    data = SubscriptionRequest(
        **{
            "hub.mode": "subscribe",
            "hub.topic": "http://example.com/feed/1",
            "hub.callback": "http://example.com/callback",
            "hub.lease_seconds": "172800",  # 2 days
            "hub.secret": "secret",
        }
    )

    async with current_app.app_context():
        with freeze_time("2024-01-02 00:00:00"):
            await validate_subscription(data)

    async with db.execute("SELECT * FROM websub_publisher") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "callback": "http://example.com/callback",
        "topic": "http://example.com/feed/1",
        "expires_at": "2024-01-04 00:00:00+00:00",
        "secret": "secret",
        "last_delivery_at": "2024-01-01 00:00:00+00:00",
    }


@freeze_time("2024-01-01 00:00:00")
async def test_unsubscribe(
    mocker: MockerFixture,
    db: Connection,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the unsubscribe function.
    """
    mocker.patch(
        "robida.blueprints.websub.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    httpx_mock.add_response(
        url=(
            "http://example.com/callback?"
            "hub.mode=unsubscribe&"
            "hub.topic=http%3A%2F%2Fexample.com%2Ffeed%2F1&"
            "hub.challenge=92cdeabd827843ad871d0214dcb2d12e&"
        ),
        content=b"92cdeabd827843ad871d0214dcb2d12e",
    )

    await db.execute(
        """
INSERT INTO websub_publisher (
    callback,
    topic,
    expires_at,
    secret,
    last_delivery_at
) VALUES (
    'http://example.com/callback',
    'http://example.com/feed/1',
    '2024-01-01 01:00:00+00:00',
    'secret',
    '2024-01-01 00:00:00+00:00'
)
        """
    )
    await db.commit()

    data = SubscriptionRequest(
        **{
            "hub.mode": "unsubscribe",
            "hub.topic": "http://example.com/feed/1",
            "hub.callback": "http://example.com/callback",
            "hub.secret": "secret",
        }
    )

    async with current_app.app_context():
        await validate_subscription(data)

    async with db.execute("SELECT * FROM websub_publisher") as cursor:
        row = await cursor.fetchone()

    assert row is None


@freeze_time("2024-01-01 00:00:00")
async def test_unsubscribe_invalid_request(
    mocker: MockerFixture,
    db: Connection,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the unsubscribe function.
    """
    mocker.patch(
        "robida.blueprints.websub.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    httpx_mock.add_response(
        url=(
            "http://example.com/callback?"
            "hub.mode=unsubscribe&"
            "hub.topic=http%3A%2F%2Fexample.com%2Ffeed%2F1&"
            "hub.challenge=92cdeabd827843ad871d0214dcb2d12e&"
        ),
        status_code=400,
    )

    await db.execute(
        """
INSERT INTO websub_publisher (
    callback,
    topic,
    expires_at,
    secret,
    last_delivery_at
) VALUES (
    'http://example.com/callback',
    'http://example.com/feed/1',
    '2024-01-01 01:00:00+00:00',
    'secret',
    '2024-01-01 00:00:00+00:00'
)
        """
    )
    await db.commit()

    data = SubscriptionRequest(
        **{
            "hub.mode": "unsubscribe",
            "hub.topic": "http://example.com/feed/1",
            "hub.callback": "http://example.com/callback",
            "hub.secret": "secret",
        }
    )

    async with current_app.app_context():
        await validate_subscription(data)

    async with db.execute(
        """
SELECT *
FROM
    websub_publisher
WHERE
    callback = ? AND
    topic = ?
        """,
        ("http://example.com/callback", "http://example.com/feed/1"),
    ) as cursor:
        row = await cursor.fetchone()

    assert row is not None


@freeze_time("2024-01-01 00:00:00")
async def test_unsubscribe_challenge_mismatch(
    mocker: MockerFixture,
    db: Connection,
    current_app: Quart,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the unsubscribe function.
    """
    mocker.patch(
        "robida.blueprints.websub.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    httpx_mock.add_response(
        url=(
            "http://example.com/callback?"
            "hub.mode=unsubscribe&"
            "hub.topic=http%3A%2F%2Fexample.com%2Ffeed%2F1&"
            "hub.challenge=92cdeabd827843ad871d0214dcb2d12e&"
        ),
        content=b"some other challenge",
    )

    await db.execute(
        """
INSERT INTO websub_publisher (
    callback,
    topic,
    expires_at,
    secret,
    last_delivery_at
) VALUES (
    'http://example.com/callback',
    'http://example.com/feed/1',
    '2024-01-01 01:00:00+00:00',
    'secret',
    '2024-01-01 00:00:00+00:00'
)
        """
    )
    await db.commit()

    data = SubscriptionRequest(
        **{
            "hub.mode": "unsubscribe",
            "hub.topic": "http://example.com/feed/1",
            "hub.callback": "http://example.com/callback",
            "hub.secret": "secret",
        }
    )

    async with current_app.app_context():
        await validate_subscription(data)

    async with db.execute(
        """
SELECT *
FROM
    websub_publisher
WHERE
    callback = ? AND
    topic = ?
        """,
        ("http://example.com/callback", "http://example.com/feed/1"),
    ) as cursor:
        row = await cursor.fetchone()

    assert row is not None


def test_apply_parameters_to_url() -> None:
    """
    Test the `apply_parameters_to_url` function.
    """
    url = "http://example.com"
    parameters = {"a": ["1"], "b": ["2"]}

    assert apply_parameters_to_url(url, **parameters) == "http://example.com?a=1&b=2"


async def test_distribute_content(
    mocker: MockerFixture,
    db: Connection,
    current_app: Quart,
) -> None:
    """
    Test the `distribute_content` function.
    """
    mocker.patch("robida.blueprints.websub.helpers.httpx")
    send_to_subscriber_ = mocker.patch(
        "robida.blueprints.websub.helpers.send_to_subscriber"
    )

    await db.execute(
        """
INSERT INTO websub_publisher (
    callback,
    topic,
    expires_at,
    secret,
    last_delivery_at
) VALUES (
    'http://example.com/callback1',
    'http://example.com/feed/1',
    '2024-02-01 01:00:00+00:00',
    'secret',
    '2024-01-01 00:00:00+00:00'
), (
    'http://example.com/callback2',
    'http://example.com/feed/1',
    '2024-01-01 01:00:00+00:00',
    'secret',
    '2024-01-01 00:00:00+00:00'
), (
    'http://example.com/callback2',
    'http://example.com/feed/2',
    '2024-02-01 01:00:00+00:00',
    'secret',
    '2024-01-01 00:00:00+00:00'
)
        """
    )
    await db.commit()

    with freeze_time("2024-01-02 00:00:00"):
        async with current_app.app_context():
            await distribute_content(
                [
                    "http://example.com/feed/1",
                    "http://example.com/feed/2",
                ]
            )

    assert send_to_subscriber_.call_count == 2
    assert dict(send_to_subscriber_.mock_calls[0].args[0]) == {
        "callback": "http://example.com/callback1",
        "topic": "http://example.com/feed/1",
        "expires_at": "2024-02-01 01:00:00+00:00",
        "secret": "secret",
        "last_delivery_at": "2024-01-01 00:00:00+00:00",
    }
    assert dict(send_to_subscriber_.mock_calls[1].args[0]) == {
        "callback": "http://example.com/callback2",
        "topic": "http://example.com/feed/2",
        "expires_at": "2024-02-01 01:00:00+00:00",
        "secret": "secret",
        "last_delivery_at": "2024-01-01 00:00:00+00:00",
    }


async def test_send_to_subscriber(
    mocker: MockerFixture,
    db: Connection,
    current_app: Quart,
) -> None:
    """
    Test the `send_to_subscriber` function.
    """
    await db.execute(
        """
INSERT INTO websub_publisher (
    callback,
    topic,
    expires_at,
    secret,
    last_delivery_at
) VALUES (
    'http://example.com/callback1',
    'http://example.com/feed/1',
    '2024-02-01 01:00:00+00:00',
    'secret',
    '2024-01-01 00:00:00+00:00'
), (
    'http://example.com/callback2',
    'http://example.com/feed/1',
    '2024-01-01 01:00:00+00:00',
    'secret',
    '2024-01-01 00:00:00+00:00'
), (
    'http://example.com/callback2',
    'http://example.com/feed/2',
    '2024-02-01 01:00:00+00:00',
    'secret',
    '2024-01-01 00:00:00+00:00'
)
        """
    )
    await db.commit()

    async def data() -> str:
        return "test"

    quart_client = mocker.Mock()
    response = mocker.Mock()
    response.headers = {"Content-Type": "text/plain"}
    type(response).data = mocker.PropertyMock(side_effect=data)
    quart_client.get = mocker.AsyncMock(return_value=response)

    httpx_client = mocker.AsyncMock()

    async with current_app.app_context():
        await send_to_subscriber(
            {
                "callback": "http://example.com/callback1",
                "topic": "http://example.com/feed/1",
                "expires_at": "2024-02-01 01:00:00+00:00",
                "secret": "secret",
                "last_delivery_at": "2024-01-01 00:00:00+00:00",
            },
            quart_client,
            httpx_client,
        )

    httpx_client.post.assert_called_once_with(
        "http://example.com/callback1",
        headers={
            "Content-Type": "text/plain",
            "Link": (
                '<http://example.com/websub>; rel="hub", '
                '<http://example.com/feed/1>; rel="self"'
            ),
            "X-Hub-Signature": "sha1=1aa349585ed7ecbd3b9c486a30067e395ca4b356",
        },
        content="test",
    )
