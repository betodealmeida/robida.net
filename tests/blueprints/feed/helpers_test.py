"""
Tests for the feed helper functions.
"""

import json
from datetime import datetime, timezone
from uuid import UUID

from aiosqlite import Connection
from freezegun import freeze_time
from pytest_httpx import HTTPXMock
from quart import Quart
from werkzeug.datastructures import Headers

from robida.blueprints.feed.helpers import (
    build_jsonfeed_item,
    get_entries,
    get_entry,
    get_title,
    make_conditional_response,
    render_microformat,
)
from robida.blueprints.feed.models import JSONFeedAuthor, JSONFeedItem
from robida.models import Entry, Microformats2


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
        entry = await get_entry(UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"))

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
        entry = await get_entry(UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"))

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
        entry = await get_entry(UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"))

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


async def test_get_entries(db: Connection, current_app: Quart) -> None:
    """
    Test the `get_entries` function.
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
            # new, not deleted
            "92cdeabd827843ad871d0214dcb2d12e",
            "http://example.com/",
            "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "content": ["hello world"],
                        "category": ["foo", "bar"],
                    },
                },
                separators=(",", ":"),
            ),
            False,
            False,
            "2024-01-01 00:00:00+00:00",
            "2024-01-01 00:00:00+00:00",
            # new, deleted
            "d2f5229639d946e1a6c539e33d119403",
            "http://example.com/",
            "http://example.com/feed/d2f52296-39d9-46e1-a6c5-39e33d119403",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "content": ["hello world"],
                        "category": ["foo", "bar"],
                    },
                },
                separators=(",", ":"),
            ),
            False,
            True,
            "2024-01-02 00:00:00+00:00",
            "2024-01-02 00:00:00+00:00",
            # new, not deleted, different author
            "96135d01f6be4e1c99d0cc5a6a4f1d10",
            "http://alice.example.com/",
            "http://example.com/feed/96135d01-f6be-4e1c-99d0-cc5a6a4f1d10",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "content": ["hello world"],
                        "category": ["foo", "bar"],
                    },
                },
                separators=(",", ":"),
            ),
            False,
            False,
            "2024-01-01 00:00:00+00:00",
            "2024-01-01 00:00:00+00:00",
            # old, not dleted
            "12f1ba3d33d6422b87932b6ac17275a9",
            "http://example.com/",
            "http://example.com/feed/12f1ba3d-33d6-422b-8793-2b6ac17275a9",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "content": ["hello world"],
                        "category": ["foo", "bar"],
                    },
                },
                separators=(",", ":"),
            ),
            False,
            False,
            "2023-01-01 00:00:00+00:00",
            "2023-01-01 00:00:00+00:00",
        ),
    )
    await db.commit()

    async with current_app.app_context():
        entries = await get_entries(since="2023-12-01 00:00:00+00:00")

    assert entries == [
        Entry(
            uuid=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            author="http://example.com/",
            location="http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
            content={
                "type": ["h-entry"],
                "properties": {"content": ["hello world"], "category": ["foo", "bar"]},
            },
            read=False,
            deleted=False,
            created_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            last_modified_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        )
    ]


async def test_build_jsonfeed_item(current_app: Quart) -> None:
    """
    Test the `build_jsonfeed_item` function.
    """
    async with current_app.app_context():
        assert build_jsonfeed_item(
            Entry(
                uuid=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
                author="http://example.com/",
                location="http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                content={
                    "type": ["h-entry"],
                    "properties": {
                        "name": ["Microformats are amazing"],
                        "author": [
                            {
                                "type": ["h-card"],
                                "properties": {
                                    "name": ["W. Developer"],
                                    "url": ["http://example.com"],
                                },
                                "value": "W. Developer",
                            }
                        ],
                        "published": ["2013-06-13 12:00:00"],
                        "summary": [
                            "In which I extoll the virtues of using microformats."
                        ],
                        "content": [
                            {"value": "Blah blah blah", "html": "<p>Blah blah blah</p>"}
                        ],
                    },
                },
                read=False,
                deleted=False,
                created_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
                last_modified_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            )
        ) == JSONFeedItem(
            id=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            url="http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
            external_url=None,
            title="Microformats are amazing",
            content_html="<p>Blah blah blah</p>",
            content_text="Blah blah blah",
            summary="In which I extoll the virtues of using microformats.",
            image=None,
            banner_image=None,
            date_published=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            date_modified=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            authors=[
                JSONFeedAuthor(
                    name="Beto Dealmeida",
                    url="http://example.com/",
                    avatar="http://example.com/static/photo.jpg",
                )
            ],
            tags=[],
            language=None,
            attachments=[],
        )


@freeze_time("2024-01-01 00:00:00")
async def test_make_conditional_response_no_entries(current_app: Quart) -> None:
    """
    Test the `make_conditional_response` function without entries.
    """
    no_entries_etag = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
    async with current_app.test_request_context("/", method="GET"):
        response = make_conditional_response([])

    assert response.status_code == 200
    assert response.headers == Headers(
        [
            ("Last-Modified", "Mon, 01 Jan 2024 00:00:00 GMT"),
            ("ETag", no_entries_etag),
            ("Content-Type", "text/html; charset=utf-8"),
        ]
    )

    async with current_app.test_request_context(
        "/",
        method="GET",
        headers={"If-None-Match": no_entries_etag},
    ):
        response = make_conditional_response([])

    assert response.status_code == 304

    async with current_app.test_request_context(
        "/",
        method="GET",
        headers={"If-Modified-Since": "Mon, 01 Jan 2024 00:00:00 GMT"},
    ):
        response = make_conditional_response([])

    assert response.status_code == 304

    async with current_app.test_request_context(
        "/",
        method="GET",
        headers={"If-Modified-Since": "Mon, 01 Jan 2022 00:00:00 GMT"},
    ):
        response = make_conditional_response([])

    assert response.status_code == 200

    # both need to match
    async with current_app.test_request_context(
        "/",
        method="GET",
        headers={
            "If-Modified-Since": "Mon, 01 Jan 2024 00:00:00 GMT",
            "If-None-Match": "something else",
        },
    ):
        response = make_conditional_response([])

    assert response.status_code == 200


async def test_render_microformat(httpx_mock: HTTPXMock, current_app: Quart) -> None:
    """
    Test the `render_microformat` function.
    """
    httpx_mock.add_response(
        url="https://tantek.com/",
        html='<a class="h-card" href="https://tantek.com/">Tantek Çelik</a>',
    )

    async with current_app.app_context():
        rendered = await render_microformat(
            {
                "type": ["h-entry"],
                "properties": {
                    "published": ["2013-03-07"],
                    "content": ["I ate a cheese sandwich."],
                    "author": ["https://tantek.com/"],
                },
            }
        )

    assert (
        rendered
        == """<article class="h-entry">
    <p class="p-content e-content">
        I ate a cheese sandwich.
    </p>
    <footer>
        <p>
            <span title="A note (h-entry)">
                📔
            </span>
            Published by
            <a class="h-card" href="https://tantek.com/">
                Tantek Çelik
            </a>
            @
            <time class="dt-published" datetime="2013-03-07">
                Thu, 07 Mar 2013 00:00:00
            </time>
        </p>
    </footer>
</article>
"""
    )


async def test_get_title() -> None:
    """
    Test the `get_title` helper function.
    """

    assert get_title({"properties": {"name": ["Hello, World!"]}}) == "Hello, World!"
    assert get_title({"properties": {"content": ["Hello, World!"]}}) == "Hello, World!"
    assert (
        get_title(
            {
                "properties": {
                    "content": [
                        {"value": "Hello, World!", "html": "<h1>Hello, world!</h1>"}
                    ]
                }
            }
        )
        == "Hello, World!"
    )
    assert get_title({"properties": {}}) == "Untitled"
