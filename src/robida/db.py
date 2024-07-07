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
