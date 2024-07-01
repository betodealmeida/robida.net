"""
Generic helper functions.
"""

import base64
import hashlib
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from uuid import UUID, uuid4

import httpx
import mf2py
from aiosqlite import Connection
from bs4 import BeautifulSoup, NavigableString, Tag
from quart import current_app
from quart.helpers import url_for

from robida.models import Entry, Microformats2

# inspired by Mastodon
SUMMARY_LENGTH = 500


# pylint: disable=too-few-public-methods
class XForwardedProtoMiddleware:
    """
    Middleware for generating https link when behind a reverse proxy.
    """

    def __init__(
        self,
        app: Callable[
            [
                dict[str, Any],
                Callable[..., Awaitable[dict[str, Any]]],
                Callable[..., Awaitable[None]],
            ],
            Awaitable[None],
        ],
    ) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        if scope["type"] == "http":
            headers = dict(scope["headers"])
            if b"x-forwarded-proto" in headers:
                scope["scheme"] = headers[b"x-forwarded-proto"].decode("latin-1")

        await self.app(scope, receive, send)


async def upsert_entry(db: Connection, hentry: Microformats2) -> Entry:
    """
    Create/update an entry in the database from an h-entry.
    """
    uuid = UUID(hentry.properties["uid"][0])

    author = location = hentry.properties["url"][0]
    if hcard := hentry.properties.get("author"):
        if url := hcard[0]["properties"].get("url"):
            author = url[0]

    try:
        created_at = datetime.fromisoformat(hentry.properties["published"][0])
    except (KeyError, ValueError):
        created_at = datetime.now(timezone.utc)

    try:
        last_modified_at = datetime.fromisoformat(hentry.properties["updated"][0])
    except (KeyError, ValueError):
        last_modified_at = created_at

    await db.execute(
        """
INSERT INTO entries (
    uuid,
    author,
    location,
    content,
    read,
    deleted,
    created_at,
    last_modified_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(uuid) DO UPDATE SET
    author = excluded.author,
    location = excluded.location,
    content = excluded.content,
    read = FALSE,
    deleted = FALSE,
    last_modified_at = excluded.last_modified_at;
        """,
        (
            uuid.hex,
            author,
            location,
            hentry.model_dump_json(exclude_unset=True),
            False,
            False,
            created_at,
            last_modified_at,
        ),
    )
    await db.execute(
        "INSERT INTO documents (uuid, content) VALUES (?, ?);",
        (
            uuid.hex,
            hentry.model_dump_json(exclude_unset=True),
        ),
    )
    await db.commit()

    return Entry(
        uuid=uuid,
        author=author,
        location=location,
        content=hentry,
        read=False,
        deleted=False,
        created_at=created_at,
        last_modified_at=last_modified_at,
    )


def new_hentry() -> Microformats2:
    """
    Create a new entry.
    """
    uuid = uuid4()
    created_at = last_modified_at = datetime.now(timezone.utc)
    url = url_for("feed.entry", uuid=str(uuid), _external=True)
    hcard = get_hcard()

    properties = {
        "author": [hcard.model_dump()],
        "published": [created_at.isoformat()],
        "updated": [last_modified_at.isoformat()],
        "url": [url],
        "uid": [str(uuid)],
    }

    return Microformats2(type=["h-entry"], properties=properties)


def get_hcard() -> Microformats2:
    """
    Build our h-card.
    """
    return Microformats2(
        type=["h-card"],
        value=url_for("homepage.index", _external=True),
        properties={
            "name": [current_app.config["NAME"]],
            "url": [url_for("homepage.index", _external=True)],
            "photo": [
                {
                    "alt": current_app.config["PHOTO_DESCRIPTION"],
                    "value": url_for(
                        "static",
                        filename="img/photo.jpg",
                        _external=True,
                    ),
                },
            ],
            "email": [current_app.config["EMAIL"]],
            "note": [current_app.config["NOTE"]],
        },
    )


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

        if "like-of" in data.properties:
            return '<span title="A like (h-entry)">❤️</span>'

        if "bookmark-of" in data.properties:
            return '<span title="A bookmark (h-entry)">🔖</span>'

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
        html = mf2py.Parser(response.content.decode(), url=url)

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


def summarize(html: str, max_length: int = SUMMARY_LENGTH) -> str:
    """
    Summarize HTML, making it shorter.

    This is used when showing entries in the feed/search/cateegory pages.
    """
    soup = BeautifulSoup(html.strip(), "html.parser")
    truncated = truncate_html(soup, max_length)

    return str(truncated)


def truncate_html(element: Tag, max_length: int) -> Tag:
    """
    Truncate an HTML element to a maximum length, considering its text.

    This returns a tuple with the truncated HTML and a boolean indicating if the
    truncation was necessary.
    """
    acc = i = 0
    for i, child in enumerate(element.contents):
        size = len(child.get_text())
        if acc + size <= max_length:
            acc += size
            continue

        new_child = child
        if isinstance(child, NavigableString):
            new_child = child[: max_length - acc] + "⋯"
        elif isinstance(child, Tag):
            new_child = truncate_html(child, max_length - acc)

        child.replace_with(new_child)
        break

    # delete leftover children
    element.contents = element.contents[: i + 1]

    return element
