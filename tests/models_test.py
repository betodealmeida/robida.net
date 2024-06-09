"""
Tests for models.
"""

from datetime import datetime, timezone
from uuid import UUID

from freezegun import freeze_time

from robida.models import Entry


@freeze_time("2024-01-01 00:00:00")
def test_entry_utcnow() -> None:
    """
    Test the `utcnow` factory.
    """
    entry = Entry(
        uuid=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
        author="https://example.com/",
        location="https://example.com/1",
        content={
            "type": ["h-entry"],
            "properties": {
                "name": ["Test"],
                "content": ["Test content."],
            },
        },
    )
    assert entry.created_at == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert entry.last_modified_at == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
