"""
Tests for the search helper function.
"""

from datetime import datetime, timezone
from uuid import UUID

from freezegun import freeze_time
from quart import Quart

from robida.blueprints.search.helpers import search_entries
from robida.db import load_entries
from robida.models import Entry, Microformats2


@freeze_time("2024-01-01 00:00:00")
async def test_search(current_app: Quart) -> None:
    """
    Test the search backend.
    """
    await load_entries(current_app)

    async with current_app.app_context():
        async with current_app.test_request_context("/", method="GET"):
            entries = await search_entries("world")

    assert entries == [
        Entry(
            uuid=UUID("1d4f24cc-8c6a-442e-8a42-bc208cb16534"),
            author="http://example.com/",
            location="http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
            content=Microformats2(
                type=["h-entry"],
                properties={
                    "url": [
                        "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534"
                    ],
                    "uid": ["1d4f24cc-8c6a-442e-8a42-bc208cb16534"],
                    "content": ["Hello, world!"],
                    "category": ["note"],
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
                children=[],
            ),
            read=False,
            deleted=False,
            created_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            last_modified_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        )
    ]


@freeze_time("2024-01-01 00:00:00")
async def test_search_invalid_query(current_app: Quart) -> None:
    """
    Test the search endpoint with an invalid match query.
    """
    await load_entries(current_app)

    async with current_app.app_context():
        async with current_app.test_request_context("/", method="GET"):
            entries = await search_entries("(world OR hello) there")

    assert entries == [
        Entry(
            uuid=UUID("1d4f24cc-8c6a-442e-8a42-bc208cb16534"),
            author="http://example.com/",
            location="http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
            content=Microformats2(
                type=["h-entry"],
                properties={
                    "url": [
                        "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534"
                    ],
                    "uid": ["1d4f24cc-8c6a-442e-8a42-bc208cb16534"],
                    "content": ["Hello, world!"],
                    "category": ["note"],
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
                children=[],
            ),
            read=False,
            deleted=False,
            created_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            last_modified_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        )
    ]
