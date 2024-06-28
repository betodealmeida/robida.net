"""
Generic helper functions.
"""

import base64
import hashlib
import urllib.parse
from datetime import datetime
from typing import Any

import httpx
import mf2py
from bs4 import BeautifulSoup

from robida.models import Microformats2


def extract_text_from_html(html: str) -> str:
    """
    Extract text from HTML.
    """
    return BeautifulSoup(html, "html.parser").get_text()


def get_type_emoji(data: dict[str, Any]) -> str:
    """
    Get the emoji for the type of the data.
    """
    data = Microformats2(**data)

    if data.type[0] == "h-entry":
        if "in-reply-to" in data.properties:
            return '<span title="A reply (h-entry)">💬</span>'

        if "name" in data.properties:
            return '<span title="An article (h-entry)">📄</span>'

        return '<span title="A note (h-entry)">📔</span>'

    return '<span title="A generic post">📝</span>'


async def fetch_hcard(url: str) -> dict[str, Any]:
    """
    Fetch an h-card from an URL.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        html = mf2py.Parser(response.content.decode())

    if cards := html.to_dict(filter_by_type="h-card"):
        return cards[0]

    return {
        "type": ["h-card"],
        "properties": {
            "name": [url],
            "url": [url],
        },
    }


def iso_to_rfc822(iso: str) -> str:
    """
    Convert an ISO 8601 date to RFC 822.
    """
    return datetime.fromisoformat(iso).strftime("%a, %d %b %Y %H:%M:%S %z")


def rfc822_to_iso(rfc822: str) -> str:
    """
    Convert an RFC 822 date to ISO 8601.
    """
    return datetime.strptime(rfc822, "%a, %d %b %Y %H:%M:%S %z").isoformat()


def canonicalize_url(url: str) -> str:
    """
    Apply URL canonicalization.

    https://indieauth.spec.indieweb.org/#url-canonicalization
    """
    parsed = urllib.parse.urlparse(url)

    # Set a scheme if not present; note that when scheme is empty the whole URL is
    # considered a path, so we need to adjust the `netloc` and `path` accordingly.
    if not parsed.scheme:
        if "/" in parsed.path:
            netloc, path = parsed.path.split("/", 1)
        else:
            netloc, path = parsed.path, "/"

        parsed = parsed._replace(
            scheme="https",
            netloc=netloc,
            path=path,
        )

    # make sure domain is lowercase
    parsed = parsed._replace(netloc=parsed.netloc.lower())

    # make sure path is at least "/"
    if not parsed.path:
        parsed = parsed._replace(path="/")

    return parsed.geturl()


def compute_challenge(code_verifier: str, code_challenge_method: str) -> str:
    """
    Compute the challenge from the code verifier and method.
    """
    if code_challenge_method == "plain":
        return code_verifier

    if code_challenge_method == "S256":
        return compute_s256_challenge(code_verifier)

    raise ValueError("Invalid code challenge method")


def compute_s256_challenge(code_verifier: str) -> str:
    """
    Compute the S256 challenge from the code verifier.

    https://tools.ietf.org/html/rfc7636#section-4.2
    """
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    encoded = base64.urlsafe_b64encode(digest)
    code_challenge = encoded.rstrip(b"=").decode("utf-8")

    return code_challenge
