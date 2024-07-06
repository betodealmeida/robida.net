"""
Tests for the generic helper functions.
"""

# pylint: disable=too-many-lines

import json
from datetime import datetime, timezone
from uuid import UUID

import pytest
from aiosqlite import Connection
from freezegun import freeze_time
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture
from quart import Quart, testing
from quart.helpers import url_for

from robida.helpers import (
    canonicalize_url,
    compute_challenge,
    fetch_hcard,
    get_entry,
    get_type_emoji,
    iso_to_rfc822,
    new_hentry,
    rfc822_to_iso,
    summarize,
    upsert_entry,
)
from robida.models import Entry, Microformats2


async def test_fetch_hcard_not_found(httpx_mock: HTTPXMock) -> None:
    """
    Test the `render_microformat` function when the h-card is not found.
    """
    httpx_mock.add_response(url="https://tantek.com/", status_code=404)

    assert await fetch_hcard("https://tantek.com/") == {
        "type": ["h-card"],
        "properties": {
            "name": ["https://tantek.com/"],
            "url": ["https://tantek.com/"],
        },
    }


async def test_get_type_emoji() -> None:
    """
    Test the `get_type_emoji` function.
    """

    assert (
        get_type_emoji({"type": ["h-entry"], "properties": {"name": ["A title"]}})
        == '<span title="An article">📄</span>'
    )
    assert (
        get_type_emoji(
            {
                "type": ["h-entry"],
                "properties": {
                    "in-reply-to": ["http://example.com/"],
                    "name": ["A title"],
                },
            }
        )
        == '<span title="A reply">💬</span>'
    )
    assert (
        get_type_emoji({"type": ["h-entry"], "properties": {}})
        == '<span title="A note">📔</span>'
    )
    assert (
        get_type_emoji(
            {"type": ["h-entry"], "properties": {"like-of": ["http://example.com/"]}}
        )
        == '<span title="A like">❤️</span>'
    )
    assert (
        get_type_emoji(
            {
                "type": ["h-entry"],
                "properties": {"bookmark-of": ["http://example.com/"]},
            }
        )
        == '<span title="A bookmark">🔖</span>'
    )
    assert (
        get_type_emoji({"type": ["h-new"], "properties": {}})
        == '<span title="A generic post">📝</span>'
    )


async def test_iso_to_rfc822() -> None:
    """
    Test the `iso_to_rfc822` function.
    """
    assert iso_to_rfc822("2022-01-01T00:00:00Z") == "Sat, 01 Jan 2022 00:00:00 +0000"
    assert (
        iso_to_rfc822("2022-01-01T00:00:00+00:00") == "Sat, 01 Jan 2022 00:00:00 +0000"
    )
    assert (
        iso_to_rfc822("2022-01-01T00:00:00+01:00") == "Sat, 01 Jan 2022 00:00:00 +0100"
    )


async def test_rfc822_to_iso() -> None:
    """
    Test the `rfc822_to_iso` function.
    """
    assert (
        rfc822_to_iso("Sat, 01 Jan 2022 00:00:00 +0000") == "2022-01-01T00:00:00+00:00"
    )
    assert (
        rfc822_to_iso("Sat, 01 Jan 2022 00:00:00 +0000") == "2022-01-01T00:00:00+00:00"
    )
    assert (
        rfc822_to_iso("Sat, 01 Jan 2022 00:00:00 +0100") == "2022-01-01T00:00:00+01:00"
    )


def test_canonicalize_url() -> None:
    """
    Test the `canonicalize_url` function.
    """
    assert canonicalize_url("https://example.com") == "https://example.com/"
    assert canonicalize_url("https://example.com/") == "https://example.com/"
    assert canonicalize_url("https://example.com/page") == "https://example.com/page"
    assert canonicalize_url("https://example.com/page/") == "https://example.com/page/"
    assert canonicalize_url("example.com") == "https://example.com/"
    assert canonicalize_url("example.com/page") == "https://example.com/page"
    assert canonicalize_url("example.com/page/") == "https://example.com/page/"


def test_compute_challenge() -> None:
    """
    Test the `compute_challenge` function.
    """
    assert compute_challenge("secret", "plain") == "secret"
    assert (
        compute_challenge("secret", "S256")
        == "K7gNU3sdo-OL0wNhqoVWhr3g6s1xYv72ol_pe_Unols"
    )

    with pytest.raises(ValueError) as excinfo:
        compute_challenge("secret", "unknown")
    assert str(excinfo.value) == "Invalid code challenge method"


@freeze_time("2024-01-01 00:00:00")
async def test_upsert_entry(db: Connection, current_app: Quart) -> None:
    """
    Test the `upsert_entry` function.
    """
    async with current_app.app_context():
        await upsert_entry(
            db,
            Microformats2(
                type=["h-entry"],
                properties={
                    "url": ["https://other.example.com"],
                    "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                    "post-status": ["published"],
                    "author": [
                        {
                            "type": ["h-card"],
                            "properties": {
                                "url": ["https://other.example.com"],
                            },
                        }
                    ],
                    "content": [
                        "This is a dummy entry created by the webmention processor."
                    ],
                },
            ),
        )

    async with db.execute(
        "SELECT * FROM entries WHERE uuid = ?;",
        ("92cdeabd827843ad871d0214dcb2d12e",),
    ) as cursor:
        entry = await cursor.fetchone()

    assert dict(entry) == {
        "uuid": "92cdeabd827843ad871d0214dcb2d12e",
        "published": 1,
        "visibility": "public",
        "sensitive": 0,
        "author": "https://other.example.com",
        "location": "https://other.example.com",
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "url": ["https://other.example.com"],
                    "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                    "post-status": ["published"],
                    "author": [
                        {
                            "type": ["h-card"],
                            "properties": {
                                "url": ["https://other.example.com"],
                            },
                        }
                    ],
                    "content": [
                        "This is a dummy entry created by the webmention processor."
                    ],
                },
            },
            separators=(",", ":"),
        ),
        "read": 0,
        "deleted": 0,
        "created_at": "2024-01-01 00:00:00+00:00",
        "last_modified_at": "2024-01-01 00:00:00+00:00",
    }


async def test_upsert_entry_published(db: Connection, current_app: Quart) -> None:
    """
    Test the `upsert_entry` function when the h-entry has the `published` attribute.
    """
    async with current_app.app_context():
        await upsert_entry(
            db,
            Microformats2(
                type=["h-entry"],
                properties={
                    "url": ["https://other.example.com"],
                    "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                    "author": [
                        {
                            "type": ["h-card"],
                            "properties": {
                                "url": ["https://other.example.com"],
                            },
                        }
                    ],
                    "content": [
                        "This is a dummy entry created by the webmention processor."
                    ],
                    "published": ["2024-01-01T01:23:45+00:00"],
                },
            ),
        )

    async with db.execute(
        "SELECT * FROM entries WHERE uuid = ?;",
        ("92cdeabd827843ad871d0214dcb2d12e",),
    ) as cursor:
        entry = await cursor.fetchone()

    assert dict(entry) == {
        "uuid": "92cdeabd827843ad871d0214dcb2d12e",
        "published": 1,
        "visibility": "public",
        "sensitive": 0,
        "author": "https://other.example.com",
        "location": "https://other.example.com",
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "url": ["https://other.example.com"],
                    "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                    "author": [
                        {
                            "type": ["h-card"],
                            "properties": {
                                "url": ["https://other.example.com"],
                            },
                        }
                    ],
                    "content": [
                        "This is a dummy entry created by the webmention processor."
                    ],
                    "published": ["2024-01-01T01:23:45+00:00"],
                },
            },
            separators=(",", ":"),
        ),
        "read": 0,
        "deleted": 0,
        "created_at": "2024-01-01 01:23:45+00:00",
        "last_modified_at": "2024-01-01 01:23:45+00:00",
    }


def test_summarize() -> None:
    """
    Test the `summarize` function.
    """
    assert summarize("Hello, world!", 255) == "Hello, world!"
    assert summarize("Hello, world!", 10) == "Hello, wor⋯"

    assert summarize(
        '<p>The cool thing thing about <a href="https://example.com" '
        'span="very very very long">this function</a> is that it takes into '
        "consideration only the text content.</p>",
        50,
    ) == (
        '<p>The cool thing thing about <a href="https://example.com" '
        'span="very very very long">this function</a> is that i⋯</p>'
    )

    assert summarize(
        '<p>The cool thing thing about <a href="https://example.com" '
        'span="very very very long">this function</a> is that it takes into '
        "consideration only the text content.</p>",
        35,
    ) == (
        '<p>The cool thing thing about <a href="https://example.com" '
        'span="very very very long">this fun⋯</a></p>'
    )


@freeze_time("2024-01-01 00:00:00")
async def test_new_hentry(mocker: MockerFixture, current_app: Quart) -> None:
    """
    Test the `new_hentry` function.
    """
    mocker.patch(
        "robida.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    async with current_app.app_context():
        assert new_hentry() == Microformats2(
            type=["h-entry"],
            value=None,
            properties={
                "author": [
                    {
                        "type": ["h-card"],
                        "value": "http://example.com/",
                        "properties": {
                            "name": ["Beto Dealmeida"],
                            "url": ["http://example.com/"],
                            "photo": [
                                {
                                    "alt": "This is my photo",
                                    "value": "http://example.com/static/img/photo.jpg",
                                }
                            ],
                            "email": ["me@example.com"],
                            "note": ["I like turtles."],
                        },
                        "children": [],
                    }
                ],
                "published": ["2024-01-01T00:00:00+00:00"],
                "updated": ["2024-01-01T00:00:00+00:00"],
                "url": ["http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                "post-status": ["published"],
                "visibility": ["public"],
                "sensitive": ["false"],
            },
            children=[],
        )


async def test_x_forwarded_proto_middleware(
    current_app: Quart,
    client: testing.QuartClient,
) -> None:
    """
    Test the `x_forwarded_proto_middleware` middleware.
    """

    @current_app.route("/self")
    async def self_view() -> dict[str, str]:
        return {"url": url_for("self_view", _external=True)}

    headers = {"x-forwarded-proto": "https"}
    response = await client.get("/self", headers=headers)
    assert response.status_code == 200
    assert await response.json == {"url": "https://example.com/self"}


async def test_get_entry(current_app: Quart, db: Connection) -> None:
    """
    Test the `get_entry` function.
    """
    await db.execute(
        """
INSERT INTO entries (
    uuid,
    author,
    location,
    content,
    read,
    deleted,
    created_at,
    last_modified_at
)
VALUES
(?, ?, ?, ?, ?, ?, ?, ?),
(?, ?, ?, ?, ?, ?, ?, ?),
(?, ?, ?, ?, ?, ?, ?, ?),
(?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            #
            "92cdeabd827843ad871d0214dcb2d12e",
            "http://example.com/",
            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "content": ["Hello, world!"],
                    },
                },
                separators=(",", ":"),
            ),
            False,
            False,
            "2024-01-01 00:00:00+00:00",
            "2024-01-01 00:00:00+00:00",
            #
            "d2f5229639d946e1a6c539e33d119403",
            "http://alice.example.com/",
            "http://alice.example.com/post/1",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "in-reply-to": [
                            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                        ],
                        "content": ["Welcome!"],
                    },
                },
                separators=(",", ":"),
            ),
            False,
            False,
            "2024-01-02 00:00:00+00:00",
            "2024-01-02 00:00:00+00:00",
            #
            "96135d01f6be4e1c99d0cc5a6a4f1d10",
            "http://example.com/",
            "http://example.com/feed/96135d01-f6be-4e1c-99d0-cc5a6a4f1d10",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "in-reply-to": [
                            "http://alice.example.com/post/1",
                        ],
                        "content": ["Thank you!"],
                    },
                },
                separators=(",", ":"),
            ),
            False,
            False,
            "2024-01-03 00:00:00+00:00",
            "2024-01-03 00:00:00+00:00",
            #
            "12f1ba3d33d6422b87932b6ac17275a9",
            "http://bob.example.com/",
            "http://bob.example.com/posts/42",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "like-of": [
                            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                        ],
                        "summary": [
                            "Liked: http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                        ],
                    },
                },
                separators=(",", ":"),
            ),
            False,
            False,
            "2024-01-07 00:00:00+00:00",
            "2024-01-07 00:00:00+00:00",
        ),
    )
    await db.execute(
        """
INSERT INTO incoming_webmentions (
    source,
    target,
    status
)
VALUES
(?, ?, ?),
(?, ?, ?);
        """,
        (
            "http://alice.example.com/post/1",
            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
            "success",
            "http://bob.example.com/posts/42",
            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
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
VALUES
(?, ?, ?);
        """,
        (
            "http://example.com/feed/96135d01-f6be-4e1c-99d0-cc5a6a4f1d10",
            "http://alice.example.com/post/1",
            "success",
        ),
    )
    await db.commit()

    async with current_app.app_context():
        entry = await get_entry(db, UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"))

    assert entry == Entry(
        uuid=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
        author="http://example.com/",
        location="http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
        content=Microformats2(
            type=["h-entry"],
            properties={"content": ["Hello, world!"]},
            children=[
                Microformats2(
                    type=["h-entry"],
                    properties={
                        "in-reply-to": [
                            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                        ],
                        "content": ["Welcome!"],
                    },
                    children=[
                        Microformats2(
                            type=["h-entry"],
                            properties={
                                "in-reply-to": ["http://alice.example.com/post/1"],
                                "content": ["Thank you!"],
                            },
                            children=[],
                        ),
                    ],
                ),
                Microformats2(
                    type=["h-entry"],
                    properties={
                        "like-of": [
                            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                        ],
                        "summary": [
                            "Liked: http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                        ],
                    },
                    children=[],
                ),
            ],
        ),
        read=False,
        deleted=False,
        created_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        last_modified_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
    )


async def test_get_entry_private(current_app: Quart, db: Connection) -> None:
    """
    Test that `get_entry` function can ommit private entries.
    """
    await db.execute(
        """
INSERT INTO entries (
    uuid,
    author,
    location,
    content,
    visibility,
    read,
    deleted,
    created_at,
    last_modified_at
)
VALUES
(?, ?, ?, ?, ?, ?, ?, ?, ?),
(?, ?, ?, ?, ?, ?, ?, ?, ?),
(?, ?, ?, ?, ?, ?, ?, ?, ?),
(?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            #
            "92cdeabd827843ad871d0214dcb2d12e",
            "http://example.com/",
            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "content": ["Hello, world!"],
                    },
                },
                separators=(",", ":"),
            ),
            "public",
            False,
            False,
            "2024-01-01 00:00:00+00:00",
            "2024-01-01 00:00:00+00:00",
            #
            "d2f5229639d946e1a6c539e33d119403",
            "http://alice.example.com/",
            "http://alice.example.com/post/1",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "in-reply-to": [
                            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                        ],
                        "content": ["Welcome!"],
                    },
                },
                separators=(",", ":"),
            ),
            "public",
            False,
            False,
            "2024-01-02 00:00:00+00:00",
            "2024-01-02 00:00:00+00:00",
            #
            "96135d01f6be4e1c99d0cc5a6a4f1d10",
            "http://example.com/",
            "http://example.com/feed/96135d01-f6be-4e1c-99d0-cc5a6a4f1d10",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "in-reply-to": [
                            "http://alice.example.com/post/1",
                        ],
                        "content": ["Thank you!"],
                    },
                },
                separators=(",", ":"),
            ),
            "public",
            False,
            False,
            "2024-01-03 00:00:00+00:00",
            "2024-01-03 00:00:00+00:00",
            # private
            "12f1ba3d33d6422b87932b6ac17275a9",
            "http://bob.example.com/",
            "http://bob.example.com/posts/42",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "visibility": ["private"],
                        "like-of": [
                            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                        ],
                        "summary": [
                            "Liked: http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                        ],
                    },
                },
                separators=(",", ":"),
            ),
            "private",
            False,
            False,
            "2024-01-07 00:00:00+00:00",
            "2024-01-07 00:00:00+00:00",
        ),
    )
    await db.execute(
        """
INSERT INTO incoming_webmentions (
    source,
    target,
    status
)
VALUES
(?, ?, ?),
(?, ?, ?);
        """,
        (
            "http://alice.example.com/post/1",
            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
            "success",
            "http://bob.example.com/posts/42",
            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
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
VALUES
(?, ?, ?);
        """,
        (
            "http://example.com/feed/96135d01-f6be-4e1c-99d0-cc5a6a4f1d10",
            "http://alice.example.com/post/1",
            "success",
        ),
    )
    await db.commit()

    async with current_app.app_context():
        entry = await get_entry(
            db,
            UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            include_private_children=True,
        )

    assert entry == Entry(
        uuid=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
        author="http://example.com/",
        location="http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
        content=Microformats2(
            type=["h-entry"],
            properties={"content": ["Hello, world!"]},
            children=[
                Microformats2(
                    type=["h-entry"],
                    properties={
                        "in-reply-to": [
                            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                        ],
                        "content": ["Welcome!"],
                    },
                    children=[
                        Microformats2(
                            type=["h-entry"],
                            properties={
                                "in-reply-to": ["http://alice.example.com/post/1"],
                                "content": ["Thank you!"],
                            },
                            children=[],
                        ),
                    ],
                ),
                Microformats2(
                    type=["h-entry"],
                    properties={
                        "visibility": ["private"],
                        "like-of": [
                            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                        ],
                        "summary": [
                            "Liked: http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                        ],
                    },
                    children=[],
                ),
            ],
        ),
        read=False,
        deleted=False,
        created_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        last_modified_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
    )

    async with current_app.app_context():
        entry = await get_entry(
            db,
            UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            include_private_children=False,
        )

    assert entry == Entry(
        uuid=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
        author="http://example.com/",
        location="http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
        content=Microformats2(
            type=["h-entry"],
            properties={"content": ["Hello, world!"]},
            children=[
                Microformats2(
                    type=["h-entry"],
                    properties={
                        "in-reply-to": [
                            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                        ],
                        "content": ["Welcome!"],
                    },
                    children=[
                        Microformats2(
                            type=["h-entry"],
                            properties={
                                "in-reply-to": ["http://alice.example.com/post/1"],
                                "content": ["Thank you!"],
                            },
                            children=[],
                        ),
                    ],
                ),
            ],
        ),
        read=False,
        deleted=False,
        created_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        last_modified_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
    )


async def test_get_entry_circular(current_app: Quart, db: Connection) -> None:
    """
    Test the `get_entry` function with circular dependencies.

    Should not happen unless the SQL query is incorrect.
    """
    await db.execute(
        """
INSERT INTO entries (
    uuid,
    author,
    location,
    content,
    read,
    deleted,
    created_at,
    last_modified_at
)
VALUES
(?, ?, ?, ?, ?, ?, ?, ?),
(?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            #
            "92cdeabd827843ad871d0214dcb2d12e",
            "http://example.com/",
            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "in-reply-to": [
                            "http://alice.example.com/post/1",
                        ],
                        "content": ["Hello, world!"],
                    },
                },
                separators=(",", ":"),
            ),
            False,
            False,
            "2024-01-01 00:00:00+00:00",
            "2024-01-01 00:00:00+00:00",
            #
            "d2f5229639d946e1a6c539e33d119403",
            "http://alice.example.com/",
            "http://alice.example.com/post/1",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "in-reply-to": [
                            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                        ],
                        "content": ["Welcome!"],
                    },
                },
                separators=(",", ":"),
            ),
            False,
            False,
            "2024-01-02 00:00:00+00:00",
            "2024-01-07 00:00:00+00:00",
        ),
    )
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
            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
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
VALUES
(?, ?, ?);
        """,
        (
            "http://example.com/feed/96135d01-f6be-4e1c-99d0-cc5a6a4f1d10",
            "http://alice.example.com/post/1",
            "success",
        ),
    )
    await db.commit()

    async with current_app.app_context():
        entry = await get_entry(db, UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"))

    assert entry == Entry(
        uuid=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
        author="http://example.com/",
        location="http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
        content=Microformats2(
            type=["h-entry"],
            properties={
                "content": ["Hello, world!"],
                "in-reply-to": ["http://alice.example.com/post/1"],
            },
            children=[
                Microformats2(
                    type=["h-entry"],
                    properties={
                        "in-reply-to": [
                            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                        ],
                        "content": ["Welcome!"],
                    },
                    children=[],
                ),
            ],
        ),
        read=False,
        deleted=False,
        created_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        last_modified_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
    )


async def test_get_entry_seen(current_app: Quart, db: Connection) -> None:
    """
    Test the `get_entry` function `seen` check.
    """
    await db.execute(
        """
INSERT INTO entries (
    uuid,
    author,
    location,
    content,
    read,
    deleted,
    created_at,
    last_modified_at
)
VALUES
(?, ?, ?, ?, ?, ?, ?, ?),
(?, ?, ?, ?, ?, ?, ?, ?),
(?, ?, ?, ?, ?, ?, ?, ?),
(?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            #
            "92cdeabd827843ad871d0214dcb2d12e",
            "http://example.com/",
            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "content": ["Hello, world!"],
                    },
                },
                separators=(",", ":"),
            ),
            False,
            False,
            "2024-01-01 00:00:00+00:00",
            "2024-01-01 00:00:00+00:00",
            #
            "d2f5229639d946e1a6c539e33d119403",
            "http://alice.example.com/",
            "http://alice.example.com/post/1",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "in-reply-to": [
                            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                        ],
                        "content": ["Welcome!"],
                    },
                },
                separators=(",", ":"),
            ),
            False,
            False,
            "2024-01-02 00:00:00+00:00",
            "2024-01-02 00:00:00+00:00",
            #
            "96135d01f6be4e1c99d0cc5a6a4f1d10",
            "http://example.com/",
            "http://example.com/feed/96135d01-f6be-4e1c-99d0-cc5a6a4f1d10",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "in-reply-to": [
                            "http://alice.example.com/post/1",
                        ],
                        "content": ["Thank you!"],
                    },
                },
                separators=(",", ":"),
            ),
            False,
            False,
            "2024-01-03 00:00:00+00:00",
            "2024-01-03 00:00:00+00:00",
            #
            "12f1ba3d33d6422b87932b6ac17275a9",
            "http://bob.example.com/",
            "http://bob.example.com/posts/42",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "like-of": [
                            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                            "http://example.com/feed/96135d01-f6be-4e1c-99d0-cc5a6a4f1d10",
                        ],
                        "summary": [
                            "Liked: http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e "
                            "and http://example.com/feed/96135d01-f6be-4e1c-99d0-cc5a6a4f1d10"
                        ],
                    },
                },
                separators=(",", ":"),
            ),
            False,
            False,
            "2024-01-07 00:00:00+00:00",
            "2024-01-07 00:00:00+00:00",
        ),
    )
    await db.execute(
        """
INSERT INTO incoming_webmentions (
    source,
    target,
    status
)
VALUES
(?, ?, ?),
(?, ?, ?),
(?, ?, ?);
        """,
        (
            "http://alice.example.com/post/1",
            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
            "success",
            "http://bob.example.com/posts/42",
            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
            "success",
            "http://bob.example.com/posts/42",
            "http://example.com/feed/96135d01-f6be-4e1c-99d0-cc5a6a4f1d10",
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
VALUES
(?, ?, ?);
        """,
        (
            "http://example.com/feed/96135d01-f6be-4e1c-99d0-cc5a6a4f1d10",
            "http://alice.example.com/post/1",
            "success",
        ),
    )
    await db.commit()

    async with current_app.app_context():
        entry = await get_entry(db, UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"))

    assert entry == Entry(
        uuid=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
        author="http://example.com/",
        location="http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
        content=Microformats2(
            type=["h-entry"],
            properties={"content": ["Hello, world!"]},
            children=[
                Microformats2(
                    type=["h-entry"],
                    properties={
                        "in-reply-to": [
                            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                        ],
                        "content": ["Welcome!"],
                    },
                    children=[
                        Microformats2(
                            type=["h-entry"],
                            properties={
                                "in-reply-to": ["http://alice.example.com/post/1"],
                                "content": ["Thank you!"],
                            },
                            children=[
                                Microformats2(
                                    type=["h-entry"],
                                    properties={
                                        "like-of": [
                                            "http://example.com/feed/"
                                            "92cdeabd-8278-43ad-871d-0214dcb2d12e",
                                            "http://example.com/feed/"
                                            "96135d01-f6be-4e1c-99d0-cc5a6a4f1d10",
                                        ],
                                        "summary": [
                                            "Liked: http://example.com/feed/"
                                            "92cdeabd-8278-43ad-871d-0214dcb2d12e and "
                                            "http://example.com/feed/"
                                            "96135d01-f6be-4e1c-99d0-cc5a6a4f1d10"
                                        ],
                                    },
                                    children=[],
                                )
                            ],
                        )
                    ],
                ),
                Microformats2(
                    type=["h-entry"],
                    properties={
                        "like-of": [
                            "http://example.com/feed/"
                            "92cdeabd-8278-43ad-871d-0214dcb2d12e",
                            "http://example.com/feed/"
                            "96135d01-f6be-4e1c-99d0-cc5a6a4f1d10",
                        ],
                        "summary": [
                            "Liked: http://example.com/feed/"
                            "92cdeabd-8278-43ad-871d-0214dcb2d12e and "
                            "http://example.com/feed/"
                            "96135d01-f6be-4e1c-99d0-cc5a6a4f1d10"
                        ],
                    },
                    children=[],
                ),
            ],
        ),
        read=False,
        deleted=False,
        created_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        last_modified_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
    )
