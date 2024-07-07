"""
Tests for models.
"""

from datetime import datetime, timezone
from uuid import UUID

import mf2py
from freezegun import freeze_time
from quart import Quart

from robida.models import Entry, HCard


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


async def test_hcard(current_app: Quart) -> None:
    """
    Test the HCard class.

    In this test we make sure that the rendered HTML contains the exact same
    """
    payload = {
        "properties": {"name": ["Beto Dealmeida"], "url": ["https://robida.net/"]},
        "type": ["h-card"],
    }
    hcard = HCard(**payload)

    async with current_app.app_context():
        html = await hcard.render()

    parsed = mf2py.parse(html)
    assert parsed["items"][0] == payload


async def test_hcard_complete(current_app: Quart) -> None:
    """
    Test the HCard class.

    In this test we make sure that the rendered HTML contains the exact same
    """
    payload = {
        "type": ["h-card"],
        "properties": {
            "name": ["Sally Ride"],
            "honorific-prefix": ["Dr."],
            "given-name": ["Sally"],
            "additional-name": ["K."],
            "family-name": ["Ride"],
            "honorific-suffix": ["Ph.D."],
            "nickname": ["sallykride"],
            "org": ["Sally Ride Science"],
            "photo": ["http://example.com/sk.jpg"],
            "url": ["http://sally.example.com"],
            "email": ["mailto:sally@example.com"],
            "tel": ["+1.818.555.1212"],
            "street-address": ["123 Main st."],
            "locality": ["Los Angeles"],
            "region": ["California"],
            "postal-code": ["91316"],
            "country-name": ["U.S.A"],
            "bday": ["1951-05-26"],
            "category": ["physicist"],
            "note": ["First American woman in space."],
        },
    }

    hcard = HCard(**payload)

    async with current_app.app_context():
        html = await hcard.render()

    parsed = mf2py.parse(html)
    assert parsed["items"][0] == payload
