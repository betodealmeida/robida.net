"""
Tests for the homepage.
"""

from quart import testing
from werkzeug.datastructures import Headers


async def test_homepage_headers(client: testing.QuartClient) -> None:
    """
    Test main endpoint and its headers.
    """
    response = await client.get("/")

    assert response.status_code == 200
    assert response.headers == Headers(
        [
            ("content-type", "text/html; charset=utf-8"),
            ("Content-Length", len(await response.data)),
            ("link", '<http://robida.net/>; rel="self"'),
            ("link", '<http://robida.net/micropub/>; rel="micropub"'),
        ]
    )
