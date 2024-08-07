"""
Helper functions for categories.
"""

import json
from datetime import datetime
from uuid import UUID

from quart import current_app, session
from quart.helpers import url_for

from robida.constants import MAX_PAGE_SIZE
from robida.db import get_db
from robida.models import Entry


CATEGORIES_QUERY = """
SELECT
    entries.uuid,
    entries.author,
    entries.location,
    entries.content,
    entries.published,
    entries.visibility,
    entries.sensitive,
    entries.read,
    entries.deleted,
    entries.created_at,
    entries.last_modified_at
FROM
    entries
WHERE
    uuid IN (
        SELECT entries.uuid
        FROM entries, json_each(entries.content, '$.properties.category')
        WHERE json_each.value = ?
    ) AND
    entries.author = ? AND
    entries.deleted = ?
    {protected}
ORDER BY
    entries.last_modified_at DESC
LIMIT
    ?
OFFSET
    ?
;
"""


async def list_entries(
    category: str,
    page: int = 0,
    page_size: int = MAX_PAGE_SIZE,
) -> list[Entry]:
    """
    Load all the entries for a given category.
    """
    # make sure the page size is within sane limits
    page_size = min(page_size, MAX_PAGE_SIZE)

    # extra predicate
    me = url_for("homepage.index", _external=True)
    protected = (
        "AND entries.published = TRUE AND entries.visibility = 'public'"
        if session.get("me") != me
        else ""
    )

    async with get_db(current_app) as db:
        async with db.execute(
            CATEGORIES_QUERY.format(protected=protected),
            (
                category,
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
            published=row["published"],
            visibility=row["visibility"],
            sensitive=row["sensitive"],
            read=row["read"],
            deleted=row["deleted"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_modified_at=datetime.fromisoformat(row["last_modified_at"]),
        )
        for row in rows
    ]
