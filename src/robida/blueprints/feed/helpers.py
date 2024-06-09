"""
Helper functions for the feed.
"""

from collections import defaultdict
import json


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
