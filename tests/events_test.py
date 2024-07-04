"""
Tests for the event dispatcher.
"""

from quart import Quart

from robida.events import EntryCreated, EventDispatcher
from robida.models import Entry, Microformats2


async def test_dispatcher(current_app: Quart) -> None:
    """
    Test the `EventDispatcher` as a decorator.
    """
    dispatcher = EventDispatcher()

    authors = set()

    @dispatcher.register(EntryCreated)
    async def store_author(event: EntryCreated) -> None:
        """
        Simple test function that stores the author of a new entry.
        """
        authors.add(event.new_entry.author)

    event = EntryCreated(
        new_entry=Entry(
            author="http://example.com",
            location="http://example.com/posts/1",
            content=Microformats2(type=["h-entry"]),
        )
    )

    # use `test_app` to ensure background tasks are run
    async with current_app.app_context():
        async with current_app.test_app():
            dispatcher.dispatch(event)

    assert authors == {"http://example.com"}
