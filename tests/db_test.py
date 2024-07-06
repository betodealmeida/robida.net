"""
Tests for the DB functions
"""

# pylint: disable=line-too-long

import json

from freezegun import freeze_time
from quart import Quart

from robida.db import get_db, load_entries


@freeze_time("2024-01-01 00:00:00")
async def test_load_entries(current_app: Quart) -> None:
    """
    Test `load_entries`.
    """
    await load_entries(current_app)

    async with get_db(current_app) as db:
        async with db.execute("SELECT * FROM entries") as cursor:
            rows = await cursor.fetchall()

    assert [dict(row) for row in rows] == [
        {
            "uuid": "1d4f24cc8c6a442e8a42bc208cb16534",
            "published": 1,
            "visibility": "public",
            "sensitive": 0,
            "author": "http://example.com/",
            "location": "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
            "content": json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "url": [
                            "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534"
                        ],
                        "uid": ["1d4f24cc-8c6a-442e-8a42-bc208cb16534"],
                        "content": ["Hello, world!"],
                        "published": ["2024-01-01T00:00:00+00:00"],
                        "author": [
                            {
                                "type": ["h-card"],
                                "properties": {
                                    "name": ["Beto Dealmeida"],
                                    "url": ["http://example.com/"],
                                },
                            }
                        ],
                        "category": ["note"],
                    },
                },
                separators=(",", ":"),
            ),
            "read": 0,
            "deleted": 0,
            "created_at": "2024-01-01 00:00:00+00:00",
            "last_modified_at": "2024-01-01 00:00:00+00:00",
        },
        {
            "uuid": "37c9ed455c0c43e4b0880e904ed849d7",
            "published": 1,
            "visibility": "public",
            "sensitive": 0,
            "author": "http://example.com/",
            "location": "http://example.com/feed/37c9ed45-5c0c-43e4-b088-0e904ed849d7",
            "content": json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "url": [
                            "http://example.com/feed/37c9ed45-5c0c-43e4-b088-0e904ed849d7"
                        ],
                        "uid": ["37c9ed45-5c0c-43e4-b088-0e904ed849d7"],
                        "content": ["Hello, world!"],
                        "published": ["2024-01-01T00:00:00+00:00"],
                        "author": [
                            {
                                "type": ["h-card"],
                                "properties": {
                                    "name": ["Beto Dealmeida"],
                                    "url": ["http://example.com/"],
                                },
                            }
                        ],
                        "category": ["note"],
                    },
                },
                separators=(",", ":"),
            ),
            "read": 0,
            "deleted": 1,
            "created_at": "2024-01-01 00:00:00+00:00",
            "last_modified_at": "2024-01-01 00:00:00+00:00",
        },
        {
            "uuid": "8bf10ecebe184b96af9104e5c2a931ad",
            "published": 1,
            "visibility": "public",
            "sensitive": 0,
            "author": "http://example.com/",
            "location": "http://example.com/feed/8bf10ece-be18-4b96-af91-04e5c2a931ad",
            "content": json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "name": ["About"],
                        "url": [
                            "http://example.com/feed/8bf10ece-be18-4b96-af91-04e5c2a931ad"
                        ],
                        "uid": ["8bf10ece-be18-4b96-af91-04e5c2a931ad"],
                        "content": [
                            {
                                "value": (
                                    "This blog runs a custom-built Python web framework "
                                    "called\n    Robida, built for the\n    IndieWeb."
                                ),
                                "html": """<p>
    This blog runs a custom-built Python web framework called
    <a href="https://github.com/betodealmeida/robida.net/">Robida</a>, built for the
    <a href="https://indieweb.org/">IndieWeb</a>.
</p>""",
                            }
                        ],
                        "summary": ["About this blog."],
                        "published": ["2024-01-01T00:00:00+00:00"],
                        "author": [
                            {
                                "type": ["h-card"],
                                "properties": {
                                    "name": ["Beto Dealmeida"],
                                    "url": ["http://example.com/"],
                                },
                            }
                        ],
                        "category": ["about", "blog", "python"],
                    },
                },
                separators=(",", ":"),
            ),
            "read": 0,
            "deleted": 0,
            "created_at": "2024-01-01 00:00:00+00:00",
            "last_modified_at": "2024-01-01 00:00:00+00:00",
        },
        {
            "uuid": "68e50fbd69c04e12bf2f208ace952ffd",
            "published": 1,
            "visibility": "public",
            "sensitive": 0,
            "author": "http://alice.example.com",
            "location": "http://alice.example.com/post/1",
            "content": json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "url": ["http://alice.example.com/post/1"],
                        "uid": ["68e50fbd-69c0-4e12-bf2f-208ace952ffd"],
                        "in-reply-to": [
                            "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534"
                        ],
                        "content": ["Welcome!"],
                        "published": ["2024-01-01T00:00:00+00:00"],
                        "author": [
                            {
                                "type": ["h-card"],
                                "properties": {
                                    "name": ["Alice"],
                                    "url": ["http://alice.example.com"],
                                },
                            }
                        ],
                    },
                },
                separators=(",", ":"),
            ),
            "read": 0,
            "deleted": 0,
            "created_at": "2024-01-01 00:00:00+00:00",
            "last_modified_at": "2024-01-01 00:00:00+00:00",
        },
        {
            "uuid": "9911109126c74e3ea0be436fbeee0d14",
            "published": 1,
            "visibility": "public",
            "sensitive": 0,
            "author": "http://example.com/",
            "location": "http://example.com/feed/99111091-26c7-4e3e-a0be-436fbeee0d14",
            "content": json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "url": [
                            "http://example.com/feed/99111091-26c7-4e3e-a0be-436fbeee0d14"
                        ],
                        "uid": ["99111091-26c7-4e3e-a0be-436fbeee0d14"],
                        "in-reply-to": ["http://alice.example.com/post/1"],
                        "content": ["Thank you!"],
                        "published": ["2024-01-01T00:00:00+00:00"],
                        "author": [
                            {
                                "type": ["h-card"],
                                "properties": {
                                    "name": ["Beto Dealmeida"],
                                    "url": ["http://example.com/"],
                                },
                            }
                        ],
                        "category": ["note"],
                    },
                },
                separators=(",", ":"),
            ),
            "read": 0,
            "deleted": 0,
            "created_at": "2024-01-01 00:00:00+00:00",
            "last_modified_at": "2024-01-01 00:00:00+00:00",
        },
    ]
