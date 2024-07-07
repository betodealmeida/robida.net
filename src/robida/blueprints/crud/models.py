"""
CRUD-related models.
"""

import json
from dataclasses import dataclass
from typing import Any

import httpx
import mf2py
import pyromark
from bs4 import BeautifulSoup, Tag

from robida.helpers import get_post_author
from robida.models import HCard, HCite, HEntry, HGeo


@dataclass
class TemplateRequest:
    """
    Represents a template request.
    """

    template: str


@dataclass
class GenericPayload:
    """
    Represents a generic payload from an unknown type.
    """

    properties: str

    async def to_hentry(self) -> HEntry:
        """
        Convert the payload to an h-entry.
        """
        hentry = HEntry()

        # ignore keys that are updated from the UI
        hentry.properties = {
            key: value
            for key, value in json.loads(self.properties).items()
            if key not in {"post-status", "visibility", "sensitive"}
        }

        return hentry


@dataclass
class ArticlePayload:
    """
    Payload from a new article.
    """

    # required
    title: str
    content: str

    # optional
    summary: str | None = None
    category: str | None = None

    async def to_hentry(self) -> HEntry:
        """
        Convert the payload to an h-entry.
        """
        hentry = HEntry()

        hentry.properties["content"] = [
            {
                "html": pyromark.markdown(self.content.strip()).strip(),
                "value": self.content.strip(),
            }
        ]

        if self.summary:
            hentry.properties["summary"] = [
                {
                    "html": pyromark.markdown(self.summary.strip()).strip(),
                    "value": self.summary.strip(),
                }
            ]

        if self.category:
            hentry.properties["category"] = [
                category.strip() for category in self.category.split(",")
            ]

        hentry.properties["name"] = [self.title.strip()]

        return hentry


@dataclass
class MetadataType:
    """
    Metadata extracted from a liked/bookmarked URL.
    """

    title: list[str]
    author: list[HCard]
    content: list[str | dict[str, Any]]


@dataclass
class ExternalSitePayload:
    """
    Payload from posts that reference an external site.
    """

    # required
    url: str

    # optional
    title: str | None = None

    async def get_metadata(self) -> MetadataType:
        """
        Get metadata from the external site.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.url, follow_redirects=True)
                response.raise_for_status()
            except httpx.HTTPStatusError:
                return MetadataType(title=[], author=[], content=[])
        soup = BeautifulSoup(response.text, "html.parser")
        parsed = mf2py.parse(response.text, url=self.url)

        return MetadataType(
            title=self._get_title(soup, parsed),
            author=await get_post_author(self.url),
            content=self._get_content(soup, parsed),
        )

    def _get_title(
        self,
        soup: Tag,
        parsed: dict[str, Any],
    ) -> list[str | dict[str, Any]]:
        """
        Get the title of the external site.
        """
        if self.title:
            return [self.title]

        if len(parsed["items"]) == 1 and "name" in parsed["items"][0]["properties"]:
            return parsed["items"][0]["properties"]["name"]

        meta_tags = [
            ("name", "title"),
            ("property", "og:title"),
            ("name", "twitter:title"),
        ]
        for attribute, value in meta_tags:
            meta = soup.find("meta", {attribute: value})
            if meta and meta.get("content"):
                return [meta.get("content")]

        if title := soup.title:
            return [title.text]

        return [self.url]

    def _get_content(
        self,
        soup: Tag,
        parsed: dict[str, Any],
    ) -> list[str | dict[str, Any]]:
        """
        Get the content of the external site.
        """
        if len(parsed["items"]) == 1 and "content" in parsed["items"][0]["properties"]:
            return parsed["items"][0]["properties"]["cotent"]

        meta_tags = [
            ("name", "description"),
            ("property", "og:description"),
            ("name", "twitter:description"),
        ]
        for attribute, value in meta_tags:
            meta = soup.find("meta", {attribute: value})
            if meta and meta.get("content"):
                return [meta.get("content")]

        return [
            {
                "html": '<a href="{url}">{url}</a>'.format(url=self.url),
                "value": self.url,
            },
        ]


@dataclass
class BookmarkPayload(ExternalSitePayload):
    """
    Payload from a new bookmark.
    """

    # optional
    category: str | None = None

    async def to_hentry(self) -> HEntry:
        """
        Convert the payload to an h-entry.
        """
        hentry = HEntry()

        metadata = await self.get_metadata()
        hentry.properties.update(
            {
                "name": metadata.title,
                "summary": [f"Bookmark of {self.url}"],
                "bookmark-of": [
                    HCite(
                        value=self.url,
                        properties={
                            "url": [self.url],
                            "author": metadata.author or [self.url],
                            "content": metadata.content,
                        },
                    ),
                ],
            }
        )

        if self.category:
            hentry.properties["category"] = [
                category.strip() for category in self.category.split(",")
            ]

        return hentry


@dataclass
class LikePayload(ExternalSitePayload):
    """
    Payload from a new like.
    """

    async def to_hentry(self) -> HEntry:
        """
        Convert the payload to an h-entry.
        """
        hentry = HEntry()

        metadata = await self.get_metadata()
        hentry.properties.update(
            {
                "name": metadata.title,
                "summary": [f"Like of {self.url}"],
                "like-of": [
                    HCite(
                        value=self.url,
                        properties={
                            "url": [self.url],
                            "author": metadata.author,
                            "content": metadata.content,
                        },
                    ),
                ],
            }
        )

        return hentry


@dataclass
class NotePayload:
    """
    Payload from a new note.
    """

    # required
    content: str

    # optional
    category: str | None = None

    async def to_hentry(self) -> HEntry:
        """
        Convert the payload to an h-entry.
        """
        hentry = HEntry()

        hentry.properties["content"] = [
            {
                "html": pyromark.markdown(self.content.strip()).strip(),
                "value": self.content.strip(),
            }
        ]

        if self.category:
            hentry.properties["category"] = [
                category.strip() for category in self.category.split(",")
            ]

        return hentry


@dataclass
class CheckinPayload:
    """
    A check-in.
    """

    coordinates: str
    name: str | None = None
    url: str | None = None
    content: str | None = None
    category: str | None = None

    async def to_hentry(self) -> HEntry:
        """
        Convert the payload to an h-entry.
        """
        hentry = HEntry()

        if self.content:
            hentry.properties["content"] = [
                {
                    "html": pyromark.markdown(self.content.strip()).strip(),
                    "value": self.content.strip(),
                }
            ]

        if self.category:
            hentry.properties["category"] = [
                category.strip() for category in self.category.split(",")
            ]

        if self.url:
            hcard = await HCard.from_url(self.url)
        else:
            hcard = HCard()

        hentry.properties["checkin"] = [hcard]

        if self.name:
            hentry.properties["name"] = [f"Checkin at {self.name}"]
            hcard.properties["name"] = [self.name]
            hcard.value = self.name
        else:
            hentry.properties["name"] = ["Checkin"]

        if self.coordinates:
            attributes = ["latitude", "longitude", "altitude"]
            hcard.properties["geo"] = [
                HGeo(
                    properties={
                        attribute: [value.strip()]
                        for attribute, value in zip(
                            attributes, self.coordinates.split(",")
                        )
                    },
                    value=self.coordinates,
                )
            ]

        return hentry
