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
            ("link", '<http://example.com/micropub>; rel="micropub"'),
            (
                "link",
                "<http://example.com/.well-known/oauth-authorization-server>; "
                'rel="indieauth-metadata"',
            ),
            ("link", '<http://example.com/auth>; rel="authorization_endpoint"'),
            ("link", '<http://example.com/token>; rel="token_endpoint"'),
            ("link", '<http://example.com/websub>; rel="hub"'),
            ("link", '<http://example.com/feed.json>; rel="alternate"'),
            ("link", '<http://example.com/feed.rss>; rel="alternate"'),
            ("link", '<http://example.com/feed.xml>; rel="alternate"'),
            ("link", '<http://example.com/feed.html>; rel="alternate"'),
            ("x-robots-tag", "noai"),
            ("x-robots-tag", "noimageai"),
            ("vary", "Cookie"),
        ]
    )
