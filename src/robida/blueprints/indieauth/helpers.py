"""
Helper functions.
"""

import urllib.parse
from typing import Any

import httpx
import mf2py
from bs4 import BeautifulSoup


async def get_client_info(client_id: str) -> tuple[dict[str, Any], set[str]]:
    """
    Get information about the IndieAuth client.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(client_id)
        html = response.text

    app_info = {}
    metadata = mf2py.parse(doc=html)
    for item in metadata["items"]:
        if "h-card" in item["type"]:
            app_info = item["properties"]
            break

    app_info.setdefault("name", [client_id])
    app_info.setdefault("url", [client_id])

    # ensure URLs are absolute
    for key in ["logo", "url", "photo"]:
        if key in app_info:
            app_info[key] = [
                urllib.parse.urljoin(client_id, url) for url in app_info[key]
            ]

    # find redirect URIs
    redirect_uris = {
        link["url"] for link in response.links.values() if link["rel"] == "redirect_uri"
    }

    soup = BeautifulSoup(html, "html.parser")
    redirect_uris.update(
        urllib.parse.urljoin(client_id, link["href"])
        for link in soup.find_all("link", rel="redirect_uri")
    )

    return app_info, redirect_uris
