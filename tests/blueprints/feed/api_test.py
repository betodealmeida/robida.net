"""
Test the feed endpoints.
"""

from quart import testing


async def test_feed(client: testing.QuartClient) -> None:
    """
    Test the feed endpoint.
    """
    response = await client.get("/feed/")

    assert response.status_code == 200
    assert await response.json == {"feed": "feed"}


async def test_entry(client: testing.QuartClient) -> None:
    """
    Test the entry endpoint.
    """
    response = await client.get("/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e")

    assert response.status_code == 200
    assert await response.json == {"entry": "92cdeabd-8278-43ad-871d-0214dcb2d12e"}


async def test_entry_invalid(client: testing.QuartClient) -> None:
    """
    Test the entry endpoint when the UUID is invalid.
    """
    response = await client.get("/feed/not-a-uuid")

    assert response.status_code == 404
