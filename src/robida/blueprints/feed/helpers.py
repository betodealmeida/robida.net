"""
Helper functions for the feed.
"""

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from bs4 import BeautifulSoup
from bs4.formatter import HTMLFormatter
from quart import Response, current_app, request
from quart.helpers import url_for

from robida.constants import MAX_PAGE_SIZE
from robida.db import get_db
from robida.helpers import extract_text_from_html, fetch_hcard
from robida.models import Entry

from .models import (
    FeedRequest,
    JSONFeed,
    JSONFeedAuthor,
    JSONFeedItem,
    JSON_FEED_VERSION,
)


GRAPH_QUERY = """
WITH RECURSIVE reply_graph AS (
    SELECT
        uuid,
        author,
        location,
        content,
        read,
        deleted,
        created_at,
        last_modified_at,
        content->>'$.properties.in-reply-to[0]' AS in_reply_to
    FROM
        entries
    WHERE
        uuid = ?

    UNION ALL

    SELECT
        e.uuid,
        e.author,
        e.location,
        e.content,
        e.read,
        e.deleted,
        e.created_at,
        e.last_modified_at,
        e.content->>'$.properties.in-reply-to[0]' AS in_reply_to
    FROM
        entries e
    INNER JOIN
        reply_graph rg
    ON
        e.content->>'$.properties.in-reply-to[0]' = rg.location
)
SELECT
    *
FROM
    reply_graph;
"""


async def get_entry_graph(db, entry_uuid):
    """
    Get the graph of an entry.
    """
    async with db.execute(GRAPH_QUERY, (entry_uuid,)) as cursor:
        rows = await cursor.fetchall()

    replies = defaultdict(list)
    for row in rows:
        replies[row["in_reply_to"]].append(
            (
                row["location"],
                json.loads(row["content"]),
            )
        )

    root = rows[0]["location"], json.loads(rows[0]["content"])
    queue = [root]
    while queue:
        location, entry = queue.pop(0)
        entry.setdefault("children", [])
        for location, reply in replies[location]:
            queue.append((location, reply))
            entry["children"].append(reply)

    return root


async def render_microformat(data: dict[str, Any]) -> str:
    """
    Render microformat as HTML.

    This function is used to test the Microformat templates.
    """
    env = current_app.jinja_env
    env.globals["fetch_hcard"] = fetch_hcard

    template = env.get_template("feed/generic.html")
    html = await template.render_async(data=data)

    return reformat_html(html)


def reformat_html(html: str) -> str:
    """
    Reformat HTML so it looks nice.
    """
    formatter = HTMLFormatter(indent=4)
    html = BeautifulSoup(html, "html.parser").prettify(formatter=formatter)

    return html


async def get_entries(
    since: str | None = None,
    page: int = 0,
    page_size: int = MAX_PAGE_SIZE,
) -> list[Entry]:
    """
    Load all the entries.
    """
    # make sure the page size is within sane limits
    page_size = min(page_size, MAX_PAGE_SIZE)

    async with get_db(current_app) as db:
        async with db.execute(
            """
SELECT
    uuid,
    author,
    location,
    content,
    read,
    deleted,
    created_at,
    last_modified_at
FROM
    entries
WHERE
    last_modified_at >= ? AND
    author = ? AND
    deleted = ?
ORDER BY
    last_modified_at DESC
LIMIT
    ?
OFFSET
    ?
            """,
            (
                since or "1970-01-01 00:00:00+00:00",
                url_for("homepage.index", _external=True),
                False,
                page_size,
                page * page_size,
            ),
        ) as cursor:
            rows = await cursor.fetchall()

    return [
        Entry(
            uuid=UUID(row["uuid"]),
            author=row["author"],
            location=row["location"],
            content=json.loads(row["content"]),
            read=row["read"],
            deleted=row["deleted"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_modified_at=datetime.fromisoformat(row["last_modified_at"]),
        )
        for row in rows
    ]


async def get_entry(uuid: UUID) -> Entry | None:
    """
    Load a given entry.
    """
    async with get_db(current_app) as db:
        async with db.execute(
            """
SELECT
    uuid,
    author,
    location,
    content,
    read,
    deleted,
    created_at,
    last_modified_at
FROM
    entries
WHERE
    uuid >= ?
            """,
            (uuid.hex,),
        ) as cursor:
            row = await cursor.fetchone()

    if row is None:
        return None

    return Entry(
        uuid=UUID(row["uuid"]),
        author=row["author"],
        location=row["location"],
        content=json.loads(row["content"]),
        read=row["read"],
        deleted=row["deleted"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_modified_at=datetime.fromisoformat(row["last_modified_at"]),
    )


def generate_etag(entries: list[Entry]) -> str:
    """
    Compute ETag for entries.
    """
    payload = [entry.content.model_dump() for entry in entries]
    serialized = json.dumps(payload, sort_keys=True)
    etag = hashlib.sha256(serialized.encode("utf-8")).hexdigest()  # Compute the hash

    return etag


def make_conditional_response(entries: list[Entry]) -> Response:
    """
    Make a conditional response, if possible.

    This function is used to check if we can return a 304. If not, it returns a standard
    response with the headers `Last-Modified` and `ETag` already set.
    """
    last_modified_at = (
        max(entry.last_modified_at for entry in entries)
        if entries
        else datetime.now(timezone.utc)
    )
    etag = generate_etag(entries)

    response = Response(
        status=200,
        headers={
            "Last-Modified": last_modified_at.strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "ETag": etag,
        },
    )

    if_modified_since = request.headers.get("If-Modified-Since")
    if_none_match = request.headers.get("If-None-Match")

    if if_modified_since is None and if_none_match is None:
        return response

    if if_modified_since and last_modified_at > datetime.strptime(
        if_modified_since,
        "%a, %d %b %Y %H:%M:%S GMT",
    ).replace(tzinfo=timezone.utc):
        return response

    if if_none_match and if_none_match != etag:
        return response

    return Response(status=304)


def build_jsonfeed_item(entry: Entry) -> JSONFeedItem:
    """
    Build a JSON Feed item.
    """

    item = JSONFeedItem(
        id=entry.uuid,
        url=entry.location,
        date_published=entry.created_at,
        date_modified=entry.last_modified_at,
        authors=[
            JSONFeedAuthor(
                name=current_app.config["NAME"],
                url=url_for("homepage.index", _external=True),
                avatar=url_for("static", filename="photo.jpg", _external=True),
            )
        ],
    )

    if "name" in entry.content.properties:
        item.title = entry.content.properties["name"][0]

    if "content" in entry.content.properties:
        content = entry.content.properties["content"][0]
        if isinstance(content, str):
            item.content_html = content.strip()
            item.content_text = extract_text_from_html(content).strip()
        else:
            item.content_html = content["html"].strip() if "html" in content else None
            item.content_text = content["value"].strip() if "value" in content else None

    if "summary" in entry.content.properties:
        item.summary = entry.content.properties["summary"][0]

    return item


def build_jsonfeed(entries: list[Entry], query_args: FeedRequest) -> JSONFeed:
    """
    Build a JSON Feed entry.
    """
    feed_url = url_for("feed.json_index", _external=True)

    return JSONFeed(
        version=JSON_FEED_VERSION,
        title=current_app.config["SITE_NAME"],
        home_page_url=url_for("homepage.index", _external=True),
        feed_url=feed_url,
        description=current_app.config["SITE_DESCRIPTION"],
        user_comment=(
            "This feed allows you to read the posts from this site in any feed reader "
            "that supports the JSON Feed format. To add this feed to your reader, copy "
            f"the following URL — {feed_url} — and add it your reader."
        ),
        next_url=url_for(
            "feed.json_index",
            since=query_args.since,
            page=query_args.page + 1,
            page_size=query_args.page_size,
            _external=True,
        ),
        authors=[
            JSONFeedAuthor(
                name=current_app.config["NAME"],
                url=url_for("homepage.index", _external=True),
                avatar=url_for("static", filename="photo.jpg", _external=True),
            ),
        ],
        language=current_app.config["LANGUAGE"],
        hubs=[url_for("websub.hub", _external=True)],
        items=[build_jsonfeed_item(entry) for entry in entries],
    )


def hfeed_from_entries(entries: list[Entry], url: str) -> dict[str, Any]:
    """
    Build an h-feed from entries.
    """
    last_modified_at = (
        max(entry.last_modified_at for entry in entries)
        if entries
        else datetime.now(timezone.utc)
    )

    return {
        "type": ["h-feed"],
        "properties": {
            "name": [current_app.config["SITE_NAME"]],
            "url": [url],
            "summary": [current_app.config["SITE_DESCRIPTION"]],
            "published": [last_modified_at.isoformat()],
            "language": [current_app.config["LANGUAGE"]],
            "author": [
                {
                    "type": ["h-card"],
                    "properties": {
                        "name": [current_app.config["NAME"]],
                        "url": [url_for("homepage.index", _external=True)],
                        "photo": [
                            url_for("static", filename="photo.jpg", _external=True)
                        ],
                    },
                }
            ],
        },
        "children": [hentry_from_entry(entry) for entry in entries],
    }


def hentry_from_entry(entry: Entry) -> dict[str, Any]:
    """
    Build an hn-entry from an entry.
    """
    entry.content.properties.setdefault("url", [entry.location])
    entry.content.properties.setdefault(
        "published",
        [entry.last_modified_at.isoformat()],
    )

    return entry.content.model_dump()


def get_title(hentry: dict[str, Any]) -> str:
    """
    Get the title of an h-entry.
    """
    if name := hentry["properties"].get("name"):
        return name[0]

    if content := hentry["properties"].get("content"):
        return content[0]["value"] if isinstance(content[0], dict) else content[0]

    return "Untitled"
