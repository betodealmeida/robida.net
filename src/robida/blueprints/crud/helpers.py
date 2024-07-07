"""
Helper functions for the CRUD endpoints.
"""

import json
import urllib.parse
from typing import Any, Callable, Coroutine, TypeVar

import httpx
import mf2py
import pyromark
from bs4 import BeautifulSoup, Tag

from robida.blueprints.crud.models import (
    ArticlePayload,
    BookmarkPayload,
    CheckinPayload,
    ExternalSitePayload,
    GenericPayload,
    LikePayload,
    NotePayload,
)
from robida.helpers import new_hentry
from robida.models import Microformats2

T = TypeVar("T")
CreateFunction = Callable[[T], Coroutine[Any, Any, dict[str, Any]]]
CustomPropertiesType = dict[str, tuple[CreateFunction[Any], type[Any]]]


async def create_hentry(data: dict[str, Any]) -> Microformats2:
    """
    Create an h-entry from the CRUD payload.
    """
    template = data.pop("template")
    hentry = new_hentry(
        **{
            "post-template": [template],
            "post-status": [
                "published" if data.pop("published", False) == "on" else "draft"
            ],
            "visibility": [data.pop("visibility")],
            "sensitive": ["true" if data.pop("sensitive", False) == "on" else "false"],
        },
    )
    hentry.properties.update(await get_type_properties(template, data))

    # remove empty properties
    for key, value in list(hentry.properties.items()):
        if not value:
            del hentry.properties[key]

    return hentry


async def update_hentry(
    hentry: Microformats2,
    data: dict[str, Any],
) -> Microformats2:
    """
    Update an existing hentry.
    """
    template = data.pop("template")
    hentry.properties.update(
        {
            "post-template": [template],
            "post-status": [
                "published" if data.pop("published", False) == "on" else "draft"
            ],
            "visibility": [data.pop("visibility")],
            "sensitive": ["true" if data.pop("sensitive", False) == "on" else "false"],
        }
    )
    hentry.properties.update(await get_type_properties(template, data))

    # remove empty properties
    for key, value in list(hentry.properties.items()):
        if not value:
            del hentry.properties[key]

    return hentry


async def get_type_properties(template: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    Get the properties for a specific template.
    """
    custom_properties: CustomPropertiesType = {
        "article": (create_article, ArticlePayload),
        "bookmark": (create_bookmark, BookmarkPayload),
        "checkin": (create_checkin, CheckinPayload),
        "like": (create_like, LikePayload),
        "note": (create_note, NotePayload),
        "generic": (create_generic, GenericPayload),
    }
    if template in custom_properties:
        function, model = custom_properties[template]
        return await function(model(**data))

    return {}


async def create_generic(data: GenericPayload) -> dict[str, Any]:
    """
    Create a generic h-entry.
    """
    return {
        key: value
        for key, value in json.loads(data.properties).items()
        if key not in {"post-status", "visibility", "sensitive"}
    }


async def create_article(data: ArticlePayload) -> dict[str, Any]:
    """
    Create an article.
    """
    html = pyromark.markdown(data.content)

    properties: dict[str, Any] = {
        "name": [data.title],
        "content": [
            {
                "html": html,
                "value": data.content,
            },
        ],
    }
    if data.summary:
        properties["summary"] = [data.summary]
    if data.category:
        properties["category"] = [
            category.strip() for category in data.category.split(",")
        ]

    return properties


async def create_bookmark(data: BookmarkPayload) -> dict[str, Any]:
    """
    Create a bookmark.
    """
    metadata = await get_metadata(data)

    properties: dict[str, Any] = {
        "name": metadata["name"],
        "summary": ["Bookmark of " + data.url],
        "bookmark-of": [
            {
                "type": ["h-cite"],
                "value": data.url,
                "properties": {
                    "url": [data.url],
                    **metadata["post"],
                },
            },
        ],
    }
    if data.category:
        properties["category"] = [
            category.strip() for category in data.category.split(",")
        ]

    return properties


async def create_checkin(data: CheckinPayload) -> dict[str, Any]:
    """
    Create a check-in.
    """
    parts = [data.coordinates]
    if data.name:
        parts.append(f"name={data.name}")
    if data.url:
        parts.append(f"url={data.url}")
    checkin = ";".join(parts)

    properties: dict[str, Any] = {"checkin": [checkin]}
    if data.content:
        html = pyromark.markdown(data.content.strip()).strip()
        properties["content"] = [
            {
                "html": html,
                "value": data.content,
            },
        ]
    if data.category:
        properties["category"] = [
            category.strip() for category in data.category.split(",")
        ]

    return properties


async def create_like(data: LikePayload) -> dict[str, Any]:
    """
    Create a like.
    """
    metadata = await get_metadata(data)

    properties: dict[str, Any] = {
        "name": metadata["name"],
        "summary": ["Like of " + data.url],
        "like-of": [
            {
                "type": ["h-cite"],
                "value": data.url,
                "properties": {
                    "url": [data.url],
                    **metadata["post"],
                },
            },
        ],
    }

    return properties


async def create_note(data: NotePayload) -> dict[str, Any]:
    """
    Create a note.
    """
    html = pyromark.markdown(data.content)

    properties: dict[str, Any] = {
        "name": [],
        "summary": [],
        "content": [
            {
                "html": html,
                "value": data.content,
            },
        ],
    }
    if data.category:
        properties["category"] = [
            category.strip() for category in data.category.split(",")
        ]

    return properties


async def get_metadata(data: ExternalSitePayload) -> dict[str, Any]:
    """
    Get metadata for an external URL: title, author, associated content.
    """
    properties: dict[str, Any] = {"post": {}}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(data.url, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return properties

    soup = BeautifulSoup(response.text, "html.parser")
    parser = mf2py.Parser(response.text, url=data.url)
    hentries = parser.to_dict(filter_by_type="h-entry")
    hcards = parser.to_dict(filter_by_type="h-card")

    properties["name"] = [data.title or get_title(soup, hentries, data.url)]
    properties["post"]["author"] = [get_author(soup, hentries, hcards, data.url)]
    properties["post"]["content"] = [get_content(soup, hentries, data.url)]

    return properties


def get_content(
    soup: Tag,
    hentries: list[dict[str, Any]],
    url: str,
) -> str | dict[str, Any]:
    """
    Extract content.
    """
    if len(hentries) == 1 and "content" in hentries[0]["properties"]:
        return hentries[0]["properties"]["content"][0]

    meta_tags = [
        ("name", "description"),
        ("property", "og:description"),
        ("name", "twitter:description"),
    ]
    for attribute, value in meta_tags:
        meta = soup.find("meta", {attribute: value})
        if meta and meta.get("content"):
            return meta["content"]

    return {
        "html": '<a href="{url}">{url}</a>'.format(url=url),
        "value": url,
    }


def get_title(
    soup: Tag,
    hentries: list[dict[str, Any]],
    url: str,
) -> str | dict[str, Any]:
    """
    Extract title.
    """
    if len(hentries) == 1 and "name" in hentries[0]["properties"]:
        return hentries[0]["properties"]["name"][0]

    meta_tags = [
        ("name", "title"),
        ("property", "og:title"),
        ("name", "twitter:title"),
    ]
    for attribute, value in meta_tags:
        meta = soup.find("meta", {attribute: value})
        if meta and meta.get("content"):
            return meta["content"]

    if title := soup.find("title"):
        return title.get_text()

    return url


def get_author(
    soup: Tag,
    hentries: list[dict[str, Any]],
    hcards: list[dict[str, Any]],
    url: str,
) -> str | dict[str, Any]:
    """
    Extract author.
    """
    if len(hentries) == 1 and "author" in hentries[0]["properties"]:
        return hentries[0]["properties"]["author"][0]

    if len(hcards) == 1:
        return hcards[0]

    if meta := soup.find("meta", {"name": "author"}):
        return meta["content"]

    # set URL as the author, without decoration (should we leave query?)
    return urllib.parse.urlparse(url)._replace(query="", fragment="").geturl()
