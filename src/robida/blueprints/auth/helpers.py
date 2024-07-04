"""
Helpers for RelMeAuth.
"""

from typing import Any, Callable
from functools import wraps

import httpx
from bs4 import BeautifulSoup
from quart import Response, request, session
from quart.helpers import make_response, redirect, url_for


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


def protected(f: Callable[..., Response]) -> Callable[..., Response]:
    """
    Decorator that checks if the request comes from us.
    """

    @wraps(f)
    async def decorated_function(*args: Any, **kwargs: Any) -> Response:
        me = url_for("homepage.index", _external=True)

        if "me" not in session:
            session["next"] = request.url
            return redirect(url_for("auth.login"))

        if session["me"] != me:
            return await make_response("insufficient_scope", 403)

        return await f(*args, **kwargs)

    return decorated_function
