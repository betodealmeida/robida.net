"""
Generic models for entries and microformats.

The models ensure that microformats have a consistent schema, so that it's easier to write
templates for them. All the data transformation should only happen when the entries are
read from the database, so that we have the original data as source of truth and the
schemas can evolve more easily.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, ClassVar
from uuid import UUID, uuid4

import httpx
import mf2py
from bs4 import BeautifulSoup
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)
from quart import current_app
from yarl import URL


def is_subset_url(base_url: str, full_url: str) -> bool:
    """
    Checks if `base_url` is a subset of `full_url`.
    """
    base = URL(base_url)
    full = URL(full_url)

    return (
        base.scheme == full.scheme
        and base.host == full.host
        and base.port == full.port
        and full.path.startswith(base.path)
    )


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
    published: bool = True
    visibility: str = "public"
    sensitive: bool = False
    read: bool = False
    deleted: bool = False
    created_at: Annotated[datetime, Field(default_factory=utcnow)]
    last_modified_at: Annotated[datetime, Field(default_factory=utcnow)]


class Microformats2(BaseModel):
    """
    A Microformats2 JSON object.

    This is the canonical output format of the microformats2 parsing algorithm.

    See http://microformats.org/wiki/microformats2-json.
    """

    # The expected Microformats2 h-type, for derived classes.
    htype: ClassVar[str]

    # The microformats2 object is an object with 2 required members named type and
    # properties, as well as an optional member named children:
    type: list[str]
    properties: Annotated[dict[str, list[Any]], Field(default_factory=dict)]
    children: Annotated[list[Microformats2], Field(default_factory=list)]
    # If a microformat2 object is used as the value of a property, it will gain the
    # additional member value to express a plain string representation. If a consuming
    # application does not understand the nested microformat2 object, it can opt to treat
    # it as that string.
    value: str | None = None

    @field_validator("type")
    @classmethod
    def ensure_type(cls, v: dict[str, Any]) -> dict[str, Any]:
        """
        Ensure the payload has the right h-type.
        """
        if hasattr(cls, "htype") and v != [cls.htype]:
            raise ValueError(f"Invalid type, expected {cls.htype}")

        return v

    @classmethod
    async def from_json(cls, json: str) -> Microformats2:
        """
        Create a microformat from a JSON string.
        """
        microformats = [
            HEntry,
            HCard,
            Microformats2,
        ]
        for microformat in microformats:
            try:
                return microformat.model_validate_json(json)
            except ValidationError:
                pass

        raise ValueError("Invalid microformat")

    async def render(self, compact: bool = False) -> str:
        """
        Render the microformat as HTML.
        """
        template = current_app.jinja_env.get_template("feed/microformats2.html")
        html = await template.render_async(data=self, compact=compact)

        return html


class HCard(Microformats2):
    """
    An h-card object.

    See https://microformats.org/wiki/h-card.
    """

    htype: ClassVar[str] = "h-card"

    type: Annotated[list[str], Field(default_factory=lambda: ["h-card"])]

    @classmethod
    async def from_url(cls, url: str) -> HCard:
        """
        Get the representative h-card for a given URL.

        See http://microformats.org/wiki/representative-h-card-parsing.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(str(url))
            parser = mf2py.Parser(response.content.decode(), url=url)

        hcards = [
            HCard(**hcard)
            for hcard in parser.to_dict(filter_by_type="h-card")
            if "url" in hcard["properties"]
        ]

        # If the page contains an h-card with uid and url properties both matching the page
        # URL, the first such h-card is the representative h-card.
        for hcard in hcards:
            if hcard.properties["url"] == [url] and hcard.properties.get("uid") == [
                url
            ]:
                return hcard

        # If no representative h-card was found, if the page contains an h-card with a url
        # property value which also has a rel=me relation (i.e. matches a URL in
        # parse_results.rels.me), the first such h-card is the representative h-card.
        parsed = parser.to_dict()
        rel_mes = parsed["rels"].get("me", [])
        for hcard in hcards:
            if any(hcard_url in rel_mes for hcard_url in hcard.properties["url"]):
                return hcard

        # If no representative h-card was found, if the page contains one single h-card, and
        # the h-card has a url property matching the page URL, that h-card is the
        # representative h-card.
        if len(hcards) == 1 and any(
            hcard_url == url for hcard_url in hcards[0].properties["url"]
        ):
            return hcards[0]

        # If no representative h-card was found, the page has no representative h-card.
        # :(

        # As a last option, we can build a dummy h-card with the URL and maybe name.
        # Let's check for any meta tags with the author name.
        properties = {"url": [url]}
        soup = BeautifulSoup(response.content, "html.parser")
        if meta := soup.find("meta", {"name": "author"}):
            properties["name"] = [meta.get("content")]

        return HCard(properties=properties)


def new_hentry_properties() -> dict[str, Any]:
    """
    Build basic properties for a new h-entry.
    """
    created_at = last_modified_at = datetime.now(timezone.utc)

    return {
        "post-status": ["published"],
        "visibility": ["public"],
        "sensitive": ["false"],
        "published": [created_at.isoformat()],
        "updated": [last_modified_at.isoformat()],
    }


class HEntry(Microformats2):
    """
    An h-entry object.

    See https://microformats.org/wiki/h-entry.
    """

    htype: ClassVar[str] = "h-entry"

    type: Annotated[list[str], Field(default_factory=lambda: ["h-entry"])]
    properties: Annotated[dict[str, Any], Field(default_factory=new_hentry_properties)]


class HGeo(Microformats2):
    """
    An h-geo object.

    See https://microformats.org/wiki/h-geo.
    """

    htype: ClassVar[str] = "h-geo"

    type: Annotated[list[str], Field(default_factory=lambda: ["h-geo"])]


class HCite(Microformats2):
    """
    An h-cite object.

    See https://microformats.org/wiki/h-cite.
    """

    htype: ClassVar[str] = "h-cite"

    type: Annotated[list[str], Field(default_factory=lambda: ["h-cite"])]
