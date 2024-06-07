"""
Helpers for RelMeAuth.
"""

import httpx
from bs4 import BeautifulSoup


async def get_soup(url: str) -> BeautifulSoup:
    """
    Fetch and parse the HTML of a given URL.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        html = response.text

    return BeautifulSoup(html, "html.parser")


async def get_profiles(url: str) -> list[str]:
    """
    Fetch all `rel="me"` profiles from a given URL.
    """
    soup = await get_soup(url)
    profiles = []
    for anchor in soup.find_all("a", rel="me"):
        href = anchor.attrs.get("href")

        if href.startswith("mailto:"):
            profiles.append(href)

        if href.startswith("https://") or href.startswith("http://"):
            # check that the URL has a backlink
            soup = await get_soup(href)
            if soup.find("a", href=url):
                profiles.append(href)

    return profiles
