"""
Tests for the categories helper function.
"""

from datetime import datetime, timezone
from uuid import UUID

from freezegun import freeze_time
from quart import Quart

from robida.blueprints.categories.helpers import list_entries
from robida.db import load_entries
from robida.models import Entry, Microformats2


@freeze_time("2024-01-01 00:00:00")
async def test_categories(current_app: Quart) -> None:
    """
    Test the categories backend.
    """
    await load_entries(current_app)

    async with current_app.app_context():
        entries = await list_entries("python")

    assert entries == [
        Entry(
            uuid=UUID("8bf10ece-be18-4b96-af91-04e5c2a931ad"),
            author="http://example.com/",
            location="http://example.com/feed/8bf10ece-be18-4b96-af91-04e5c2a931ad",
            content=Microformats2(
                type=["h-entry"],
                properties={
                    "name": ["About"],
                    "url": [
                        "http://example.com/feed/8bf10ece-be18-4b96-af91-04e5c2a931ad"
                    ],
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
                    "category": ["blog", "python"],
                },
                children=[],
            ),
            read=False,
            deleted=False,
            created_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            last_modified_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        ),
    ]
