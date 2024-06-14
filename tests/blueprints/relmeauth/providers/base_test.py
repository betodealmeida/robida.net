"""
Tests for the base RelMeAuth provider.
"""

from pytest_mock import MockerFixture
from quart import Quart, session

from robida.blueprints.relmeauth.providers.base import Provider


async def test_base_provider(mocker: MockerFixture, current_app: Quart) -> None:
    """
    Test the base provider.
    """
    # the base provider never matches
    assert not Provider.match("https://me.example.com")

    async with current_app.test_request_context("/", method="GET"):
        Provider.blueprint = mocker.MagicMock()

        Provider(
            "https://me.example.com",
            "https://home.apache.org/phonebook.html?uid=me",
        )

        assert dict(session) == {}
