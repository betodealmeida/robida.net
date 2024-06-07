"""
Tests for the entries helper functions.
"""

from aiosqlite import Connection

from robida.blueprints.entries.helpers import get_entry_graph


async def test_get_entry_graph(db: Connection) -> None:
    """
    Test the `get_entry_graph` function.
    """
    await db.execute(
        """
INSERT INTO entries (uuid, author, location, content, read, deleted)
VALUES
('1', 'author1', 'location1', '{"properties": {"in-reply-to": []}}', 0, 0),
('2', 'author2', 'location2', '{"properties": {"in-reply-to": ["location1"]}}', 0, 0),
('3', 'author3', 'location3', '{"properties": {"in-reply-to": ["location2"]}}', 0, 0),
('4', 'author4', 'location4', '{"properties": {"in-reply-to": ["location3"]}}', 0, 0),
('5', 'author5', 'location5', '{"properties": {"in-reply-to": []}}', 0, 0),
('6', 'author6', 'location6', '{"properties": {"in-reply-to": ["location5"]}}', 0, 0),
('7', 'author7', 'location7', '{"properties": {"in-reply-to": ["location6"]}}', 0, 0),
('8', 'author8', 'location8', '{"properties": {"in-reply-to": ["location1"]}}', 0, 0),
('9', 'author9', 'location9', '{"properties": {"in-reply-to": ["location8"]}}', 0, 0),
('10', 'author10', 'location10', '{"properties": {"in-reply-to": ["location9"]}}', 0, 0);
"""
    )
    await db.commit()

    root = await get_entry_graph(db, "1")
    assert root == (
        "location1",
        {
            "properties": {"in-reply-to": []},
            "children": [
                {
                    "properties": {"in-reply-to": ["location1"]},
                    "children": [
                        {
                            "properties": {"in-reply-to": ["location2"]},
                            "children": [
                                {
                                    "properties": {"in-reply-to": ["location3"]},
                                    "children": [],
                                }
                            ],
                        }
                    ],
                },
                {
                    "properties": {"in-reply-to": ["location1"]},
                    "children": [
                        {
                            "properties": {"in-reply-to": ["location8"]},
                            "children": [
                                {
                                    "properties": {"in-reply-to": ["location9"]},
                                    "children": [],
                                }
                            ],
                        }
                    ],
                },
            ],
        },
    )
