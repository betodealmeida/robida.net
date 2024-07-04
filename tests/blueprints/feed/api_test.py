"""
Test the feed endpoints.
"""

import json

import mf2py
from aiosqlite import Connection
from freezegun import freeze_time
from quart import Quart, testing

from robida.db import load_entries


async def test_feed_json(db: Connection, client: testing.QuartClient) -> None:
    """
    Test the JSON Feed endpoint.
    """
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
        == "6c07533892a937cb31037af074c295e165dd8abe0f8d11eccd33ede1682abd0f"
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
        "authors": [
            {
                "name": "Beto Dealmeida",
                "url": "http://example.com/",
                "avatar": "http://example.com/static/img/photo.jpg",
            }
        ],
        "language": "en-US",
        "next_url": None,
        "hubs": ["http://example.com/websub"],
        "items": [
            {
                "id": "92cdeabd827843ad871d0214dcb2d12e",
                "url": "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                "tags": ["foo", "bar"],
                "content_html": "hello world",
                "content_text": "hello world",
                "date_published": "2024-01-01T00:00:00Z",
                "date_modified": "2024-01-01T00:00:00Z",
                "authors": [
                    {
                        "name": "Beto Dealmeida",
                        "url": "http://example.com/",
                        "avatar": "http://example.com/static/img/photo.jpg",
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
    db: Connection, client: testing.QuartClient
) -> None:
    """
    Test the JSON Feed pagination
    """
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
            False,
            "2024-01-02 00:00:00+00:00",
            "2024-01-02 00:00:00+00:00",
        ),
    )
    await db.commit()

    response = await client.get(
        "/feed.json",
        query_string={"page": "1", "page_size": "1"},
    )
    payload = await response.json
    assert len(payload["items"]) == 1
    assert payload["next_url"] == "http://example.com/feed.json?page=2&page_size=1"

    response = await client.get(
        "/feed.json",
        query_string={"page": "2", "page_size": "1"},
    )
    payload = await response.json
    assert len(payload["items"]) == 1
    assert payload["next_url"] is None


async def test_feed_html(db: Connection, client: testing.QuartClient) -> None:
    """
    Test the h-feed HTML endpoint.
    """
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
        == "6c07533892a937cb31037af074c295e165dd8abe0f8d11eccd33ede1682abd0f"
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


async def test_feed_rss(db: Connection, client: testing.QuartClient) -> None:
    """
    Test the RSS 2.0 endpoint.
    """
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
        == "6c07533892a937cb31037af074c295e165dd8abe0f8d11eccd33ede1682abd0f"
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


async def test_feed_atom(db: Connection, client: testing.QuartClient) -> None:
    """
    Test the Atom endpoint.
    """
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
        == "6c07533892a937cb31037af074c295e165dd8abe0f8d11eccd33ede1682abd0f"
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


@freeze_time("2024-01-01 00:00:00")
async def test_entry(client: testing.QuartClient, current_app: Quart) -> None:
    """
    Test the entry endpoint.
    """
    await load_entries(current_app)
    response = await client.get("/feed/8bf10ece-be18-4b96-af91-04e5c2a931ad")

    assert response.status_code == 200
    assert (
        response.headers["ETag"]
        == "eed8d2521e55b1bdedee8ae16e4dfd36db3b65cc1d3d5c3f4be2ec7743c51586"
    )

    html = await response.data
    assert mf2py.parse(html) == {
        "items": [
            {
                "type": ["h-entry"],
                "properties": {
                    "name": ["About"],
                    "summary": ["About this blog."],
                    "content": [
                        {
                            "value": (
                                "This blog runs a custom-built Python web framework "
                                "called Robida, built for the IndieWeb."
                            ),
                            "lang": "en",
                            "html": """<p>
    This blog runs a custom-built Python web framework called
    <a href="https://github.com/betodealmeida/robida.net/" rel="noopener noreferrer">Robida</a>, built for the
    <a href="https://indieweb.org/" rel="noopener noreferrer">IndieWeb</a>.
</p>""",
                        }
                    ],
                    "url": [
                        "http://example.com/feed/8bf10ece-be18-4b96-af91-04e5c2a931ad"
                    ],
                    "published": ["2024-01-01T00:00:00+0000"],
                    "category": ["about", "blog", "python"],
                },
                "children": [
                    {
                        "type": ["h-card"],
                        "properties": {
                            "name": ["Beto Dealmeida"],
                            "url": ["http://example.com/"],
                        },
                        "lang": "en",
                    }
                ],
                "lang": "en",
            }
        ],
        "rels": {
            "micropub": ["/micropub"],
            "indieauth-metadata": ["/.well-known/oauth-authorization-server"],
            "authorization_endpoint": ["/auth"],
            "token_endpoint": ["/token"],
            "hub": ["/websub"],
            "alternate": ["/feed.json", "/feed.rss", "/feed.xml", "/feed.html"],
            "stylesheet": ["/static/css/main.css"],
            "noopener": [
                "https://github.com/betodealmeida/robida.net/",
                "https://indieweb.org/",
            ],
            "noreferrer": [
                "https://github.com/betodealmeida/robida.net/",
                "https://indieweb.org/",
            ],
        },
        "rel-urls": {
            "/micropub": {"text": "", "rels": ["micropub"]},
            "/.well-known/oauth-authorization-server": {
                "text": "",
                "rels": ["indieauth-metadata"],
            },
            "/auth": {"text": "", "rels": ["authorization_endpoint"]},
            "/token": {"text": "", "rels": ["token_endpoint"]},
            "/websub": {"text": "", "rels": ["hub"]},
            "/feed.json": {"text": "", "rels": ["alternate"]},
            "/feed.rss": {"text": "", "rels": ["alternate"]},
            "/feed.xml": {"text": "", "rels": ["alternate"]},
            "/feed.html": {"text": "", "rels": ["alternate"]},
            "/static/css/main.css": {"text": "", "rels": ["stylesheet"]},
            "https://github.com/betodealmeida/robida.net/": {
                "text": "Robida",
                "rels": ["noopener", "noreferrer"],
            },
            "https://indieweb.org/": {
                "text": "IndieWeb",
                "rels": ["noopener", "noreferrer"],
            },
        },
        "debug": {
            "description": "mf2py - microformats2 parser for python",
            "source": "https://github.com/microformats/mf2py",
            "version": "2.0.1",
            "markup parser": "html5lib",
        },
        "alternates": [
            {"url": "/feed.json", "text": ""},
            {"url": "/feed.rss", "text": ""},
            {"url": "/feed.xml", "text": ""},
            {"url": "/feed.html", "text": ""},
        ],
    }


async def test_entry_not_found(client: testing.QuartClient) -> None:
    """
    Test the entry endpoint response for non-existing entries.
    """
    response = await client.get("/feed/2da01180-2997-43fb-b0bf-9b1df9783d2e")

    assert response.status_code == 404


async def test_entry_deleted(client: testing.QuartClient, current_app: Quart) -> None:
    """
    Test the entry endpoint response for deleted entries.
    """
    await load_entries(current_app)
    response = await client.get("/feed/37c9ed45-5c0c-43e4-b088-0e904ed849d7")

    assert response.status_code == 410


@freeze_time("2024-01-01 00:00:00")
async def test_entry_not_modified(
    client: testing.QuartClient,
    current_app: Quart,
) -> None:
    """
    Test the entry endpoint response for non-modified entries.
    """
    await load_entries(current_app)
    response = await client.get(
        "/feed/8bf10ece-be18-4b96-af91-04e5c2a931ad",
        headers={
            "If-None-Match": "eed8d2521e55b1bdedee8ae16e4dfd36db3b65cc1d3d5c3f4be2ec7743c51586"
        },
    )

    assert response.status_code == 304


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


async def test_max_page_size_redirect(client: testing.QuartClient) -> None:
    """
    Test that we redirect the user when a too large page size is requested.
    """
    for page in ["/feed.html", "/feed.rss", "/feed.xml", "/feed.json"]:
        response = await client.get(page, query_string={"page_size": "1000"})

        assert response.status_code == 302
        assert response.headers["Location"] == f"{page}?page=1&page_size=100"
