"""
Event handler.

This module provides an event handler, so that different blueprints can register to be
notified when a new entry is created, updated, or deleted.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, DefaultDict, TypeVar

from quart import current_app

from robida.models import Entry


@dataclass
class Event:
    """
    Base class for events.
    """


@dataclass
class EntryCreated(Event):
    """
    Event for when a new post is created.
    """

    new_entry: Entry


@dataclass
class EntryUpdated(Event):
    """
    Event for when a post is updated.
    """

    new_entry: Entry
    old_entry: Entry


@dataclass
class EntryDeleted(Event):
    """
    Event for when a post is deleted.
    """

    old_entry: Entry


T = TypeVar("T", bound=Event)
EventHandler = Callable[[T], Coroutine[Any, Any, None]]
Callbacks = DefaultDict[type[T], list[EventHandler[T]]]


class EventDispatcher:
    """
    Event dispatcher for when posts are created/updated/deleted.
    """

    def __init__(self) -> None:
        self.callbacks: Callbacks = defaultdict(list)

    def register(
        self,
        event_type: type[T],
    ) -> Callable[[EventHandler[T]], EventHandler[T]]:
        """
        Register a callback for an event type.

        Should be used as a decorator:

            @event_dispatcher.register(EntryCreated)
            async def on_entry_created(event: EntryCreated) -> None:
                pass

        """

        def decorator(callback: EventHandler[T]) -> EventHandler[T]:
            self.callbacks[event_type].append(callback)
            return callback

        return decorator

    def dispatch(self, event: Event) -> None:
        """
        Dispatch an event to all registered callbacks.
        """
        for callback in self.callbacks[type(event)]:
            current_app.add_background_task(callback, event)


dispatcher = EventDispatcher()
