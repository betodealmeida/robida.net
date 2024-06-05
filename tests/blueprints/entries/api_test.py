"""
Test the entries endpoints.
"""

from quart import testing


async def test_entries(client: testing.QuartClient) -> None:
    """
    Test the entries endpoint.
    """
    response = await client.get("/entries/")

    assert response.status_code == 200
    assert await response.json == {"entries": "entries"}


async def test_entry(client: testing.QuartClient) -> None:
    """
    Test the entry endpoint.
    """
    response = await client.get("/entries/92cdeabd-8278-43ad-871d-0214dcb2d12e")

    assert response.status_code == 200
    assert await response.json == {"entry": "92cdeabd827843ad871d0214dcb2d12e"}


async def test_entry_invalid(client: testing.QuartClient) -> None:
    """
    Test the entry endpoint when the UUID is invalid.
    """
    response = await client.get("/entries/not-a-uuid")

    assert response.status_code == 404
