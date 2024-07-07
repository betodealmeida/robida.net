"""
Generic helper functions.
"""

import asyncio
import base64
import hashlib
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx
import mf2py
import yaml
from aiosqlite import Connection
from bs4 import BeautifulSoup, NavigableString, Tag
from bs4.formatter import HTMLFormatter
from quart import current_app
from quart.helpers import url_for

from robida.events import EntryCreated, EntryDeleted, EntryUpdated, dispatcher
from robida.models import Entry, HCard, HEntry

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
                content=HEntry.model_validate_json(row["content"]),
                published=row["published"],
                visibility=row["visibility"],
                sensitive=row["sensitive"],
                read=row["read"],
                deleted=row["deleted"],
                created_at=datetime.fromisoformat(row["created_at"]),
                last_modified_at=datetime.fromisoformat(row["last_modified_at"]),
            )
        )

    # populate children
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


async def upsert_entry(db: Connection, hentry: HEntry) -> Entry:
    """
    Create/update an entry in the database from an h-entry.

    Note that the h-entry might come from a webmention, so it might not follow the
    conventions used in the application.
    """
    # if there's no URL the h-entry cannot be external, and so it MUST be a new h-hentry
    if "url" not in hentry.properties:
        uuid = uuid4()
        old_entry = None
        location = url_for("feed.entry", uuid=str(uuid), _external=True)
        hentry.properties["url"] = hentry.properties["uid"] = [location]

    # if there is a URL, the h-entry might be external and not exist in the DB yet
    else:
        location = hentry.properties["url"][0]

        async with db.execute(
            "SELECT uuid FROM entries WHERE location = ?;",
            (location,),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            uuid = UUID(row["uuid"])
            old_entry = await get_entry(db, uuid)
        else:
            uuid = uuid4()
            old_entry = None

    hcard = await find_hcard(hentry)

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

    # Set a template, if one was not defined. This allows for easier editing on the
    # web UI of entries created from an external MicroPub client.
    template = get_template(hentry)
    hentry.properties.setdefault("post-template", [template])

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
            hcard.properties["url"][0],
            location,
            hentry.model_dump_json(),
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
            hentry.model_dump_json(),
        ),
    )
    await db.commit()

    new_entry = Entry(
        uuid=uuid,
        author=hcard.properties["url"][0],
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


async def find_hcard(hentry: HEntry) -> HCard:
    """
    Find the h-card of an h-entry.

    This function traverses the properties and children of the h-entry to find the
    h-card, if any.
    """
    if "author" in hentry.properties and len(hentry.properties["author"]) == 1:
        return HCard(**hentry.properties["author"][0])

    for child in hentry.children:
        if child.type == ["h-card"]:
            return child

    return await HCard.from_url(hentry.properties["url"][0])


def get_own_hcard() -> HCard:
    """
    Build our h-card.
    """
    with open(current_app.config["HCARD"], "r", encoding="utf-8") as input:
        hcard = HCard(**yaml.safe_load(input))

    # make sure to set the URL to the blog
    hcard.properties["url"] = [url_for("homepage.index", _external=True)]

    return hcard


def hentry_from_entry(entry: Entry) -> HEntry:
    """
    Build an h-entry from an entry.
    """
    defaults = {
        "uid": [entry.location],
        "url": [entry.location],
        "post-status": ["published" if entry.published else "draft"],
        "visibility": [entry.visibility],
        "sensitive": ["true" if entry.sensitive else "false"],
        "published": [entry.last_modified_at.isoformat()],
    }
    missing = {
        key: value
        for key, value in defaults.items()
        if key not in entry.content.properties
    }
    entry.content.properties.update(missing)

    return entry.content


def extract_text_from_html(html: str) -> str:
    """
    Extract text from HTML.
    """
    return BeautifulSoup(html, "html.parser").get_text()


def get_template(hentry: HEntry) -> str:
    """
    Get the template for an h-entry.
    """
    templates = {
        "in-reply-to": "reply",
        "like-of": "like",
        "bookmark-of": "bookmark",
        "checkin": "checkin",
        "name": "article",
        "content": "note",
    }
    for key, template in templates.items():
        if key in hentry.properties:
            return template

    return "generic"


def get_type_emoji(hentry: HEntry) -> str:
    """
    Get the emoji for the type of the data.
    """
    types = {
        "reply": ("A reply", "💬"),
        "like": ("A like", "❤️"),
        "bookmark": ("A bookmark", "🔖"),
        "checkin": ("A checkin", "🚩"),
        "article": ("An article", "📄"),
        "note": ("A note", "📔"),
    }
    template = get_template(hentry)
    title, emoji = types.get(template, ("A generic post", "📝"))

    return f'<span title="{title}">{emoji}</span>'


async def get_representative_hcard(url: str) -> HCard:
    """
    Fetch the representative h-card of a given URL.
    """
    return await HCard.from_url(url)


async def get_post_author(url: str) -> list[HCard]:
    """
    Implement the authorship algorithm.

    See: https://indieweb.org/authorship-spec
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        parser = mf2py.Parser(response.content.decode(), url=url)

    # 1. start with a particular h-entry to determine authorship for, and no author. if
    # no h-entry, then there's no post to find authorship for, abort.
    # 2. parse the h-entry
    hentries = parser.to_dict(filter_by_type="h-entry")
    if not hentries:
        return []

    author = []
    for hentry in hentries:
        # 3. if the h-entry has an author property, use that
        if author := hentry["properties"].get("author"):
            break
    else:
        # 4. otherwise if the h-entry has a parent h-feed with author property, use that
        if hfeeds := parser.to_dict(filter_by_type="h-feed"):
            if len(hfeeds) == 1 and "author" in hfeeds[0]["properties"]:
                author = hfeeds[0]["properties"]["author"]

    # 6. if there is no author-page and the h-entry's page is a permalink page, then
    # 6.1. if the page has a rel-author link, let the author-page's URL be the href of the
    # rel-author link
    rels = parser.to_dict()["rels"]
    if not author and "author" in rels:
        author = rels["author"]

    return await asyncio.gather(*[get_hcard_from_author(item) for item in author])


async def get_hcard_from_author(author: str | dict[str, list[Any]]) -> HCard:
    """
    Steps 5 and 7 of the authorship algorithm.
    """
    # 5. if an author property was found
    # 5.1. if it has an h-card, use it, exit.
    if isinstance(author, dict):
        return HCard(**author)

    # 5.2. otherwise if author property is an http(s) URL, let the author-page have
    # that URL
    if author.startswith("http://") or author.startswith("https://"):
        # 7. if there is an author-page URL
        # 7.1. get the author-page from that URL and parse it for microformats2
        async with httpx.AsyncClient() as client:
            response = await client.get(author)
            parser = mf2py.Parser(response.content.decode(), url=author)
        candidates = parser.to_dict(filter_by_type="h-card")

        # 7.2. if author-page has 1+ h-card with url == uid == author-page's URL,
        # then use first such h-card, exit.
        for candidate in candidates:
            if (
                candidate["properties"]["url"]
                == candidate["properties"]["uid"]
                == [author]
            ):
                return HCard(**candidate)

        # 7.3. else if author-page has 1+ h-card with url property which matches the
        # href of a rel-me link on the author-page (perhaps the same hyperlink
        # element as the u-url, though not required to be), use first such h-card,
        # exit.
        parsed = parser.to_dict()
        rels = parsed["rels"]
        me = set(rels.get("me", []))

        for candidate in candidates:
            if any(url in me for url in candidate["properties"].get("url", [])):
                return HCard(**candidate)

        # 7.4. if the h-entry's page has 1+ h-card with url == author-page URL, use
        # first such h-card, exit.
        for candidate in candidates:
            if candidate["properties"]["url"] == [author]:
                return HCard(**candidate)

    # 5.3. otherwise use the author property as the author name, exit
    return HCard(properties={"name": [author]})


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

    This is used when showing entries in the feed/search/category pages.
    """
    soup = BeautifulSoup(html.strip(), "html.parser")
    truncated = truncate_html(soup, max_length)

    return str(truncated)


def truncate_html(element: Tag, max_length: int) -> Tag:
    """
    Truncate an HTML element to a maximum length, considering its text.
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


def reformat_html(html: str) -> str:
    """
    Reformat HTML so it looks nice.
    """
    formatter = HTMLFormatter(indent=4)
    html = BeautifulSoup(
        html,
        "html.parser",
        preserve_whitespace_tags=["p", "pre"],
    ).prettify(formatter=formatter)

    return html
