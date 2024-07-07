"""
Generic helper functions.
"""

import base64
import hashlib
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from uuid import UUID, uuid4

import httpx
import mf2py
from aiosqlite import Connection
from bs4 import BeautifulSoup, NavigableString, Tag
from quart import current_app
from quart.helpers import url_for

from robida.events import EntryCreated, EntryDeleted, EntryUpdated, dispatcher
from robida.models import Entry, Microformats2

# inspired by Mastodon
SUMMARY_LENGTH = 500


ENTRY_WITH_CHILDREN = """
WITH RECURSIVE linked_entries AS (
    SELECT
        e.uuid,
        e.author,
        e.location,
        e.content,
        e.published,
        e.visibility,
        e.sensitive,
        e.read,
        e.deleted,
        e.created_at,
        e.last_modified_at,
        NULL AS target
    FROM entries e
    WHERE e.uuid = ?

    UNION

    SELECT
        e.uuid,
        e.author,
        e.location,
        e.content,
        e.published,
        e.visibility,
        e.sensitive,
        e.read,
        e.deleted,
        e.created_at,
        e.last_modified_at,
        iw.target AS target
    FROM entries e
    JOIN incoming_webmentions iw ON e.location = iw.source
    JOIN linked_entries le ON iw.target = le.location
    WHERE
        iw.status = 'success' AND
        e.published = TRUE
        {protected}

    UNION

    SELECT
        e.uuid,
        e.author,
        e.location,
        e.content,
        e.published,
        e.visibility,
        e.sensitive,
        e.read,
        e.deleted,
        e.created_at,
        e.last_modified_at,
        ow.target AS target
    FROM entries e
    JOIN outgoing_webmentions ow ON e.location = ow.source
    JOIN linked_entries le ON ow.target = le.location
    WHERE
        ow.status = 'success'
        AND e.published = TRUE
        {protected}
)
SELECT * FROM linked_entries;
"""


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


async def get_entry(
    db: Connection,
    uuid: UUID,
    include_private_children: bool = True,
) -> Entry | None:
    """
    Return an entry with all its replies.
    """
    protected = "" if include_private_children else "AND e.visibility = 'public'"

    async with db.execute(
        ENTRY_WITH_CHILDREN.format(protected=protected),
        (uuid.hex,),
    ) as cursor:
        rows = await cursor.fetchall()

    if not rows:
        return None

    reply_map = defaultdict(list)
    for row in rows:
        reply_map[row["target"]].append(
            Entry(
                uuid=UUID(row["uuid"]),
                author=row["author"],
                location=row["location"],
                content=Microformats2.model_validate_json(row["content"]),
                published=row["published"],
                visibility=row["visibility"],
                sensitive=row["sensitive"],
                read=row["read"],
                deleted=row["deleted"],
                created_at=datetime.fromisoformat(row["created_at"]),
                last_modified_at=datetime.fromisoformat(row["last_modified_at"]),
            )
        )

    root = reply_map[None][0]
    queue = [root]
    seen = set()
    while queue:
        entry = queue.pop(0)
        if entry.uuid in seen:
            continue
        seen.add(entry.uuid)

        replies = reply_map[entry.location]
        entry.content.children.extend(reply.content for reply in replies)
        queue.extend(replies)

    return root


async def upsert_entry(db: Connection, hentry: Microformats2) -> Entry:
    """
    Create/update an entry in the database from an h-entry.
    """
    uuid = UUID(hentry.properties["uid"][0])
    old_entry = await get_entry(db, uuid)

    author = location = hentry.properties["url"][0]
    if hcard := hentry.properties.get("author"):
        if url := hcard[0]["properties"].get("url"):
            author = url[0]

    # "In most implementations, not passing a post-status is assumed to be published."
    # https://indieweb.org/Micropub-extensions#Post_Status
    if "post-status" in hentry.properties:
        published = hentry.properties["post-status"][0] != "draft"
    else:
        published = True

    # "If no visibility is set, a server SHOULD assume the visibility is meant to be
    # public."
    # https://indieweb.org/Micropub-extensions#Visibility
    visibility = (
        hentry.properties["visibility"][0]
        if "visibility" in hentry.properties
        and hentry.properties["visibility"][0] in {"public", "unlisted", "private"}
        else "public"
    )

    sensitive = (
        hentry.properties["sensitive"][0] == "true"
        if "sensitive" in hentry.properties
        else False
    )

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
    published,
    visibility,
    sensitive,
    read,
    deleted,
    created_at,
    last_modified_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(uuid) DO UPDATE SET
    author = excluded.author,
    location = excluded.location,
    content = excluded.content,
    published = excluded.published,
    visibility = excluded.visibility,
    sensitive = excluded.sensitive,
    read = FALSE,
    deleted = FALSE,
    last_modified_at = excluded.last_modified_at;
        """,
        (
            uuid.hex,
            author,
            location,
            hentry.model_dump_json(exclude_unset=True),
            published,
            visibility,
            sensitive,
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

    new_entry = Entry(
        uuid=uuid,
        author=author,
        location=location,
        content=hentry,
        published=published,
        visibility=visibility,
        sensitive=sensitive,
        read=False,
        deleted=False,
        created_at=created_at,
        last_modified_at=last_modified_at,
    )

    dispatcher.dispatch(
        EntryUpdated(old_entry=old_entry, new_entry=new_entry)
        if old_entry
        else EntryCreated(new_entry=new_entry)
    )

    return new_entry


async def delete_entry(db: Connection, entry: Entry) -> None:
    """
    Delete a given entry.
    """
    await db.execute(
        """
UPDATE
    entries
SET
    deleted = TRUE
WHERE
    uuid = ?;
        """,
        (entry.uuid.hex,),
    )
    await db.commit()

    dispatcher.dispatch(EntryDeleted(old_entry=entry))


async def undelete_entry(db: Connection, entry: Entry) -> None:
    """
    Undelete a given entry.
    """
    await db.execute(
        """
UPDATE
    entries
SET
    deleted = FALSE
WHERE
    uuid = ?;
        """,
        (entry.uuid.hex,),
    )
    await db.commit()

    dispatcher.dispatch(EntryCreated(new_entry=entry))


def new_hentry(**kwargs: Any) -> Microformats2:
    """
    Create a new entry.
    """
    uuid = uuid4()
    created_at = last_modified_at = datetime.now(timezone.utc)
    url = url_for("feed.entry", uuid=str(uuid), _external=True)
    hcard = get_hcard()

    properties = {
        "author": [hcard.model_dump()],
        "url": [url],
        "uid": [str(uuid)],
        "post-status": ["published"],
        "visibility": ["public"],
        "sensitive": ["false"],
        "published": [created_at.isoformat()],
        "updated": [last_modified_at.isoformat()],
        **kwargs,
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


def hentry_from_entry(entry: Entry) -> dict[str, Any]:
    """
    Build an h-entry from an entry.
    """
    entry.content.properties.setdefault("uid", [str(entry.uuid)])
    entry.content.properties.setdefault("url", [entry.location])
    entry.content.properties.setdefault(
        "post-status", ["published" if entry.published else "draft"]
    )
    entry.content.properties.setdefault("visibility", [entry.visibility])
    entry.content.properties.setdefault(
        "sensitive", ["true" if entry.sensitive else "false"]
    )
    entry.content.properties.setdefault(
        "published",
        [entry.last_modified_at.isoformat()],
    )

    return entry.content.model_dump()


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
            return '<span title="A reply">💬</span>'

        if "like-of" in data.properties:
            return '<span title="A like">❤️</span>'

        if "bookmark-of" in data.properties:
            return '<span title="A bookmark">🔖</span>'

        if "name" in data.properties:
            return '<span title="An article">📄</span>'

        return '<span title="A note">📔</span>'

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
