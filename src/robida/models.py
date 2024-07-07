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
import pyromark
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from quart import current_app, url_for


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
    Microformats 2 JSON.

    See http://microformats.org/wiki/microformats2-json.
    """

    # The expected Microformats2 h-type, for derived classes.
    htype: ClassVar[str]

    # Fields every Microformats2 should have.
    type: list[str]
    value: str | None = None
    properties: Annotated[dict[str, Any], Field(default_factory=dict)]
    children: Annotated[list[Microformats2], Field(default_factory=list)]

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
    def from_json(cls, json: str) -> Microformats2:
        """
        Create a microformat from a JSON string.
        """
        microformats = [
            Checkin,
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
    An h-card.

    See https://microformats.org/wiki/h-card.
    """

    htype: ClassVar[str] = "h-card"

    type: Annotated[list[str], Field(default_factory=lambda: ["h-card"])]

    @field_validator("properties")
    @classmethod
    def ensure_name(cls, v: dict[str, Any]) -> dict[str, Any]:
        """
        Ensure there is at least one name.
        """
        if "name" in v and isinstance(v["name"], list) and len(v["name"]) > 0:
            return v

        raise ValueError("No name provided")

    @classmethod
    async def from_url(cls, url: str) -> HCard:
        """
        Create an h-card from a URL.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            html = mf2py.Parser(response.content.decode(), url=url)

        for payload in html.to_dict(filter_by_type="h-card"):
            if payload.get("properties", {}).get("url") == url:
                return cls(**payload)

        return cls(properties={"name": [url], "url": [url]})


def hentry_properties() -> dict[str, Any]:
    """
    Build basic h-entry properties.
    """
    uuid = uuid4()
    created_at = last_modified_at = datetime.now(timezone.utc)
    url = url_for("feed.entry", uuid=str(uuid), _external=True)

    return {
        "url": [url],
        "uid": [str(uuid)],
        "post-status": ["published"],
        "visibility": ["public"],
        "sensitive": ["false"],
        "published": [created_at.isoformat()],
        "updated": [last_modified_at.isoformat()],
    }


class HEntry(Microformats2):
    """
    An h-entry.

    See https://microformats.org/wiki/h-entry.
    """

    htype: ClassVar[str] = "h-entry"

    # The property that defines the type of the post.
    property_name: ClassVar[str]

    # Special class attributes to render the entry and build CRUD forms.
    template: ClassVar[str] = "generic"
    description: ClassVar[str] = "A generic entry"
    emoji: ClassVar[str] = "📝"

    type: Annotated[list[str], Field(default_factory=lambda: ["h-entry"])]
    properties: Annotated[dict[str, Any], Field(default_factory=hentry_properties)]

    @field_validator("properties")
    @classmethod
    def ensure_post_type(cls, v: dict[str, Any]) -> dict[str, Any]:
        """
        Check that the payload has the property that defines the post type.
        """
        # Base class, no property to check...
        if not hasattr(cls, "property_name"):
            return v

        type_property = v["properties"].get(cls.property_name)
        if not isinstance(type_property, list) or not len(type_property) > 0:
            raise ValueError("Not a valid type")

        return v

    @model_validator(mode="before")
    @classmethod
    def pre_root(cls, values: dict[str, Any]) -> dict[str, Any]:
        """
        Set a CRUD template and make sure all content is HTML.
        """
        values["post-template"] = cls.template

        queue = [values]
        while queue:
            item = queue.pop(0)
            if content := item["properties"].get("content"):
                if isinstance(content, str):
                    content = content.strip()
                    item["properties"]["content"] = {
                        "value": content,
                        "html": pyromark.markdown(content),
                    }
                elif (
                    isinstance(content, dict)
                    and "value" in content
                    and "html" not in content
                ):
                    content["html"] = pyromark.markdown(content["value"])

            # traverse chidlren
            queue.extend(item.get("children", []))

            # traverse properties
            for value in item["properties"].values():
                if isinstance(value, list):
                    queue.extend(item for item in value if isinstance(item, dict))

        return values


async def parse_geo_checkin(checkin: str) -> HCard:
    """
    Parse IndiePass geo check-in format.

    IndiePass sets the checking to a geocoded string that looks like this:

        geo:35.6,-70.1,-24.7;name=X;url=Y

    """
    properties: dict[str, Any] = {
        "value": checkin,
    }

    geo, *metadata = checkin.split(";")

    keys = ["latitude", "longitude", "altitude"]
    coordinates = geo.split(":", 1)[1].split(",")
    properties.update({key: [value] for key, value in zip(keys, coordinates)})

    for pair in metadata:
        if "=" in pair:
            key, value = pair.split("=", 1)
            properties[key] = [value]

    if url := properties.get("url"):
        hcard = await HCard.from_url(url[0])
        hcard.properties.update(properties)
    else:
        hcard = HCard(properties=properties)

    return hcard


class Checkin(HEntry):
    """
    A check-in.

    See https://indieweb.org/checkin.
    """

    property_name: ClassVar[str] = "checkin"

    template: ClassVar[str] = "checkin"
    description: ClassVar[str] = "A check-in"
    emoji: ClassVar[str] = "🚩"

    @model_validator(mode="before")
    @classmethod
    def pre_root(cls, values: dict[str, Any]) -> dict[str, Any]:
        """
        Make sure we have a proper h-card with coordinates.
        """
        values = super().pre_root(values)

        # ensure checkin is an h-card
        values["properties"]["checkin"] = [
            cls.generate_hcard(checkin) for checkin in values["properties"]["checkin"]
        ]

        # copy content to the checkin, since IndiePass puts it in the root of the h-entry
        if "content" in values["properties"]:
            for checkin in values["properties"]["checkin"]:
                checkin.properties.sedefault("content", values["properties"]["content"])

        return values

    @staticmethod
    async def generate_hcard(checkin: str | dict[str, Any]) -> HCard:
        """
        Ensure the check-in is an h-card.
        """
        if isinstance(checkin, dict):
            return HCard(**checkin)

        if checkin.startswith("geo:"):
            return await parse_geo_checkin(checkin)

        return HCard(properties={"name": [checkin]})
