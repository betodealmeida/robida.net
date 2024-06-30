"""
Tests for the helper functions.
"""

# pylint: disable=redefined-outer-name, line-too-long, too-many-lines

import json
import urllib.parse
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID

import httpx
import pytest
from aiosqlite import Connection
from freezegun import freeze_time
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture
from quart import Quart

from robida.blueprints.webmention.helpers import (
    MODERATION_MESSAGE,
    create_entry,
    extract_urls,
    get_webmention_hentry,
    find_endpoint,
    find_in_json,
    find_vouch,
    is_domain_trusted,
    is_url_in_app,
    is_vouch_valid,
    links_back,
    match_url,
    poll_webmention,
    process_webmention,
    queue_webmention,
    send_salmention,
    send_webmention,
    send_webmentions,
    validate_webmention,
    verify_request,
)
from robida.blueprints.webmention.models import WebMentionStatus
from robida.db import load_entries
from robida.models import Microformats2


async def test_verify_request(current_app: Quart) -> None:
    """
    Test the `verify_request` function.
    """
    async with current_app.app_context():
        verify_request("https://other.example.com", "http://example.com/")

        with pytest.raises(ValueError) as excinfo:
            verify_request("gemini://other.example.com", "http://example.com/")
        assert (
            str(excinfo.value)
            == 'Invalid scheme ("gemini") in source. Must be one of: http, https'
        )

        with pytest.raises(ValueError) as excinfo:
            verify_request(
                "https://other.example.com",
                "http://example.com/invalid/endpoint",
            )
        assert (
            str(excinfo.value)
            == 'Target URL ("http://example.com/invalid/endpoint") is not valid.'
        )


@freeze_time("2024-01-01 00:00:00", auto_tick_seconds=3600)
async def test_process_webmention(mocker: MockerFixture) -> None:
    """
    Test the `process_webmention` function.
    """

    async def gen() -> AsyncGenerator[tuple[WebMentionStatus, str, str | None], None]:
        """
        Simulate webmention processing.
        """
        yield (
            WebMentionStatus.RECEIVED,
            "The webmention was received and is queued for processing.",
            None,
        )
        yield (
            WebMentionStatus.PROCESSING,
            "The webmention is being processed.",
            None,
        )
        yield (
            WebMentionStatus.SUCCESS,
            "The webmention processed successfully and approved.",
            json.dumps(
                {
                    "type": ["h-entry"],
                    "properties": {
                        "author": {"url": "https://other.example.com"},
                        "content": [
                            "This is a dummy entry created by the webmention processor."
                        ],
                    },
                },
                separators=(",", ":"),
            ),
        )

    mocker.patch(
        "robida.blueprints.webmention.helpers.validate_webmention",
        return_value=gen(),
    )
    get_db = mocker.patch("robida.blueprints.webmention.helpers.get_db")

    await process_webmention(
        UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
        "https://other.example.com",
        "http://example.com/",
        None,
    )

    sql = """
UPDATE incoming_webmentions
SET
    status = ?,
    message = ?,
    content = ?,
    last_modified_at = ?
WHERE
    uuid = ?;
                """
    async with get_db() as db:
        db.execute.assert_has_calls(
            [
                mocker.call(
                    sql,
                    (
                        WebMentionStatus.RECEIVED,
                        "The webmention was received and is queued for processing.",
                        None,
                        datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
                        "92cdeabd827843ad871d0214dcb2d12e",
                    ),
                ),
                mocker.call(
                    sql,
                    (
                        WebMentionStatus.PROCESSING,
                        "The webmention is being processed.",
                        None,
                        datetime(2024, 1, 1, 1, 0, tzinfo=timezone.utc),
                        "92cdeabd827843ad871d0214dcb2d12e",
                    ),
                ),
                mocker.call(
                    sql,
                    (
                        WebMentionStatus.SUCCESS,
                        "The webmention processed successfully and approved.",
                        '{"type":["h-entry"],"properties":{"author":{"url":"https://other.example.com"},"content":["This is a dummy entry created by the webmention processor."]}}',
                        datetime(2024, 1, 1, 2, 0, tzinfo=timezone.utc),
                        "92cdeabd827843ad871d0214dcb2d12e",
                    ),
                ),
            ]
        )


@freeze_time("2024-01-01 00:00:00", auto_tick_seconds=3600)
async def test_process_webmention_failure(mocker: MockerFixture) -> None:
    """
    Test the `process_webmention` function failing.
    """

    async def gen() -> AsyncGenerator[tuple[WebMentionStatus, str, str | None], None]:
        """
        Simulate webmention processing.
        """
        yield (
            WebMentionStatus.FAILURE,
            "An unknown error occurred. I blame the goblins.",
            None,
        )

    mocker.patch(
        "robida.blueprints.webmention.helpers.validate_webmention",
        return_value=gen(),
    )
    get_db = mocker.patch("robida.blueprints.webmention.helpers.get_db")

    await process_webmention(
        UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
        "https://other.example.com",
        "http://example.com/",
        None,
    )

    sql = """
UPDATE incoming_webmentions
SET
    status = ?,
    message = ?,
    content = ?,
    last_modified_at = ?
WHERE
    uuid = ?;
                """
    async with get_db() as db:
        db.execute.assert_has_calls(
            [
                mocker.call(
                    sql,
                    (
                        WebMentionStatus.FAILURE,
                        "An unknown error occurred. I blame the goblins.",
                        None,
                        datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
                        "92cdeabd827843ad871d0214dcb2d12e",
                    ),
                ),
                mocker.call(
                    "UPDATE entries SET deleted = ? WHERE uuid = ?;",
                    (True, "92cdeabd827843ad871d0214dcb2d12e"),
                ),
            ]
        )


async def test_validate_webmention_invalid_scheme(db: Connection) -> None:
    """
    Test the `validate_webmention` function when the source scheme is invalid.
    """
    validator = validate_webmention(
        db,
        UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
        "gemini://other.example.com",
        "http://example.com/",
    )

    (status, message, content) = await anext(validator)
    assert status == WebMentionStatus.FAILURE
    assert message == 'Invalid scheme ("gemini") in source. Must be one of: http, https'
    assert content is None

    with pytest.raises(StopAsyncIteration):
        await anext(validator)


async def test_validate_webmention_invalid_url(
    httpx_mock: HTTPXMock,
    db: Connection,
    current_app: Quart,
) -> None:
    """
    Test the `validate_webmention` function when the source is unavailable.
    """
    httpx_mock.add_response(url="https://other.example.com", status_code=404)

    async with current_app.app_context():
        validator = validate_webmention(
            db,
            UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            "https://other.example.com",
            "http://example.com/",
        )

        (status, message, content) = await anext(validator)
        assert status == WebMentionStatus.PROCESSING
        assert message == "The webmention is being processed."
        assert content is None

        (status, message, content) = await anext(validator)
        assert status == WebMentionStatus.FAILURE
        assert message == (
            "Failed to fetch source URL: Client error '404 Not Found' for url "
            "'https://other.example.com'\n"
            "For more information check: "
            "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/404"
        )
        assert content is None

        with pytest.raises(StopAsyncIteration):
            await anext(validator)


async def test_validate_webmention_no_backlink(
    httpx_mock: HTTPXMock,
    db: Connection,
    current_app: Quart,
) -> None:
    """
    Test the `validate_webmention` function when the source doesn't link to the target.
    """
    httpx_mock.add_response(
        url="https://other.example.com",
        html='<a href="https://example.com/invalid">Invalid</a>',
        headers={"Content-Type": "text/html"},
    )

    async with current_app.app_context():
        validator = validate_webmention(
            db,
            UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            "https://other.example.com",
            "http://example.com/",
        )

        (status, message, content) = await anext(validator)
        assert status == WebMentionStatus.PROCESSING
        assert message == "The webmention is being processed."
        assert content is None

        (status, message, content) = await anext(validator)
        assert status == WebMentionStatus.FAILURE
        assert message == "The target URL is not mentioned in the source."
        assert content is None

        with pytest.raises(StopAsyncIteration):
            await anext(validator)


@freeze_time("2024-01-01 00:00:00")
async def test_validate_webmention_needs_moderation(
    mocker: MockerFixture,
    httpx_mock: HTTPXMock,
    db: Connection,
    current_app: Quart,
) -> None:
    """
    Test the `validate_webmention` function when the webmention needs moderation.
    """
    mocker.patch(
        "robida.blueprints.webmention.helpers.is_domain_trusted",
        return_value=False,
    )
    mocker.patch(
        "robida.blueprints.webmention.helpers.is_vouch_valid",
        return_value=False,
    )
    httpx_mock.add_response(
        url="https://other.example.com",
        html='<a href="http://example.com/">Look at this!</a>',
        headers={"Content-Type": "text/html"},
    )

    async with current_app.app_context():
        validator = validate_webmention(
            db,
            UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            "https://other.example.com",
            "http://example.com/",
        )

        (status, message, content) = await anext(validator)
        assert status == WebMentionStatus.PROCESSING
        assert message == "The webmention is being processed."
        assert content is None

        (status, message, content) = await anext(validator)
        assert status == WebMentionStatus.PENDING_MODERATION
        assert message == MODERATION_MESSAGE
        assert content == json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "url": ["https://other.example.com"],
                    "content": [
                        {
                            "html": '<a rel="nofollow" href="https://other.example.com">https://other.example.com</a>',
                            "value": "https://other.example.com",
                        },
                    ],
                    "published": ["2024-01-01T00:00:00+00:00"],
                },
            },
            separators=(",", ":"),
        )

        with pytest.raises(StopAsyncIteration):
            await anext(validator)


@freeze_time("2024-01-01 00:00:00")
async def test_validate_webmention(
    mocker: MockerFixture,
    httpx_mock: HTTPXMock,
    db: Connection,
    current_app: Quart,
) -> None:
    """
    Test the `validate_webmention` function.
    """
    mocker.patch(
        "robida.blueprints.webmention.helpers.is_domain_trusted",
        return_value=True,
    )
    mocker.patch(
        "robida.blueprints.webmention.helpers.is_vouch_valid",
        return_value=True,
    )
    send_salmention = mocker.patch(
        "robida.blueprints.webmention.helpers.send_salmention"
    )
    create_entry = mocker.patch("robida.blueprints.webmention.helpers.create_entry")
    httpx_mock.add_response(
        url="https://other.example.com",
        html='<a href="http://example.com/">Look at this!</a>',
        headers={"Content-Type": "text/html"},
    )

    async with current_app.app_context():
        validator = validate_webmention(
            db,
            UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            "https://other.example.com",
            "http://example.com/",
        )

        (status, message, content) = await anext(validator)
        assert status == WebMentionStatus.PROCESSING
        assert message == "The webmention is being processed."
        assert content is None

        (status, message, content) = await anext(validator)
        assert status == WebMentionStatus.SUCCESS
        assert message == "The webmention processed successfully and approved."
        assert content == json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "url": ["https://other.example.com"],
                    "content": [
                        {
                            "html": '<a rel="nofollow" href="https://other.example.com">https://other.example.com</a>',
                            "value": "https://other.example.com",
                        }
                    ],
                    "published": ["2024-01-01T00:00:00+00:00"],
                },
            },
            separators=(",", ":"),
        )

        with pytest.raises(StopAsyncIteration):
            await anext(validator)

    create_entry.assert_called_with(
        db,
        UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
        "https://other.example.com",
        Microformats2(
            type=["h-entry"],
            properties={
                "url": ["https://other.example.com"],
                "content": [
                    {
                        "html": '<a rel="nofollow" href="https://other.example.com">https://other.example.com</a>',
                        "value": "https://other.example.com",
                    }
                ],
                "published": ["2024-01-01T00:00:00+00:00"],
            },
        ),
    )

    send_salmention.assert_called_with("http://example.com/")


async def test_get_webmention_hentry() -> None:
    """
    Test the `get_webmention_hentry` function.
    """
    assert get_webmention_hentry(
        httpx.Response(
            text="""
<article class="h-entry">
    <h1 class="p-name">Microformats are amazing</h1>
    <p>Published by <a class="p-author h-card" href="http://w.example.com">W. Developer</a>
    on <time class="dt-published" datetime="2013-06-13 12:00:00">13<sup>th</sup> June 2013</time></p>

    <p class="p-summary">In which I extoll the virtues of using microformats.</p>

    <div class="e-content">
        <p><a href="http://example.com/">This page</a>.</p>
    </div>
</article>
            """,
            headers={"Content-Type": "text/html"},
            status_code=200,
        ),
        "http://other.example.com/",
        "http://example.com/",
    ) == Microformats2(
        type=["h-entry"],
        properties={
            "name": ["Microformats are amazing"],
            "author": [
                {
                    "type": ["h-card"],
                    "properties": {
                        "name": ["W. Developer"],
                        "url": ["http://w.example.com"],
                    },
                    "value": "W. Developer",
                }
            ],
            "published": ["2013-06-13 12:00:00"],
            "summary": ["In which I extoll the virtues of using microformats."],
            "content": [
                {
                    "value": "This page.",
                    "html": '<p><a href="http://example.com/">This page</a>.</p>',
                }
            ],
        },
    )


@freeze_time("2024-01-01 00:00:00")
async def test_get_webmention_hentry_no_microformats() -> None:
    """
    Test the `get_webmention_hentry` function when the page has no microformats.
    """
    assert get_webmention_hentry(
        httpx.Response(
            text="<p>Hi, there!</p>",
            headers={"Content-Type": "text/html"},
            status_code=200,
        ),
        "http://other.example.com/",
        "http://example.com/",
    ) == Microformats2(
        type=["h-entry"],
        properties={
            "url": ["http://other.example.com/"],
            "content": [
                {
                    "html": '<a rel="nofollow" href="http://other.example.com/">http://other.example.com/</a>',
                    "value": "http://other.example.com/",
                }
            ],
            "published": ["2024-01-01T00:00:00+00:00"],
        },
    )


@freeze_time("2024-01-01 00:00:00")
async def test_get_webmention_hentry_json() -> None:
    """
    Test the `get_webmention_hentry` function when the response is JSON.
    """
    hentry = {
        "type": ["h-entry"],
        "properties": {
            "content": ["Microformats are amazing"],
            "in-reply-to": ["http://example.com/"],
        },
    }

    assert get_webmention_hentry(
        httpx.Response(
            json=hentry,
            headers={"Content-Type": "application/json"},
            status_code=200,
        ),
        "http://other.example.com/",
        "http://example.com/",
    ) == Microformats2(
        type=["h-entry"],
        properties={
            "content": ["Microformats are amazing"],
            "in-reply-to": ["http://example.com/"],
        },
        children=[],
    )


@freeze_time("2024-01-01 00:00:00")
async def test_get_webmention_hentry_json_nested() -> None:
    """
    Test the `get_webmention_hentry` function with a nested response.
    """
    hentry = {
        "type": ["h-entry"],
        "properties": {
            "content": ["Microformats are amazing"],
            "in-reply-to": ["http://example.com/"],
        },
    }
    hfeed = {
        "type": ["h-feed"],
        "properties": {},
        "children": [hentry],
    }

    assert get_webmention_hentry(
        httpx.Response(
            json=hfeed,
            headers={"Content-Type": "application/json"},
            status_code=200,
        ),
        "http://other.example.com/",
        "http://example.com/",
    ) == Microformats2(
        type=["h-entry"],
        properties={
            "content": ["Microformats are amazing"],
            "in-reply-to": ["http://example.com/"],
        },
        children=[],
    )


@freeze_time("2024-01-01 00:00:00")
async def test_get_webmention_hentry_json_not_dict() -> None:
    """
    Test the `get_webmention_hentry` function with a non-object JSON response.
    """
    assert get_webmention_hentry(
        httpx.Response(
            json=["foo", "bar"],
            headers={"Content-Type": "application/json"},
            status_code=200,
        ),
        "http://other.example.com/",
        "http://example.com/",
    ) == Microformats2(
        type=["h-entry"],
        properties={
            "url": ["http://other.example.com/"],
            "content": [
                {
                    "html": '<a rel="nofollow" href="http://other.example.com/">http://other.example.com/</a>',
                    "value": "http://other.example.com/",
                }
            ],
            "published": ["2024-01-01T00:00:00+00:00"],
        },
    )


@freeze_time("2024-01-01 00:00:00")
async def test_get_webmention_hentry_json_no_microformats() -> None:
    """
    Test the `get_webmention_hentry` function when the h-entry is invalid.
    """
    assert get_webmention_hentry(
        httpx.Response(
            json={"type": ["h-entry"], "foo": "http://example.com/"},
            headers={"Content-Type": "application/json"},
            status_code=200,
        ),
        "http://other.example.com/",
        "http://example.com/",
    ) == Microformats2(
        type=["h-entry"],
        properties={
            "url": ["http://other.example.com/"],
            "content": [
                {
                    "html": '<a rel="nofollow" href="http://other.example.com/">http://other.example.com/</a>',
                    "value": "http://other.example.com/",
                }
            ],
            "published": ["2024-01-01T00:00:00+00:00"],
        },
    )


async def test_is_domain_trusted(db: Connection, current_app: Quart) -> None:
    """
    Test the `is_domain_trusted` function.
    """
    await db.execute(
        "INSERT INTO trusted_domains (domain) VALUES (?)",
        ("example.com",),
    )
    await db.commit()

    async with current_app.app_context():
        assert await is_domain_trusted(db, "http://example.com")
        assert await is_domain_trusted(db, "https://example.com/callback")
        assert not await is_domain_trusted(db, "https://other.example.com/callback")


async def test_is_vouch_valid_no_vouch(db: Connection) -> None:
    """
    Test the `is_vouch_valid` function when no vouch is passed.
    """
    assert not await is_vouch_valid(db, None, "https://bob.example.com")


async def test_is_vouch_valid_not_trusted(
    mocker: MockerFixture, db: Connection
) -> None:
    """
    Test the `is_vouch_valid` function when the vouch is not trusted.
    """
    mocker.patch(
        "robida.blueprints.webmention.helpers.is_domain_trusted",
        return_value=False,
    )
    assert not await is_vouch_valid(
        db,
        "https://alice.example.com",
        "https://bob.example.com",
    )


async def test_is_vouch_valid_vouch_error(
    mocker: MockerFixture,
    httpx_mock: HTTPXMock,
    db: Connection,
) -> None:
    """
    Test the `is_vouch_valid` function when the vouch returns an error.
    """
    mocker.patch(
        "robida.blueprints.webmention.helpers.is_domain_trusted",
        return_value=True,
    )
    httpx_mock.add_response(
        url="https://alice.example.com",
        status_code=404,
    )
    assert not await is_vouch_valid(
        db,
        "https://alice.example.com",
        "https://bob.example.com/post/1",
    )


async def test_is_vouch_valid(
    mocker: MockerFixture,
    httpx_mock: HTTPXMock,
    db: Connection,
) -> None:
    """
    Test the `is_vouch_valid` function.
    """
    mocker.patch(
        "robida.blueprints.webmention.helpers.is_domain_trusted",
        return_value=True,
    )
    httpx_mock.add_response(
        url="https://alice.example.com",
        html='<a href="https://bob.example.com">Bob</a>',
        headers={"Content-Type": "text/html"},
    )
    assert await is_vouch_valid(
        db,
        "https://alice.example.com",
        "https://bob.example.com/post/1",
    )


@freeze_time("2024-01-01 00:00:00")
async def test_create_entry(db: Connection, current_app: Quart) -> None:
    """
    Test the `create_entry` function.
    """
    async with current_app.app_context():
        await create_entry(
            db,
            UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            "https://other.example.com",
            Microformats2(
                type=["h-entry"],
                properties={
                    "author": {"url": "https://other.example.com"},
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
        "author": "https://other.example.com",
        "location": "https://other.example.com",
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "author": {"url": "https://other.example.com"},
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


async def test_create_entry_published(db: Connection, current_app: Quart) -> None:
    """
    Test the `create_entry` function when the h-entry has the `published` attribute.
    """
    async with current_app.app_context():
        await create_entry(
            db,
            UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            "https://other.example.com",
            Microformats2(
                type=["h-entry"],
                properties={
                    "author": {"url": "https://other.example.com"},
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
        "author": "https://other.example.com",
        "location": "https://other.example.com",
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "author": {"url": "https://other.example.com"},
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


def test_match_url() -> None:
    """
    Test the `match_url` function.
    """
    matcher = match_url("http://example.com/")
    assert matcher("http://example.com/")
    assert not matcher("http://example.com/callback")

    matcher = match_url("http://example.com/", domain_only=True)
    assert matcher("http://example.com/")
    assert matcher("http://example.com/callback")


def test_find_in_json() -> None:
    """
    Test the `find_in_json` function.
    """

    def test(value):
        return value == "http://example.com/"

    assert find_in_json({"url": "http://example.com/"}, test)
    assert find_in_json({"author": [{"url": "http://example.com/"}]}, test)
    assert not find_in_json({"author": [{"url": "http://other.example.com/"}]}, test)


def test_links_back_error() -> None:
    """
    Test the `links_back` function with an error response.
    """
    assert not links_back(
        httpx.Response(
            status_code=400,
        ),
        "http://example.com/",
    )


def test_links_back_html() -> None:
    """
    Test the `links_back` function with HTML pages.
    """
    assert links_back(
        httpx.Response(
            text='<a href="http://example.com/">Example</a>',
            headers={"Content-Type": "text/html"},
            status_code=200,
        ),
        "http://example.com/",
    )
    assert not links_back(
        httpx.Response(
            text='<a href="http://example.com/about">Example</a>',
            headers={"Content-Type": "text/html"},
            status_code=200,
        ),
        "http://example.com/",
    )
    assert links_back(
        httpx.Response(
            text='<a href="http://example.com/post/1">Example</a>',
            headers={"Content-Type": "text/html"},
            status_code=200,
        ),
        "http://example.com/about",
        domain_only=True,
    )


def test_links_back_json() -> None:
    """
    Test the `links_back` function with JSON responses.
    """
    assert links_back(
        httpx.Response(
            json={"url": "http://example.com/"},
            headers={"Content-Type": "application/json"},
            status_code=200,
        ),
        "http://example.com/",
    )
    assert not links_back(
        httpx.Response(
            json={"url": "http://example.com/about"},
            headers={"Content-Type": "application/json"},
            status_code=200,
        ),
        "http://example.com/",
    )
    assert links_back(
        httpx.Response(
            json={"url": "http://example.com/post/1"},
            headers={"Content-Type": "application/json"},
            status_code=200,
        ),
        "http://example.com/about",
        domain_only=True,
    )


def test_links_back_text() -> None:
    """
    Test the `links_back` function with plain text.
    """
    assert links_back(
        httpx.Response(
            text="Check out http://example.com/",
            headers={"Content-Type": "text/plain"},
            status_code=200,
        ),
        "http://example.com/",
    )
    assert not links_back(
        httpx.Response(
            text="Check out http://example.com/about",
            headers={"Content-Type": "text/plain"},
            status_code=200,
        ),
        "http://example.com/",
    )
    assert links_back(
        httpx.Response(
            text="Check out http://example.com/post/1",
            headers={"Content-Type": "text/plain"},
            status_code=200,
        ),
        "http://example.com/about",
        domain_only=True,
    )


def test_links_back_non_supported(mocker: MockerFixture) -> None:
    """
    Test the `links_back` function with a non-supported content type.
    """
    logger = mocker.patch("robida.blueprints.webmention.helpers.logger")

    assert links_back(
        httpx.Response(
            text="Check out [this site](http://example.com/)",
            headers={"Content-Type": "text/markdown"},
            status_code=200,
        ),
        "http://example.com/",
    )
    assert not links_back(
        httpx.Response(
            text="Check out [this site](http://example.com/about)",
            headers={"Content-Type": "text/markdown"},
            status_code=200,
        ),
        "http://example.com/",
    )
    assert links_back(
        httpx.Response(
            text="Check out [this post](http://example.com/post/1)",
            headers={"Content-Type": "text/markdown"},
            status_code=200,
        ),
        "http://example.com/about",
        domain_only=True,
    )

    logger.warning.assert_called_with(
        'Unknown content type "%s", falling back to text/plain',
        "text/markdown",
    )


async def test_is_url_in_app(current_app: Quart) -> None:
    """
    Test the `is_url_in_app` function.
    """
    async with current_app.app_context():
        assert is_url_in_app("http://example.com/")
        assert not is_url_in_app("http://other.example.com/")


async def test_find_endpoint_invalid_scheme() -> None:
    """
    Test the `find_endpoint` function when an invalid scheme is passed.
    """
    async with httpx.AsyncClient() as client:
        assert await find_endpoint(client, "gemini://example.com/") is None


async def test_find_endpoint_head_error(httpx_mock: HTTPXMock) -> None:
    """
    Test the `find_endpoint` function when the `HEAD` request fails.
    """
    httpx_mock.add_response(url="http://example.com/", status_code=404)

    async with httpx.AsyncClient() as client:
        assert await find_endpoint(client, "http://example.com/") is None


async def test_find_endpoint_from_head(httpx_mock: HTTPXMock) -> None:
    """
    Test the `find_endpoint` function reading the endpoint from the `Link` header.
    """
    httpx_mock.add_response(
        url="http://example.com/",
        headers={"Link": '<http://example.com/webmention>; rel="webmention"'},
    )

    async with httpx.AsyncClient() as client:
        assert (
            await find_endpoint(client, "http://example.com/")
            == "http://example.com/webmention"
        )


async def test_find_endpoint_non_html(httpx_mock: HTTPXMock) -> None:
    """
    Test the `find_endpoint` function when the file is not HTML.
    """
    httpx_mock.add_response(
        url="http://example.com/",
        headers={"Content-Type": "application/json"},
    )

    async with httpx.AsyncClient() as client:
        assert await find_endpoint(client, "http://example.com/") is None


async def test_find_endpoint_get_error(httpx_mock: HTTPXMock) -> None:
    """
    Test the `find_endpoint` function when the `GET` request fails.
    """
    httpx_mock.add_response(
        method="HEAD",
        url="http://example.com/",
        headers={"Content-Type": "text/html"},
    )
    httpx_mock.add_response(
        method="GET",
        url="http://example.com/",
        status_code=404,
    )

    async with httpx.AsyncClient() as client:
        assert await find_endpoint(client, "http://example.com/") is None


async def test_find_endpoint_from_html(httpx_mock: HTTPXMock) -> None:
    """
    Test the `find_endpoint` function reading the endpoint from the HTML.
    """
    httpx_mock.add_response(
        url="http://example.com/",
        html="""
<link rel="self" href="http://example.com/"/>
<a rel="webmention" href="http://example.com/webmention">Webmention</a>
<a href="about.html">About</a>
        """,
        headers={"Content-Type": "text/html"},
    )

    async with httpx.AsyncClient() as client:
        assert (
            await find_endpoint(client, "http://example.com/")
            == "http://example.com/webmention"
        )


async def test_find_endpoint_not_found(httpx_mock: HTTPXMock) -> None:
    """
    Test the `find_endpoint` function reading the endpoint is not found in the HTML.
    """
    httpx_mock.add_response(
        url="http://example.com/",
        html='<a href="about.html">About</a>',
        headers={"Content-Type": "text/html"},
    )

    async with httpx.AsyncClient() as client:
        assert await find_endpoint(client, "http://example.com/") is None


async def test_find_vouch(
    db: Connection,
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the `find_vouch` function.
    """
    httpx_mock.add_response(
        url="http://alice.example.com/",
        html="""
<a href="https://duckduckgo.com/">DuckDuckGo</a>
<a href="/post/1">First post</a>
        """,
    )
    httpx_mock.add_response(
        url="http://alice.example.com/post/1",
        html="""
<a href="https://duckduckgo.com/">DuckDuckGo</a>
<a href="/post/2">Next post</a>
        """,
    )
    httpx_mock.add_response(
        url="http://alice.example.com/post/2",
        html="""
<a href="/post/1">Previous post</a>
<a href="https://duckduckgo.com/">DuckDuckGo</a>
<a href="/post/3">Next post</a>
        """,
    )
    httpx_mock.add_response(
        url="http://alice.example.com/post/3",
        html="""
<a href="/post/2">Previous post</a>
<a href="https://duckduckgo.com/">DuckDuckGo</a>
<a href="http://carol.example.com/colophon.html">I really like this!</a>
        """,
    )
    httpx_mock.add_response(
        url="http://carol.example.com/post/2",
        html="""
<a href="http://example.com/">Robida is cool</a>
        """,
    )

    await db.execute(
        """
INSERT INTO incoming_webmentions (
    uuid,
    source,
    target,
    vouch,
    status,
    message,
    created_at,
    last_modified_at
)
VALUES
    (?, ?, ?, ?, ?, ?, ?, ?),
    (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            "92cdeabd827843ad871d0214dcb2d12e",
            "http://carol.example.com/post/1",
            "http://bob.example.com/about.html",
            None,
            "success",
            "The webmention processed successfully and approved.",
            "2023-01-01 00:00:00+00:00",
            "2023-01-01 00:00:00+00:00",
            #
            "492875f4a5bf49c99686e0a158366582",
            "http://carol.example.com/post/2",
            "http://bob.example.com/post/42",
            None,
            "success",
            "The webmention processed successfully and approved.",
            "2023-12-01 00:00:00+00:00",
            "2023-12-01 00:00:00+00:00",
        ),
    )
    await db.commit()

    async with current_app.app_context():
        async with httpx.AsyncClient() as client:
            assert (
                await find_vouch(
                    db,
                    client,
                    "http://example.com/post/42",
                    "http://alice.example.com/post/1",
                )
                == "http://carol.example.com/post/2"
            )


async def test_find_vouch_link_gone(
    db: Connection,
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the `find_vouch` function when the incoming webmention no longer exists.
    """
    httpx_mock.add_response(
        url="http://alice.example.com/",
        html="""
<a href="https://duckduckgo.com/">DuckDuckGo</a>
<a href="/post/1">First post</a>
        """,
    )
    httpx_mock.add_response(
        url="http://alice.example.com/post/1",
        html="""
<a href="https://duckduckgo.com/">DuckDuckGo</a>
<a href="/post/2">Next post</a>
        """,
    )
    httpx_mock.add_response(
        url="http://alice.example.com/post/2",
        html="""
<a href="/post/1">Previous post</a>
<a href="https://duckduckgo.com/">DuckDuckGo</a>
<a href="/post/3">Next post</a>
        """,
    )
    httpx_mock.add_response(
        url="http://alice.example.com/post/3",
        html="""
<a href="/post/2">Previous post</a>
<a href="https://duckduckgo.com/">DuckDuckGo</a>
<a href="http://carol.example.com/colophon.html">I really like this!</a>
        """,
    )
    httpx_mock.add_response(
        url="http://carol.example.com/post/1",
        html="""
<p>This page has been deleted.</p>
        """,
        status_code=410,
    )
    httpx_mock.add_response(
        url="http://carol.example.com/post/2",
        html="""
<p>This page has been deleted.</p>
        """,
        status_code=410,
    )

    await db.execute(
        """
INSERT INTO incoming_webmentions (
    uuid,
    source,
    target,
    vouch,
    status,
    message,
    created_at,
    last_modified_at
)
VALUES
    (?, ?, ?, ?, ?, ?, ?, ?),
    (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            "92cdeabd827843ad871d0214dcb2d12e",
            "http://carol.example.com/post/1",
            "http://bob.example.com/about.html",
            None,
            "success",
            "The webmention processed successfully and approved.",
            "2023-01-01 00:00:00+00:00",
            "2023-01-01 00:00:00+00:00",
            #
            "492875f4a5bf49c99686e0a158366582",
            "http://carol.example.com/post/2",
            "http://bob.example.com/post/42",
            None,
            "success",
            "The webmention processed successfully and approved.",
            "2023-12-01 00:00:00+00:00",
            "2023-12-01 00:00:00+00:00",
        ),
    )
    await db.commit()

    async with current_app.app_context():
        async with httpx.AsyncClient() as client:
            assert (
                await find_vouch(
                    db,
                    client,
                    "http://example.com/post/42",
                    "http://alice.example.com/post/1",
                )
                is None
            )


async def test_find_vouch_no_path(
    db: Connection,
    httpx_mock: HTTPXMock,
    current_app: Quart,
) -> None:
    """
    Test the `find_vouch` function when no path can be found.
    """
    httpx_mock.add_response(
        url="http://alice.example.com/",
        html="""
<a href="https://duckduckgo.com/">DuckDuckGo</a>
        """,
    )
    httpx_mock.add_response(
        url="http://alice.example.com/post/1",
        html="""
<a href="https://duckduckgo.com/">DuckDuckGo</a>
<a rel="alternate" href="http://alice.example.com/feed.json">My JSON Feed</a>
        """,
    )
    httpx_mock.add_response(
        url="http://alice.example.com/feed.json",
        json={"hello": "world"},
    )

    await db.execute(
        """
INSERT INTO incoming_webmentions (
    uuid,
    source,
    target,
    vouch,
    status,
    message,
    created_at,
    last_modified_at
)
VALUES
    (?, ?, ?, ?, ?, ?, ?, ?),
    (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            "92cdeabd827843ad871d0214dcb2d12e",
            "http://carol.example.com/post/1",
            "http://bob.example.com/about.html",
            None,
            "success",
            "The webmention processed successfully and approved.",
            "2023-01-01 00:00:00+00:00",
            "2023-01-01 00:00:00+00:00",
            #
            "492875f4a5bf49c99686e0a158366582",
            "http://carol.example.com/post/2",
            "http://bob.example.com/post/42",
            None,
            "success",
            "The webmention processed successfully and approved.",
            "2023-12-01 00:00:00+00:00",
            "2023-12-01 00:00:00+00:00",
        ),
    )
    await db.commit()

    async with current_app.app_context():
        async with httpx.AsyncClient() as client:
            assert (
                await find_vouch(
                    db,
                    client,
                    "http://example.com/post/42",
                    "http://alice.example.com/post/1",
                )
                is None
            )


async def test_find_vouch_no_domains(db: Connection, current_app: Quart) -> None:
    """
    Test the `find_vouch` function when there are no domains.

    When there are no incoming webmentions yet we need to short-circuit the function to
    avoid crawling the whole target website.
    """
    async with current_app.app_context():
        async with httpx.AsyncClient() as client:
            assert (
                await find_vouch(
                    db,
                    client,
                    "http://example.com/post/42",
                    "http://alice.example.com/post/1",
                )
                is None
            )


@freeze_time("2024-01-01 00:00:00", auto_tick_seconds=3600)
async def test_send_salmention(mocker: MockerFixture, current_app: Quart) -> None:
    """
    Test the `send_salmention` function.
    """
    send_webmentions = mocker.patch(
        "robida.blueprints.webmention.helpers.send_webmentions"
    )

    await load_entries(current_app)
    async with current_app.app_context():
        await send_salmention(
            "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534"
        )

    send_webmentions.assert_called_with(
        "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
        Microformats2(
            type=["h-entry"],
            properties={
                "url": ["http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534"],
                "content": ["Hello, world!"],
                "category": ["note"],
                "published": ["2024-01-01T00:00:00+00:00"],
                "author": [
                    {
                        "type": ["h-card"],
                        "properties": {
                            "name": ["Beto Dealmeida"],
                            "url": ["http://example.com/"],
                        },
                    }
                ],
            },
            children=[
                Microformats2(
                    type=["h-entry"],
                    properties={
                        "url": ["http://alice.example.com/post/1"],
                        "in-reply-to": [
                            "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534"
                        ],
                        "content": ["Welcome!"],
                        "published": ["2024-01-01T09:00:00+00:00"],
                        "author": [
                            {
                                "type": ["h-card"],
                                "properties": {
                                    "name": ["Alice"],
                                    "url": ["http://alice.example.com"],
                                },
                            }
                        ],
                    },
                    children=[
                        Microformats2(
                            type=["h-entry"],
                            properties={
                                "url": [
                                    "http://example.com/feed/99111091-26c7-4e3e-a0be-436fbeee0d14"
                                ],
                                "in-reply-to": ["http://alice.example.com/post/1"],
                                "content": ["Thank you!"],
                                "category": ["note"],
                                "published": ["2024-01-01T12:00:00+00:00"],
                                "author": [
                                    {
                                        "type": ["h-card"],
                                        "properties": {
                                            "name": ["Beto Dealmeida"],
                                            "url": ["http://example.com/"],
                                        },
                                    }
                                ],
                            },
                            children=[],
                        )
                    ],
                )
            ],
        ),
    )


async def test_send_webmentions(
    mocker: MockerFixture,
    db: Connection,
    current_app: Quart,
) -> None:
    """
    Test the `send_webmentions` function.
    """
    queue_webmention = mocker.patch(
        "robida.blueprints.webmention.helpers.queue_webmention"
    )

    await db.execute(
        "INSERT INTO outgoing_webmentions (source, target, status) VALUES (?, ?, ?)",
        (
            "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
            "http://alice.example.com/post/2",
            WebMentionStatus.SUCCESS,
        ),
    )
    await db.commit()

    data = Microformats2(
        type=["h-entry"],
        properties={
            "in-reply-to": ["http://alice.example.com/post/1"],
            "content": [
                {
                    "html": '<a href="http://example.com/">Robida is cool</a>',
                    "value": "Robida is cool",
                },
            ],
        },
    )
    async with current_app.app_context():
        await send_webmentions(
            "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
            data,
        )

    queue_webmention.assert_has_calls(
        [
            mocker.call(
                mocker.ANY,
                mocker.ANY,
                "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
                "http://example.com/",
                data,
            ),
            mocker.call(
                mocker.ANY,
                mocker.ANY,
                "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
                "http://alice.example.com/post/1",
                data,
            ),
            mocker.call(
                mocker.ANY,
                mocker.ANY,
                "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
                "http://alice.example.com/post/2",
                data,
            ),
        ],
        any_order=True,
    )


@freeze_time("2024-01-01 00:00:00", auto_tick_seconds=3600)
async def test_queue_webmention_happy_path(mocker: MockerFixture) -> None:
    """
    Test the `queue_webmention` function.
    """

    async def gen() -> AsyncGenerator[tuple[WebMentionStatus, str, str | None], None]:
        """
        Simulate webmention processing.
        """
        yield (
            WebMentionStatus.SUCCESS,
            "The webmention was successfully sent.",
            None,
        )

    mocker.patch(
        "robida.blueprints.webmention.helpers.send_webmention",
        return_value=gen(),
    )
    get_db = mocker.patch("robida.blueprints.webmention.helpers.get_db")
    client = mocker.MagicMock()
    mocker.patch(
        "robida.blueprints.webmention.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )

    async with get_db() as db:
        await queue_webmention(
            db,
            client,
            "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
            "http://example.com/",
            Microformats2(
                type=["h-entry"],
                properties={
                    "in-reply-to": ["http://alice.example.com/post/1"],
                    "content": [
                        {
                            "html": '<a href="http://example.com/">Robida is cool</a>',
                            "value": "Robida is cool",
                        },
                    ],
                },
            ),
        )

    db.execute.assert_has_calls(
        [
            mocker.call(
                """
INSERT INTO outgoing_webmentions (
    uuid,
    source,
    target,
    vouch,
    status,
    message,
    content,
    created_at,
    last_modified_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (source, target) DO UPDATE SET
    status = excluded.status,
    message = excluded.message,
    content = excluded.content,
    last_modified_at = excluded.last_modified_at;
            """,
                (
                    "92cdeabd827843ad871d0214dcb2d12e",
                    "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
                    "http://example.com/",
                    None,
                    WebMentionStatus.PROCESSING,
                    "The webmention is being processed.",
                    json.dumps(
                        {
                            "type": ["h-entry"],
                            "properties": {
                                "in-reply-to": ["http://alice.example.com/post/1"],
                                "content": [
                                    {
                                        "html": '<a href="http://example.com/">Robida is cool</a>',
                                        "value": "Robida is cool",
                                    }
                                ],
                            },
                        },
                        separators=(",", ":"),
                    ),
                    datetime(2024, 1, 1, tzinfo=timezone.utc),
                    datetime(2024, 1, 1, tzinfo=timezone.utc),
                ),
            ),
            mocker.call(
                "INSERT OR IGNORE INTO trusted_domains (domain) VALUES (?);",
                ("example.com",),
            ),
            mocker.call(
                """
UPDATE outgoing_webmentions
SET
    status = ?,
    message = ?,
    vouch = ?,
    last_modified_at = ?
WHERE
    uuid = ?;
            """,
                (
                    WebMentionStatus.SUCCESS,
                    "The webmention was successfully sent.",
                    None,
                    datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
                    "92cdeabd827843ad871d0214dcb2d12e",
                ),
            ),
        ]
    )


@freeze_time("2024-01-01 00:00:00", auto_tick_seconds=3600)
async def test_queue_webmention_no_endpoint(mocker: MockerFixture) -> None:
    """
    Test the `queue_webmention` function when there are no endpoints.
    """

    async def gen() -> AsyncGenerator[tuple[WebMentionStatus, str, str | None], None]:
        """
        Simulate webmention processing.
        """
        yield (
            WebMentionStatus.NO_ENDPOINT,
            "The target does not support webmentions.",
            None,
        )

    mocker.patch(
        "robida.blueprints.webmention.helpers.send_webmention",
        return_value=gen(),
    )
    get_db = mocker.patch("robida.blueprints.webmention.helpers.get_db")
    client = mocker.MagicMock()
    mocker.patch(
        "robida.blueprints.webmention.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )

    async with get_db() as db:
        await queue_webmention(
            db,
            client,
            "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
            "http://example.com/",
            Microformats2(
                type=["h-entry"],
                properties={
                    "in-reply-to": ["http://alice.example.com/post/1"],
                    "content": [
                        {
                            "html": '<a href="http://example.com/">Robida is cool</a>',
                            "value": "Robida is cool",
                        },
                    ],
                },
            ),
        )

    db.execute.assert_has_calls(
        [
            mocker.call(
                """
INSERT INTO outgoing_webmentions (
    uuid,
    source,
    target,
    vouch,
    status,
    message,
    content,
    created_at,
    last_modified_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (source, target) DO UPDATE SET
    status = excluded.status,
    message = excluded.message,
    content = excluded.content,
    last_modified_at = excluded.last_modified_at;
            """,
                (
                    "92cdeabd827843ad871d0214dcb2d12e",
                    "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
                    "http://example.com/",
                    None,
                    WebMentionStatus.PROCESSING,
                    "The webmention is being processed.",
                    json.dumps(
                        {
                            "type": ["h-entry"],
                            "properties": {
                                "in-reply-to": ["http://alice.example.com/post/1"],
                                "content": [
                                    {
                                        "html": '<a href="http://example.com/">Robida is cool</a>',
                                        "value": "Robida is cool",
                                    }
                                ],
                            },
                        },
                        separators=(",", ":"),
                    ),
                    datetime(2024, 1, 1, tzinfo=timezone.utc),
                    datetime(2024, 1, 1, tzinfo=timezone.utc),
                ),
            ),
            mocker.call(
                "INSERT OR IGNORE INTO trusted_domains (domain) VALUES (?);",
                ("example.com",),
            ),
            mocker.call(
                """
UPDATE outgoing_webmentions
SET
    status = ?,
    message = ?,
    vouch = ?,
    last_modified_at = ?
WHERE
    uuid = ?;
            """,
                (
                    WebMentionStatus.NO_ENDPOINT,
                    "The target does not support webmentions.",
                    None,
                    datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
                    "92cdeabd827843ad871d0214dcb2d12e",
                ),
            ),
        ]
    )


def test_extract_urls() -> None:
    """
    Test the `extract_urls` function.
    """
    assert extract_urls(Microformats2(type=["h-entry"], properties={})) == set()
    assert extract_urls(
        Microformats2(
            type=["h-entry"],
            properties={
                "url": ["http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534"],
                "in-reply-to": ["http://alice.example.com/post/1"],
                "content": [
                    {
                        "html": '<a href="http://example.com/">Robida is cool</a>',
                        "value": "Robida is cool",
                    },
                ],
            },
        )
    ) == {
        "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
        "http://alice.example.com/post/1",
        "http://example.com/",
    }


async def test_send_webmention_no_endpoint(
    mocker: MockerFixture,
    db: Connection,
) -> None:
    """
    Test the `send_webmention` function when there are no endpoints.
    """
    mocker.patch(
        "robida.blueprints.webmention.helpers.find_endpoint",
        return_value=None,
    )
    client = mocker.MagicMock()

    event_stream = send_webmention(
        db,
        client,
        "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
        "http://example.com/",
        None,
    )
    (status, message, vouch) = await anext(event_stream)
    assert status == WebMentionStatus.NO_ENDPOINT
    assert message == "The target does not support webmentions."
    assert vouch is None

    with pytest.raises(StopAsyncIteration):
        await anext(event_stream)


async def test_send_webmention_200(
    mocker: MockerFixture,
    httpx_mock: HTTPXMock,
    db: Connection,
) -> None:
    """
    Test the `send_webmention` function on a 200 response.
    """
    httpx_mock.add_response(
        url="http://example.com/webmention",
        method="POST",
        status_code=200,
    )
    mocker.patch(
        "robida.blueprints.webmention.helpers.find_endpoint",
        return_value="http://example.com/webmention",
    )

    async with httpx.AsyncClient() as client:
        event_stream = send_webmention(
            db,
            client,
            "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
            "http://example.com/",
            None,
        )
        (status, message, vouch) = await anext(event_stream)
        assert status == WebMentionStatus.SUCCESS
        assert message == "The webmention was successfully sent."
        assert vouch is None

        with pytest.raises(StopAsyncIteration):
            await anext(event_stream)

    request = httpx_mock.get_request(url="http://example.com/webmention")
    assert request.method == "POST"
    assert (
        request.content
        == urllib.parse.urlencode(
            {
                "source": "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
                "target": "http://example.com/",
            }
        ).encode()
    )


async def test_send_webmention_202(
    mocker: MockerFixture,
    httpx_mock: HTTPXMock,
    db: Connection,
) -> None:
    """
    Test the `send_webmention` function on a 202 response.
    """
    httpx_mock.add_response(
        url="http://example.com/webmention",
        method="POST",
        status_code=202,
    )
    mocker.patch(
        "robida.blueprints.webmention.helpers.find_endpoint",
        return_value="http://example.com/webmention",
    )

    async with httpx.AsyncClient() as client:
        event_stream = send_webmention(
            db,
            client,
            "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
            "http://example.com/",
            None,
        )
        (status, message, vouch) = await anext(event_stream)
        assert status == WebMentionStatus.SUCCESS
        assert message == "The webmention was accepted."
        assert vouch is None

        with pytest.raises(StopAsyncIteration):
            await anext(event_stream)

    request = httpx_mock.get_request(url="http://example.com/webmention")
    assert request.method == "POST"
    assert (
        request.content
        == urllib.parse.urlencode(
            {
                "source": "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
                "target": "http://example.com/",
            }
        ).encode()
    )


async def test_send_webmention_201(
    mocker: MockerFixture,
    httpx_mock: HTTPXMock,
    db: Connection,
) -> None:
    """
    Test the `send_webmention` function on a 201 response.
    """
    httpx_mock.add_response(
        url="http://example.com/webmention",
        method="POST",
        status_code=201,
        headers={"Location": "http://example.com/webmention/1"},
    )
    mocker.patch(
        "robida.blueprints.webmention.helpers.find_endpoint",
        return_value="http://example.com/webmention",
    )

    async def gen() -> AsyncGenerator[tuple[WebMentionStatus, str], None]:
        """
        Simulate webmention processing.
        """
        yield (WebMentionStatus.PROCESSING, "The webmention is being processed.")
        yield (WebMentionStatus.SUCCESS, "The webmention was successfully sent.")

    poll_webmention = mocker.patch(
        "robida.blueprints.webmention.helpers.poll_webmention",
        return_value=gen(),
    )

    async with httpx.AsyncClient() as client:
        event_stream = send_webmention(
            db,
            client,
            "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
            "http://example.com/",
            None,
        )

        (status, message, vouch) = await anext(event_stream)
        assert status == WebMentionStatus.PROCESSING
        assert message == "The webmention is being processed."
        assert vouch is None

        (status, message, vouch) = await anext(event_stream)
        assert status == WebMentionStatus.SUCCESS
        assert message == "The webmention was successfully sent."
        assert vouch is None

        with pytest.raises(StopAsyncIteration):
            await anext(event_stream)

    request = httpx_mock.get_request(url="http://example.com/webmention")
    assert request.method == "POST"
    assert (
        request.content
        == urllib.parse.urlencode(
            {
                "source": "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
                "target": "http://example.com/",
            }
        ).encode()
    )

    poll_webmention.assert_called_with(client, "http://example.com/webmention/1")


async def test_send_webmention_449(
    mocker: MockerFixture,
    httpx_mock: HTTPXMock,
    db: Connection,
    current_app: Quart,
) -> None:
    """
    Test the `send_webmention` function on a 449 response.
    """

    def requires_vouch(request: httpx.Request) -> httpx.Response:
        form = urllib.parse.parse_qs(request.content.decode())
        status_code = 449 if "vouch" not in form else 200
        return httpx.Response(status_code=status_code)

    httpx_mock.add_callback(requires_vouch)

    mocker.patch(
        "robida.blueprints.webmention.helpers.find_endpoint",
        return_value="http://example.com/webmention",
    )
    mocker.patch(
        "robida.blueprints.webmention.helpers.find_vouch",
        return_value="http://alice.example.com/post/1",
    )

    async with current_app.app_context():
        async with httpx.AsyncClient() as client:
            event_stream = send_webmention(
                db,
                client,
                "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
                "http://example.com/",
                None,
            )
            (status, message, vouch) = await anext(event_stream)
            assert status == WebMentionStatus.SUCCESS
            assert message == "The webmention was successfully sent."
            assert vouch == "http://alice.example.com/post/1"

        with pytest.raises(StopAsyncIteration):
            await anext(event_stream)


async def test_send_webmention_449_no_vouch(
    mocker: MockerFixture,
    httpx_mock: HTTPXMock,
    db: Connection,
    current_app: Quart,
) -> None:
    """
    Test the `send_webmention` function on a 449 response and no valid vouch.
    """

    def requires_vouch(request: httpx.Request) -> httpx.Response:
        form = urllib.parse.parse_qs(request.content.decode())
        status_code = 449 if "vouch" not in form else 200
        return httpx.Response(status_code=status_code)

    httpx_mock.add_callback(requires_vouch)

    mocker.patch(
        "robida.blueprints.webmention.helpers.find_endpoint",
        return_value="http://example.com/webmention",
    )
    mocker.patch(
        "robida.blueprints.webmention.helpers.find_vouch",
        return_value=None,
    )

    async with current_app.app_context():
        async with httpx.AsyncClient() as client:
            event_stream = send_webmention(
                db,
                client,
                "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
                "http://example.com/",
                None,
            )
            (status, message, vouch) = await anext(event_stream)
            assert status == WebMentionStatus.FAILURE
            assert message == "The webmention failed and no vouch URL was found."
            assert vouch is None

        with pytest.raises(StopAsyncIteration):
            await anext(event_stream)


async def test_send_webmention_400(
    mocker: MockerFixture,
    httpx_mock: HTTPXMock,
    db: Connection,
) -> None:
    """
    Test the `send_webmention` function on a 400 response.
    """
    httpx_mock.add_response(
        url="http://example.com/webmention",
        method="POST",
        status_code=400,
        text="Invalid request",
    )
    mocker.patch(
        "robida.blueprints.webmention.helpers.find_endpoint",
        return_value="http://example.com/webmention",
    )

    async with httpx.AsyncClient() as client:
        event_stream = send_webmention(
            db,
            client,
            "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
            "http://example.com/",
            None,
        )
        (status, message, vouch) = await anext(event_stream)
        assert status == WebMentionStatus.FAILURE
        assert message == "The webmention failed: Invalid request"
        assert vouch is None

        with pytest.raises(StopAsyncIteration):
            await anext(event_stream)

    request = httpx_mock.get_request(url="http://example.com/webmention")
    assert request.method == "POST"
    assert (
        request.content
        == urllib.parse.urlencode(
            {
                "source": "http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534",
                "target": "http://example.com/",
            }
        ).encode()
    )


async def test_poll_webmention(mocker: MockerFixture, httpx_mock: HTTPXMock) -> None:
    """
    Test the `poll_webmention` function.
    """
    httpx_mock.add_response(
        url="http://example.com/webmention/1",
        method="GET",
        status_code=200,
    )
    mocker.patch("robida.blueprints.webmention.helpers.asyncio.sleep")

    async with httpx.AsyncClient() as client:
        event_stream = poll_webmention(client, "http://example.com/webmention/1")

        (status, message) = await anext(event_stream)
        assert status == WebMentionStatus.PROCESSING
        assert message == "The webmention is being processed."

        (status, message) = await anext(event_stream)
        assert status == WebMentionStatus.SUCCESS
        assert message == "The webmention was successfully sent."

        with pytest.raises(StopAsyncIteration):
            await anext(event_stream)


async def test_poll_webmention_retries(
    mocker: MockerFixture,
    httpx_mock: HTTPXMock,
) -> None:
    """
    Test the `poll_webmention` function with retries.
    """

    class RequiresRetries:  # pylint: disable=too-few-public-methods
        """
        Callback that requires retries.
        """

        def __init__(self, needed: int) -> None:
            self.count = 1
            self.needed = needed

        def __call__(self, request: httpx.Request) -> httpx.Response:
            if self.count >= self.needed:
                return httpx.Response(status_code=200)

            self.count += 1
            return httpx.Response(status_code=202)

    httpx_mock.add_callback(RequiresRetries(2))
    mocker.patch("robida.blueprints.webmention.helpers.asyncio.sleep")

    async with httpx.AsyncClient() as client:
        event_stream = poll_webmention(client, "http://example.com/webmention/1")

        (status, message) = await anext(event_stream)
        assert status == WebMentionStatus.PROCESSING
        assert message == "The webmention is being processed."

        (status, message) = await anext(event_stream)
        assert status == WebMentionStatus.SUCCESS
        assert message == "The webmention was successfully sent."

        with pytest.raises(StopAsyncIteration):
            await anext(event_stream)


async def test_poll_webmention_error(
    mocker: MockerFixture, httpx_mock: HTTPXMock
) -> None:
    """
    Test the `poll_webmention` function.
    """
    httpx_mock.add_response(
        url="http://example.com/webmention/1",
        method="GET",
        status_code=400,
    )
    mocker.patch("robida.blueprints.webmention.helpers.asyncio.sleep")

    async with httpx.AsyncClient() as client:
        event_stream = poll_webmention(client, "http://example.com/webmention/1")

        (status, message) = await anext(event_stream)
        assert status == WebMentionStatus.PROCESSING
        assert message == "The webmention is being processed."

        (status, message) = await anext(event_stream)
        assert status == WebMentionStatus.FAILURE
        assert message == "Gave up on checking webmention status after 10 tries."

        with pytest.raises(StopAsyncIteration):
            await anext(event_stream)
