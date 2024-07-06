"""
DB-related functions.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import aiosqlite
from quart import Quart
from quart.helpers import url_for

from robida.models import Entry, Microformats2


@asynccontextmanager
async def get_db(app: Quart) -> aiosqlite.Connection:
    """
    Context manager for a DB connection with a row factory.
    """
    async with aiosqlite.connect(app.config["DATABASE"]) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db(app: Quart) -> None:
    """
    Create tables.
    """
    async with get_db(app) as db:
        with open(Path(app.root_path) / "schema.sql", encoding="utf-8") as file_:
            await db.executescript(file_.read())
        await db.commit()


async def load_entries(app: Quart) -> None:
    """
    Populate the DB with a few entries.
    """
    # pylint: disable=import-outside-toplevel
    from robida.helpers import extract_text_from_html

    async with app.app_context():
        note = Entry(
            uuid=UUID("1d4f24cc-8c6a-442e-8a42-bc208cb16534"),
            author=url_for("homepage.index", _external=True),
            location=url_for(
                "feed.entry",
                uuid="1d4f24cc-8c6a-442e-8a42-bc208cb16534",
                _external=True,
            ),
            content=Microformats2(
                type=["h-entry"],
                properties={
                    "url": [
                        url_for(
                            "feed.entry",
                            uuid="1d4f24cc-8c6a-442e-8a42-bc208cb16534",
                            _external=True,
                        )
                    ],
                    "content": ["Hello, world!"],
                    "published": [datetime.now(timezone.utc).isoformat()],
                    "author": [
                        {
                            "type": ["h-card"],
                            "properties": {
                                "name": [app.config["NAME"]],
                                "url": [url_for("homepage.index", _external=True)],
                            },
                        }
                    ],
                    "category": ["note"],
                },
            ),
            published=True,
            visibility="public",
            sensitive=False,
        )

        deleted = Entry(
            uuid=UUID("37c9ed45-5c0c-43e4-b088-0e904ed849d7"),
            author=url_for("homepage.index", _external=True),
            location=url_for(
                "feed.entry",
                uuid="37c9ed45-5c0c-43e4-b088-0e904ed849d7",
                _external=True,
            ),
            content=Microformats2(
                type=["h-entry"],
                properties={
                    "url": [
                        url_for(
                            "feed.entry",
                            uuid="37c9ed45-5c0c-43e4-b088-0e904ed849d7",
                            _external=True,
                        )
                    ],
                    "content": ["Hello, world!"],
                    "published": [datetime.now(timezone.utc).isoformat()],
                    "author": [
                        {
                            "type": ["h-card"],
                            "properties": {
                                "name": [app.config["NAME"]],
                                "url": [url_for("homepage.index", _external=True)],
                            },
                        }
                    ],
                    "category": ["note"],
                },
            ),
            published=True,
            visibility="public",
            sensitive=False,
            deleted=True,
        )

        html = """
<p>
    This blog runs a custom-built Python web framework called
    <a href="https://github.com/betodealmeida/robida.net/">Robida</a>, built for the
    <a href="https://indieweb.org/">IndieWeb</a>.
</p>
        """
        article = Entry(
            uuid=UUID("8bf10ece-be18-4b96-af91-04e5c2a931ad"),
            author=url_for("homepage.index", _external=True),
            location=url_for(
                "feed.entry",
                uuid="8bf10ece-be18-4b96-af91-04e5c2a931ad",
                _external=True,
            ),
            content=Microformats2(
                type=["h-entry"],
                properties={
                    "name": ["About"],
                    "url": [
                        url_for(
                            "feed.entry",
                            uuid="8bf10ece-be18-4b96-af91-04e5c2a931ad",
                            _external=True,
                        )
                    ],
                    "content": [
                        {
                            "value": extract_text_from_html(html).strip(),
                            "html": html.strip(),
                        },
                    ],
                    "summary": ["About this blog."],
                    "published": [datetime.now(timezone.utc).isoformat()],
                    "author": [
                        {
                            "type": ["h-card"],
                            "properties": {
                                "name": [app.config["NAME"]],
                                "url": [url_for("homepage.index", _external=True)],
                            },
                        }
                    ],
                    "category": ["about", "blog", "python"],
                },
            ),
            published=True,
            visibility="public",
            sensitive=False,
        )

        reply = Entry(
            uuid=UUID("68e50fbd-69c0-4e12-bf2f-208ace952ffd"),
            author="http://alice.example.com",
            location="http://alice.example.com/post/1",
            content=Microformats2(
                type=["h-entry"],
                properties={
                    "url": ["http://alice.example.com/post/1"],
                    "in-reply-to": [
                        url_for(
                            "feed.entry",
                            uuid="1d4f24cc-8c6a-442e-8a42-bc208cb16534",
                            _external=True,
                        )
                    ],
                    "content": ["Welcome!"],
                    "published": [datetime.now(timezone.utc).isoformat()],
                    "author": [
                        {
                            "type": ["h-card"],
                            "properties": {
                                "name": ["Alice"],
                                "url": ["http://alice.example.com"],
                            },
                        }
                    ],
                },
            ),
            published=True,
            visibility="public",
            sensitive=False,
        )

        another_reply = Entry(
            uuid=UUID("99111091-26c7-4e3e-a0be-436fbeee0d14"),
            author=url_for("homepage.index", _external=True),
            location=url_for(
                "feed.entry",
                uuid="99111091-26c7-4e3e-a0be-436fbeee0d14",
                _external=True,
            ),
            content=Microformats2(
                type=["h-entry"],
                properties={
                    "url": [
                        url_for(
                            "feed.entry",
                            uuid="99111091-26c7-4e3e-a0be-436fbeee0d14",
                            _external=True,
                        )
                    ],
                    "in-reply-to": ["http://alice.example.com/post/1"],
                    "content": ["Thank you!"],
                    "published": [datetime.now(timezone.utc).isoformat()],
                    "author": [
                        {
                            "type": ["h-card"],
                            "properties": {
                                "name": [app.config["NAME"]],
                                "url": [url_for("homepage.index", _external=True)],
                            },
                        }
                    ],
                    "category": ["note"],
                },
            ),
            published=True,
            visibility="public",
            sensitive=False,
        )

    entries = [note, deleted, article, reply, another_reply]

    async with get_db(app) as db:
        for entry in entries:
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
    deleted,
    created_at,
    last_modified_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    entry.uuid.hex,
                    entry.author,
                    entry.location,
                    entry.content.model_dump_json(exclude_unset=True),
                    entry.published,
                    entry.visibility,
                    entry.sensitive,
                    entry.deleted,
                    entry.created_at,
                    entry.last_modified_at,
                ),
            )
            await db.execute(
                """
INSERT INTO documents (
    uuid,
    content
)
VALUES (?, ?);
                """,
                (
                    entry.uuid.hex,
                    entry.content.model_dump_json(exclude_unset=True),
                ),
            )

        async with app.app_context():
            await db.execute(
                """
INSERT INTO incoming_webmentions (
    source,
    target,
    status
)
VALUES (?, ?, ?);
                """,
                (
                    "http://alice.example.com/post/1",
                    url_for(
                        "feed.entry",
                        uuid=UUID("1d4f24cc-8c6a-442e-8a42-bc208cb16534"),
                        _external=True,
                    ),
                    "success",
                ),
            )
            await db.execute(
                """
INSERT INTO outgoing_webmentions (
    source,
    target,
    status
)
VALUES (?, ?, ?);
                """,
                (
                    url_for(
                        "feed.entry",
                        uuid=UUID("99111091-26c7-4e3e-a0be-436fbeee0d14"),
                        _external=True,
                    ),
                    "http://alice.example.com/post/1",
                    "success",
                ),
            )
        await db.commit()
