"""
Feed related models.
"""

# pylint: disable=too-many-instance-attributes

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, SerializationInfo, field_serializer
from quart import current_app

JSON_FEED_VERSION = "https://jsonfeed.org/version/1.1"


@dataclass
class FeedRequest:
    """
    Feed request dataclass.
    """

    since: str | None = None
    page: int = 1
    page_size: int = -1

    def __post_init__(self):
        """
        Set default page size.
        """
        if self.page_size == -1:
            self.page_size = int(current_app.config["PAGE_SIZE"])


class JSONFeedAuthor(BaseModel):
    """
    A JSON Feed author.
    """

    name: str | None = None
    url: str | None = None
    avatar: str | None = None


class JSONFeedAttachment(BaseModel):
    """
    An attachment for a JSON Feed item.
    """

    url: str
    mime_type: str
    title: str | None = None
    size_in_bytes: float | None = None
    duration_in_seconds: float | None = None


class JSONFeedItem(BaseModel):
    """
    A JSON Feed item.
    """

    id: UUID
    url: str | None = None
    external_url: str | None = None
    title: str | None = None
    content_html: str | None = None
    content_text: str | None = None
    summary: str | None = None
    image: str | None = None
    banner_image: str | None = None
    date_published: datetime | None = None
    date_modified: datetime | None = None
    authors: Annotated[list[JSONFeedAuthor], Field(default_factory=list)]
    tags: Annotated[list[str], Field(default_factory=list)]
    language: str | None = None
    attachments: Annotated[list[JSONFeedAttachment], Field(default_factory=list)]

    @field_serializer("id")
    def serialize_id(self, id_: UUID, _info: SerializationInfo) -> str:
        """
        Use non-dashed UUIDs.
        """
        return id_.hex


class JSONFeed(BaseModel):
    """
    A JSON Feed.

    https://www.jsonfeed.org/version/1.1/
    """

    title: str
    version: str = JSON_FEED_VERSION
    home_page_url: str | None = None
    feed_url: str | None = None
    description: str | None = None
    user_comment: str | None = None
    next_url: str | None = None
    icon: str | None = None
    favicon: str | None = None
    authors: Annotated[list[JSONFeedAuthor], Field(default_factory=list)]
    language: str | None = None
    expired: bool | None = None
    hubs: Annotated[list[str], Field(default_factory=list)]
    items: Annotated[list[JSONFeedItem], Field(default_factory=list)]
