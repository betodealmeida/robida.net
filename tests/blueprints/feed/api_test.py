"""
Test the feed endpoints.
"""

import json

from quart import Quart, testing

from robida.db import get_db


async def test_feed_json(client: testing.QuartClient, current_app: Quart) -> None:
    """
    Test the JSON Feed endpoint.
    """
    async with get_db(current_app) as db:
        await db.execute(
            """
INSERT INTO entries (
    uuid,
    author,
    location,
    content,
    read,
    deleted,
    created_at,
    last_modified_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "92cdeabd827843ad871d0214dcb2d12e",
                "http://example.com/",
                "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                json.dumps(
                    {
                        "type": ["h-entry"],
                        "properties": {
                            "content": ["hello world"],
                            "category": ["foo", "bar"],
                        },
                    },
                    separators=(",", ":"),
                ),
                False,
                False,
                "2024-01-01 00:00:00+00:00",
                "2024-01-01 00:00:00+00:00",
            ),
        )
        await db.commit()

    response = await client.get("/feed.json")

    assert response.status_code == 200
    assert '<http://example.com/feed.json>; rel="self"' in response.headers.getlist(
        "Link"
    )
    assert response.headers["Content-Type"] == "application/feed+json"
    assert response.headers["Last-Modified"] == "Mon, 01 Jan 2024 00:00:00 GMT"
    assert (
        response.headers["ETag"]
        == "faeee22f6d53d26e38c317f7197c22911ab5cfa4781979a4d792d13118c973cb"
    )
    assert await response.json == {
        "title": "Robida",
        "version": "https://jsonfeed.org/version/1.1",
        "home_page_url": "http://example.com/",
        "feed_url": "http://example.com/feed.json",
        "description": "A blog",
        "user_comment": (
            "This feed allows you to read the posts from this site in any feed reader "
            "that supports the JSON Feed format. To add this feed to your reader, copy "
            "the following URL — http://example.com/feed.json — and add it your reader."
        ),
        "next_url": "http://example.com/feed.json?page=2",
        "authors": [
            {
                "name": "Beto Dealmeida",
                "url": "http://example.com/",
                "avatar": "http://example.com/static/photo.jpg",
            }
        ],
        "language": "en-US",
        "hubs": ["http://example.com/websub"],
        "items": [
            {
                "id": "92cdeabd827843ad871d0214dcb2d12e",
                "url": "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                "content_html": "hello world",
                "content_text": "hello world",
                "date_published": "2024-01-01T00:00:00Z",
                "date_modified": "2024-01-01T00:00:00Z",
                "authors": [
                    {
                        "name": "Beto Dealmeida",
                        "url": "http://example.com/",
                        "avatar": "http://example.com/static/photo.jpg",
                    }
                ],
            }
        ],
    }


async def test_feed_json_content_negotiation(client: testing.QuartClient) -> None:
    """
    Test the JSON Feed endpoint via content negotiation.
    """
    response = await client.get(
        "/feed",
        headers={"Accept": "application/feed+json"},
    )

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/feed+json"
    assert '<http://example.com/feed.json>; rel="self"' in response.headers.getlist(
        "Link"
    )


async def test_feed_json_conditional_get(client: testing.QuartClient) -> None:
    """
    Test conditional GET on the JSON Feed endpoint.
    """
    response = await client.get(
        "/feed.json",
        headers={
            "If-None-Match": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        },
    )

    assert response.status_code == 304


async def test_feed_json_pagination(
    client: testing.QuartClient,
    current_app: Quart,
) -> None:
    """
    Test the JSON Feed pagination
    """
    async with get_db(current_app) as db:
        await db.execute(
            """
INSERT INTO entries (
    uuid,
    author,
    location,
    content,
    read,
    deleted,
    created_at,
    last_modified_at
)
VALUES
(?, ?, ?, ?, ?, ?, ?, ?),
(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "92cdeabd827843ad871d0214dcb2d12e",
                "http://example.com/",
                "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                json.dumps(
                    {
                        "type": ["h-entry"],
                        "properties": {
                            "content": ["hello world"],
                            "category": ["foo", "bar"],
                        },
                    },
                    separators=(",", ":"),
                ),
                False,
                False,
                "2024-01-01 00:00:00+00:00",
                "2024-01-01 00:00:00+00:00",
                "d2f5229639d946e1a6c539e33d119403",
                "http://example.com/",
                "http://example.com/feed/d2f52296-39d9-46e1-a6c5-39e33d119403",
                json.dumps(
                    {
                        "type": ["h-entry"],
                        "properties": {
                            "content": ["hello world"],
                            "category": ["foo", "bar"],
                        },
                    },
                    separators=(",", ":"),
                ),
                False,
                True,
                "2024-01-02 00:00:00+00:00",
                "2024-01-02 00:00:00+00:00",
            ),
        )
        await db.commit()

    response = await client.get("/feed.json?page=1&page_size=1")
    payload = await response.json
    assert payload["next_url"] == "http://example.com/feed.json?page=2&page_size=1"

    response = await client.get("/feed.json?page=2&page_size=1")
    payload = await response.json
    assert payload["next_url"] == "http://example.com/feed.json?page=3&page_size=1"


async def test_feed_html(client: testing.QuartClient, current_app: Quart) -> None:
    """
    Test the h-feed HTML endpoint.
    """
    async with get_db(current_app) as db:
        await db.execute(
            """
INSERT INTO entries (
    uuid,
    author,
    location,
    content,
    read,
    deleted,
    created_at,
    last_modified_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "92cdeabd827843ad871d0214dcb2d12e",
                "http://example.com/",
                "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                json.dumps(
                    {
                        "type": ["h-entry"],
                        "properties": {
                            "content": ["hello world"],
                            "category": ["foo", "bar"],
                        },
                    },
                    separators=(",", ":"),
                ),
                False,
                False,
                "2024-01-01 00:00:00+00:00",
                "2024-01-01 00:00:00+00:00",
            ),
        )
        await db.commit()

    response = await client.get("/feed.html", headers={"Accept": "text/mf2+html"})

    assert response.status_code == 200
    assert '<http://example.com/feed.html>; rel="self"' in response.headers.getlist(
        "Link"
    )
    assert response.headers["Content-Type"] == "text/mf2+html"
    assert response.headers["Last-Modified"] == "Mon, 01 Jan 2024 00:00:00 GMT"
    assert (
        response.headers["ETag"]
        == "faeee22f6d53d26e38c317f7197c22911ab5cfa4781979a4d792d13118c973cb"
    )


async def test_feed_html_content_negotiation(client: testing.QuartClient) -> None:
    """
    Test the h-feed HTML endpoint via content negotiation.
    """
    response = await client.get(
        "/feed",
        headers={"Accept": "text/mf2+html"},
    )

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/mf2+html"
    assert '<http://example.com/feed.html>; rel="self"' in response.headers.getlist(
        "Link"
    )


async def test_feed_html_conditional_get(client: testing.QuartClient) -> None:
    """
    Test conditional GET on the h-feed HTML endpoint.
    """
    response = await client.get(
        "/feed.html",
        headers={
            "If-None-Match": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        },
    )

    assert response.status_code == 304


async def test_feed_rss(client: testing.QuartClient, current_app: Quart) -> None:
    """
    Test the RSS 2.0 endpoint.
    """
    async with get_db(current_app) as db:
        await db.execute(
            """
INSERT INTO entries (
    uuid,
    author,
    location,
    content,
    read,
    deleted,
    created_at,
    last_modified_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "92cdeabd827843ad871d0214dcb2d12e",
                "http://example.com/",
                "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                json.dumps(
                    {
                        "type": ["h-entry"],
                        "properties": {
                            "content": ["hello world"],
                            "category": ["foo", "bar"],
                        },
                    },
                    separators=(",", ":"),
                ),
                False,
                False,
                "2024-01-01 00:00:00+00:00",
                "2024-01-01 00:00:00+00:00",
            ),
        )
        await db.commit()

    response = await client.get("/feed.rss", headers={"Accept": "application/rss+xml"})

    assert response.status_code == 200
    assert '<http://example.com/feed.rss>; rel="self"' in response.headers.getlist(
        "Link"
    )
    assert response.headers["Content-Type"] == "application/rss+xml"
    assert response.headers["Last-Modified"] == "Mon, 01 Jan 2024 00:00:00 GMT"
    assert (
        response.headers["ETag"]
        == "faeee22f6d53d26e38c317f7197c22911ab5cfa4781979a4d792d13118c973cb"
    )


async def test_feed_rss_content_negotiation(client: testing.QuartClient) -> None:
    """
    Test the RSS 2.0 endpoint via content negotiation.
    """
    response = await client.get(
        "/feed",
        headers={"Accept": "application/rss+xml"},
    )

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/rss+xml"
    assert '<http://example.com/feed.rss>; rel="self"' in response.headers.getlist(
        "Link"
    )


async def test_feed_rss_conditional_get(client: testing.QuartClient) -> None:
    """
    Test conditional GET on the RSS 2.0 endpoint.
    """
    response = await client.get(
        "/feed.rss",
        headers={
            "If-None-Match": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        },
    )

    assert response.status_code == 304


async def test_feed_atom(client: testing.QuartClient, current_app: Quart) -> None:
    """
    Test the Atom endpoint.
    """
    async with get_db(current_app) as db:
        await db.execute(
            """
INSERT INTO entries (
    uuid,
    author,
    location,
    content,
    read,
    deleted,
    created_at,
    last_modified_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "92cdeabd827843ad871d0214dcb2d12e",
                "http://example.com/",
                "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                json.dumps(
                    {
                        "type": ["h-entry"],
                        "properties": {
                            "content": ["hello world"],
                            "category": ["foo", "bar"],
                        },
                    },
                    separators=(",", ":"),
                ),
                False,
                False,
                "2024-01-01 00:00:00+00:00",
                "2024-01-01 00:00:00+00:00",
            ),
        )
        await db.commit()

    response = await client.get("/feed.xml", headers={"Accept": "application/atom+xml"})

    assert response.status_code == 200
    assert '<http://example.com/feed.xml>; rel="self"' in response.headers.getlist(
        "Link"
    )
    assert response.headers["Content-Type"] == "application/atom+xml"
    assert response.headers["Last-Modified"] == "Mon, 01 Jan 2024 00:00:00 GMT"
    assert (
        response.headers["ETag"]
        == "faeee22f6d53d26e38c317f7197c22911ab5cfa4781979a4d792d13118c973cb"
    )


async def test_feed_atom_content_negotiation(client: testing.QuartClient) -> None:
    """
    Test the Atom endpoint via content negotiation.
    """
    response = await client.get(
        "/feed",
        headers={"Accept": "application/atom+xml"},
    )

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/atom+xml"
    assert '<http://example.com/feed.xml>; rel="self"' in response.headers.getlist(
        "Link"
    )


async def test_feed_atom_conditional_get(client: testing.QuartClient) -> None:
    """
    Test conditional GET on the Atom endpoint.
    """
    response = await client.get(
        "/feed.xml",
        headers={
            "If-None-Match": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        },
    )

    assert response.status_code == 304


async def test_entry(client: testing.QuartClient) -> None:
    """
    Test the entry endpoint.
    """
    response = await client.get("/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e")

    assert response.status_code == 200
    assert await response.json == {"entry": "92cdeabd827843ad871d0214dcb2d12e"}


async def test_entry_invalid(client: testing.QuartClient) -> None:
    """
    Test the entry endpoint when the UUID is invalid.
    """
    response = await client.get("/feed/not-a-uuid")

    assert response.status_code == 404


async def test_rss_xslt(client: testing.QuartClient) -> None:
    """
    Test the RSS 2.0 XSLT endpoint.
    """
    response = await client.get("/rss.xslt")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/xslt+xml"


async def test_atom_xslt(client: testing.QuartClient) -> None:
    """
    Test the Atom XSLT endpoint.
    """
    response = await client.get("/atom.xslt")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/xslt+xml"
