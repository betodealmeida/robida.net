"""
DB-related functions.
"""

from contextlib import asynccontextmanager

import aiosqlite
from quart import Quart


@asynccontextmanager
async def get_db(app: Quart) -> aiosqlite.Connection:
    """
    Context manager for a DB connection with a row factory.
    """
    async with aiosqlite.connect(app.config["DATABASE"]) as db:
        db.row_factory = aiosqlite.Row
        yield db
