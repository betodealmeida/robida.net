"""
Generic models for entries and microformats.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

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

    uuid: UUID
    author: str
    location: str
    content: Microformats2
    read: bool = False
    deleted: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    last_modified_at: datetime = Field(default_factory=utcnow)


class Microformats2(BaseModel):
    """
    Microformats 2 JSON.

    See http://microformats.org/wiki/microformats2-json.
    """

    type: list[str]
    properties: dict[str, Any]
    children: list[Microformats2] = Field(default_factory=list)
