"""
Helper functions for the CRUD endpoints.
"""

from typing import Any

import httpx
import mf2py
from bs4 import BeautifulSoup

from robida.helpers import new_hentry
from robida.models import Microformats2


async def create_hentry(data: dict[str, Any]) -> Microformats2:
    """
    Create an h-entry from the CRUD payload.
    """
    hentry = new_hentry()
    template = data["template"]

    if template == "like":
        hentry.properties.update(await create_like(data))

    return hentry


# pylint: disable=too-many-branches
async def create_like(data: dict[str, Any]) -> dict[str, Any]:
    """
    Create a like.
    """
    like_of = {
        "type": ["h-cite"],
        "value": data["url"],
        "properties": {"url": [data["url"]]},
    }
    properties = {
        "summary": ["Like of " + data["url"]],
        "like-of": [like_of],
    }

    title = data["title"]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(data["url"], follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return properties

    parser = mf2py.Parser(response.text, url=data["url"])
    soup = BeautifulSoup(response.text, "html.parser")

    # find content
    content = None
    hentries = parser.to_dict(filter_by_type="h-entry")
    if len(hentries) == 1 and "content" in hentries[0]["properties"]:
        content = hentries[0]["properties"]["content"][0]
    if not content:
        meta = soup.find("meta", property="og:description")
        if meta and meta["content"]:
            content = meta["content"]
    if not content:
        content = {
            "html": '<a href="{url}">{url}</a>'.format(url=data["url"]),
            "value": data["url"],
        }
    like_of["properties"]["content"] = [content]

    # try to set a title
    if not title and len(hentries) == 1 and "name" in hentries[0]["properties"]:
        title = hentries[0]["properties"]["name"][0]
    if not title:
        meta = soup.find("meta", property="og:title")
        if meta and meta["content"]:
            title = meta["content"]
    if not title:
        title = soup.find("title").get_text()
    if not title:
        title = data["url"]
    properties["name"] = [title]

    # find author
    if len(hentries) == 1 and "author" in hentries[0]["properties"]:
        like_of["properties"]["author"] = hentries[0]["properties"]["author"]
    else:
        hcards = parser.to_dict(filter_by_type="h-card")
        if len(hcards) == 1:
            like_of["properties"]["author"] = hcards

    return properties
