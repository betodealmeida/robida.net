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

from robida.helpers import extract_text_from_html
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
                },
            ),
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
                },
            ),
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
                    "name": ["Welcome to my blog!"],
                    "content": [
                        {
                            "value": extract_text_from_html(html).strip(),
                            "html": html.strip(),
                        },
                    ],
                    "summary": ["A quick intro on my blog"],
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
                },
            ),
        )

    entries = [note, deleted, article]

    async with get_db(app) as db:
        for entry in entries:
            await db.execute(
                """
INSERT INTO entries (
    uuid,
    author,
    location,
    content,
    deleted,
    created_at,
    last_modified_at
) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    entry.uuid.hex,
                    entry.author,
                    entry.location,
                    entry.content.model_dump_json(exclude_unset=True),
                    entry.deleted,
                    entry.created_at,
                    entry.last_modified_at,
                ),
            )
            await db.execute(
                """
INSERT INTO documents (uuid, content) VALUES (?, ?);
                """,
                (
                    entry.uuid.hex,
                    entry.content.model_dump_json(exclude_unset=True),
                ),
            )
        await db.commit()
