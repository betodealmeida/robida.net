"""
Generic models for entries and microformats.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    """
    Return the current datetime in UTC.
    """
    return datetime.now(timezone.utc)


class Entry(BaseModel):
    """
    Entry dataclass.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    uuid: Annotated[UUID, Field(default_factory=uuid4)]
    author: str
    location: str
    content: Microformats2
    read: bool = False
    deleted: bool = False
    created_at: Annotated[datetime, Field(default_factory=utcnow)]
    last_modified_at: Annotated[datetime, Field(default_factory=utcnow)]


class Microformats2(BaseModel):
    """
    Microformats 2 JSON.

    See http://microformats.org/wiki/microformats2-json.
    """

    type: list[str]
    value: str | None = None
    properties: Annotated[dict[str, Any], Field(default_factory=dict)]
    children: Annotated[list[Microformats2], Field(default_factory=list)]
