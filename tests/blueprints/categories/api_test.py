"""
Tests for the categories API.
"""

# pylint: disable=line-too-long

import mf2py
from freezegun import freeze_time
from quart import Quart, testing

from robida.db import load_entries


@freeze_time("2024-01-01 00:00:00")
async def test_category(client: testing.QuartClient, current_app: Quart) -> None:
    """
    Test the category endpoint.
    """
    await load_entries(current_app)
    response = await client.get("/category/python")

    assert response.status_code == 200
    assert (
        response.headers["ETag"]
        == "e4f00d1a3dc8c3ed4289ba94cbdc9b3143b55fc7352002b2a98baa7569a67532"
    )

    html = await response.data
    assert mf2py.parse(html) == {
        "items": [
            {
                "type": ["h-feed"],
                "properties": {"name": ["Robida"], "summary": ["A blog"]},
                "children": [
                    {
                        "type": ["h-entry"],
                        "properties": {
                            "name": ["About"],
                            "summary": ["About this blog."],
                            "content": [
                                {
                                    "value": (
                                        "This blog runs a custom-built Python web "
                                        "framework called Robida, built for the "
                                        "IndieWeb. ⋯"
                                    ),
                                    "lang": "en",
                                    "html": """This blog runs a custom-built Python web framework called
    Robida, built for the
    IndieWeb.
⋯""",
                                },
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


@freeze_time("2024-01-01 00:00:00")
async def test_category_conditional_get(
    client: testing.QuartClient,
    current_app: Quart,
) -> None:
    """
    Test conditional GETs in the category endpoint.
    """
    await load_entries(current_app)
    response = await client.get(
        "/category/python",
        headers={
            "If-None-Match": "e4f00d1a3dc8c3ed4289ba94cbdc9b3143b55fc7352002b2a98baa7569a67532"
        },
    )

    assert response.status_code == 304
