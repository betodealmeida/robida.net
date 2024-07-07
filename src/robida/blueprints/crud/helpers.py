"""
Helper functions for the CRUD endpoints.
"""

from typing import Any

from robida.blueprints.crud.models import (
    ArticlePayload,
    BookmarkPayload,
    CheckinPayload,
    GenericPayload,
    LikePayload,
    NotePayload,
)
from robida.helpers import get_own_hcard
from robida.models import HEntry


async def create_hentry(data: dict[str, Any]) -> HEntry:
    """
    Create an h-entry from the CRUD payload.
    """
    template = data.pop("template")
    published = data.pop("published", False) == "on"
    visibility = data.pop("visibility")
    sensitive = data.pop("sensitive", False) == "on"

    hcard = get_own_hcard()
    hentry = await build_hentry(template, data)
    hentry.properties.update(
        {
            "author": [hcard.model_dump()],
            "post-template": [template],
            "post-status": ["published" if published else "draft"],
            "visibility": [visibility],
            "sensitive": ["true" if sensitive else "false"],
        }
    )

    return hentry


async def update_hentry(
    hentry: HEntry,
    data: dict[str, Any],
) -> HEntry:
    """
    Update an existing hentry.
    """
    template = data.pop("template")
    published = data.pop("published", False) == "on"
    visibility = data.pop("visibility")
    sensitive = data.pop("sensitive", False) == "on"

    hcard = get_own_hcard()
    new_hentry = await build_hentry(template, data)
    new_hentry.properties.update(
        {
            # preserve these from the original h-entry
            "url": hentry.properties["url"],
            "uid": hentry.properties["uid"],
            "published": hentry.properties["published"],
            # update these from the form
            "author": [hcard.model_dump()],
            "post-template": [template],
            "post-status": ["published" if published else "draft"],
            "visibility": [visibility],
            "sensitive": ["true" if sensitive else "false"],
        }
    )

    return new_hentry


async def build_hentry(template: str, data: dict[str, Any]) -> HEntry:
    """
    Generate the h-entry for a specific template based on the payload data.
    """
    custom_properties = {
        "article": ArticlePayload,
        "bookmark": BookmarkPayload,
        "checkin": CheckinPayload,
        "like": LikePayload,
        "note": NotePayload,
        "generic": GenericPayload,
    }
    if template not in custom_properties:
        return HEntry()

    instance = custom_properties[template](**data)
    return await instance.to_hentry()
