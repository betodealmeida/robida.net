"""
DB-related functions.
"""

from contextlib import asynccontextmanager

import aiosqlite
from quart import current_app


@asynccontextmanager
async def get_db() -> aiosqlite.Connection:
    """
    Context manager for a DB connection with a row factory.
    """
    async with aiosqlite.connect(current_app.config["DATABASE"]) as db:
        db.row_factory = aiosqlite.Row
        yield db
