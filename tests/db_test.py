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
            "author": "http://example.com/",
            "location": "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
            "content": json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
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
            "uuid": "8bf10ecebe184b96af9104e5c2a931ad",
            "author": "http://example.com/",
            "location": "http://example.com/feed/8bf10ece-be18-4b96-af91-04e5c2a931ad",
            "content": json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "name": ["Welcome to my blog!"],
                        "content": [
                            {
                                "value": """This blog runs a custom-built Python web framework called
        Robida, built for the
        IndieWeb.""",
                                "html": """<p>
        This blog runs a custom-built Python web framework called
        <a href="https://github.com/betodealmeida/robida.net/">Robida</a>, built for the
        <a href="https://indieweb.org/">IndieWeb</a>.
    </p>""",
                            }
                        ],
                        "summary": ["A quick intro on my blog"],
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
