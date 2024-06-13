"""
Helper functions for searching.
"""

import json
from datetime import datetime
from uuid import UUID

from quart import current_app
from quart.helpers import url_for

from robida.constants import MAX_PAGE_SIZE
from robida.db import get_db
from robida.models import Entry


async def search_entries(
    needle: str,
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
    entries.uuid,
    entries.author,
    entries.location,
    entries.content,
    entries.read,
    entries.deleted,
    entries.created_at,
    entries.last_modified_at
FROM
    entries
JOIN
    documents
ON
    entries.uuid = documents.uuid
WHERE
    entries.author = ? AND
    entries.deleted = ? AND
    documents MATCH ?
ORDER BY
    entries.last_modified_at DESC
LIMIT
    ?
OFFSET
    ?
            """,
            (
                url_for("homepage.index", _external=True),
                False,
                needle,
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
