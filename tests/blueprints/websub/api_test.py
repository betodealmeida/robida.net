"""
Tests for WebSub.
"""

from pytest_mock import MockerFixture
from quart import testing

from robida.blueprints.websub.models import SubscriptionRequest


async def test_hub(mocker: MockerFixture, client: testing.QuartClient) -> None:
    """
    Test the hub endpoint.
    """
    validate_subscription = mocker.patch(
        "robida.blueprints.websub.api.validate_subscription"
    )

    response = await client.post(
        "/websub",
        form={
            "hub.mode": "subscribe",
            "hub.topic": "http://example.com/feed/1",
            "hub.callback": "http://example.com/callback",
            "hub.lease_seconds": "3600",
            "hub.secret": "secret",
        },
    )

    assert response.status_code == 202
    validate_subscription.assert_called_with(
        SubscriptionRequest(
            **{
                "hub.mode": "subscribe",
                "hub.topic": "http://example.com/feed/1",
                "hub.callback": "http://example.com/callback",
                "hub.lease_seconds": "3600",
                "hub.secret": "secret",
            }
        )
    )

    response = await client.post(
        "/websub",
        form={
            "hub.mode": "unsubscribe",
            "hub.topic": "http://example.com/feed/1",
            "hub.callback": "http://example.com/callback",
        },
    )

    assert response.status_code == 202
    validate_subscription.assert_called_with(
        SubscriptionRequest(
            **{
                "hub.mode": "unsubscribe",
                "hub.topic": "http://example.com/feed/1",
                "hub.callback": "http://example.com/callback",
            }
        )
    )


async def test_hub_invalid_mode(
    mocker: MockerFixture,
    client: testing.QuartClient,
) -> None:
    """
    Test the hub endpoint with an invalid mode.
    """
    mocker.patch("robida.blueprints.websub.api.validate_subscription")

    response = await client.post(
        "/websub",
        form={
            "hub.mode": "delete",
            "hub.topic": "http://example.com/feed/1",
            "hub.callback": "http://example.com/callback",
        },
    )

    assert response.status_code == 400


async def test_hub_invalid_topic(
    mocker: MockerFixture,
    client: testing.QuartClient,
) -> None:
    """
    Test the hub endpoint with an invalid topic.
    """
    mocker.patch("robida.blueprints.websub.api.validate_subscription")

    response = await client.post(
        "/websub",
        form={
            "hub.mode": "subscribe",
            "hub.topic": "http://example.com/",
            "hub.callback": "http://example.com/callback",
        },
    )

    assert response.status_code == 400
    assert await response.data == b"Only URLs in http://example.com/feed are supported"


async def test_publish(mocker: MockerFixture, client: testing.QuartClient) -> None:
    """
    Test the publish endpoint.
    """
    distribute_content = mocker.patch("robida.blueprints.websub.api.distribute_content")

    response = await client.post(
        "/websub/publish",
        form={
            "hub.mode": "publish",
            "hub.url": "http://example.com/feed/1",
        },
    )

    assert response.status_code == 202
    distribute_content.assert_called_with(["http://example.com/feed/1"])


async def test_publish_multiple(
    mocker: MockerFixture, client: testing.QuartClient
) -> None:
    """
    Test the publish endpoint with multiple updated URLs.
    """
    distribute_content = mocker.patch("robida.blueprints.websub.api.distribute_content")

    response = await client.post(
        "/websub/publish",
        form=[
            ("hub.mode", "publish"),
            ("hub.url[]", "http://example.com/feed/1"),
            ("hub.url[]", "http://example.com/feed/tags/something"),
        ],
    )

    assert response.status_code == 202
    distribute_content.assert_called_with(
        [
            "http://example.com/feed/1",
            "http://example.com/feed/tags/something",
        ]
    )
