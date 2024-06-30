"""
Tests for `robots.txt`.
"""

from uuid import UUID

from pytest_mock import MockerFixture
from quart import testing


async def test_robots(client: testing.QuartClient) -> None:
    """
    Test the file.
    """
    response = await client.get("/robots.txt")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"


async def test_honeypot(mocker: MockerFixture, client: testing.QuartClient) -> None:
    """
    Test the honeypot.
    """
    mocker.patch("robida.blueprints.robots.api.asyncio.sleep")
    mocker.patch(
        "robida.blueprints.robots.api.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    response = await client.get("/secret/into-the-mirror")
    assert await response.data == (
        b"from into-the-mirror to "
        b'<a href="/secret/92cdeabd827843ad871d0214dcb2d12e">'
        b"page 92cdeabd827843ad871d0214dcb2d12e</a>"
    )
