"""
Tests for the Micropub endpoint.
"""

import json
import urllib.parse
from io import BytesIO
from uuid import UUID

from aiosqlite.core import Connection
from freezegun import freeze_time
from pytest_mock import MockerFixture
from quart import testing
from quart.datastructures import FileStorage
from werkzeug.datastructures import Authorization


@freeze_time("2024-01-01 00:00:00")
async def test_create_entry(
    mocker: MockerFixture,
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test main endpoint.
    """
    mocker.patch(
        "robida.blueprints.micropub.api.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    mocker.patch("robida.helpers.dispatcher")

    # h=entry&content=hello+world&category[]=foo&category[]=bar
    response = await client.post(
        "/micropub",
        form=[
            ("h", "entry"),
            ("content", "hello world"),
            ("category[]", "foo"),
            ("category[]", "bar"),
        ],
        auth=Authorization("bearer", token="create"),
    )

    assert response.status_code == 201

    async with db.execute("SELECT * FROM entries") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "uuid": "92cdeabd827843ad871d0214dcb2d12e",
        "published": 1,
        "visibility": "public",
        "sensitive": 0,
        "author": "http://example.com/",
        "location": "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "content": ["hello world"],
                    "category": ["foo", "bar"],
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
                    "url": [
                        "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                    ],
                    "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                },
            },
            separators=(",", ":"),
        ),
        "read": 0,
        "deleted": 0,
        "created_at": "2024-01-01 00:00:00+00:00",
        "last_modified_at": "2024-01-01 00:00:00+00:00",
    }


@freeze_time("2024-01-01 00:00:00")
async def test_create_entry_no_type(
    mocker: MockerFixture,
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test main endpoint with a multipart/form-data payload without the type specified.
    """
    mocker.patch(
        "robida.blueprints.micropub.api.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    mocker.patch("robida.helpers.dispatcher")

    # h=entry&content=hello+world&category[]=foo&category[]=bar
    response = await client.post(
        "/micropub",
        form=[
            ("content", "hello world"),
            ("category[]", "foo"),
            ("category[]", "bar"),
        ],
        auth=Authorization("bearer", token="create"),
    )

    assert response.status_code == 201

    async with db.execute("SELECT * FROM entries") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "uuid": "92cdeabd827843ad871d0214dcb2d12e",
        "published": 1,
        "visibility": "public",
        "sensitive": 0,
        "author": "http://example.com/",
        "location": "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "content": ["hello world"],
                    "category": ["foo", "bar"],
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
                    "url": [
                        "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                    ],
                    "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                },
            },
            separators=(",", ":"),
        ),
        "read": 0,
        "deleted": 0,
        "created_at": "2024-01-01 00:00:00+00:00",
        "last_modified_at": "2024-01-01 00:00:00+00:00",
    }


@freeze_time("2024-01-01 00:00:00")
async def test_create_entry_from_json(
    mocker: MockerFixture,
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test main endpoint with a JSON request payload.
    """
    mocker.patch(
        "robida.blueprints.micropub.api.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    mocker.patch("robida.helpers.dispatcher")

    # https://www.w3.org/TR/micropub/#json-syntax
    response = await client.post(
        "/micropub",
        json={
            "type": ["h-entry"],
            "properties": {
                "content": ["hello world"],
                "category": ["foo", "bar"],
                "photo": ["https://photos.example.com/592829482876343254.jpg"],
            },
        },
        auth=Authorization("bearer", token="create"),
    )

    assert response.status_code == 201

    async with db.execute("SELECT * FROM entries") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "uuid": "92cdeabd827843ad871d0214dcb2d12e",
        "published": 1,
        "visibility": "public",
        "sensitive": 0,
        "author": "http://example.com/",
        "location": "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "content": ["hello world"],
                    "category": ["foo", "bar"],
                    "photo": ["https://photos.example.com/592829482876343254.jpg"],
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
                    "url": [
                        "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                    ],
                    "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                },
            },
            separators=(",", ":"),
        ),
        "read": 0,
        "deleted": 0,
        "created_at": "2024-01-01 00:00:00+00:00",
        "last_modified_at": "2024-01-01 00:00:00+00:00",
    }


@freeze_time("2024-01-01 00:00:00")
async def test_create_entry_from_json_no_type(
    mocker: MockerFixture,
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test main endpoint with a JSON request payload without the type specified.
    """
    mocker.patch(
        "robida.blueprints.micropub.api.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    mocker.patch("robida.helpers.dispatcher")

    # https://www.w3.org/TR/micropub/#json-syntax
    response = await client.post(
        "/micropub",
        json={
            "properties": {
                "content": ["hello world"],
                "category": ["foo", "bar"],
                "photo": ["https://photos.example.com/592829482876343254.jpg"],
                "author": [
                    {
                        "type": ["h-card"],
                        "properties": {
                            "url": ["http://example.com/"],
                        },
                    },
                ],
                "published": ["2024-01-01T00:00:00Z"],
                "updated": ["2024-01-01T00:00:00Z"],
            },
        },
        auth=Authorization("bearer", token="create"),
    )

    assert response.status_code == 201

    async with db.execute("SELECT * FROM entries") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "uuid": "92cdeabd827843ad871d0214dcb2d12e",
        "published": 1,
        "visibility": "public",
        "sensitive": 0,
        "author": "http://example.com/",
        "location": "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e",
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "content": ["hello world"],
                    "category": ["foo", "bar"],
                    "photo": ["https://photos.example.com/592829482876343254.jpg"],
                    "author": [
                        {
                            "type": ["h-card"],
                            "properties": {"url": ["http://example.com/"]},
                        }
                    ],
                    "published": ["2024-01-01T00:00:00Z"],
                    "updated": ["2024-01-01T00:00:00Z"],
                    "url": [
                        "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                    ],
                    "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                },
            },
            separators=(",", ":"),
        ),
        "read": 0,
        "deleted": 0,
        "created_at": "2024-01-01 00:00:00+00:00",
        "last_modified_at": "2024-01-01 00:00:00+00:00",
    }


@freeze_time("2024-01-01 00:00:00")
async def test_create_entry_with_file(
    mocker: MockerFixture,
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test uploading file directly.
    """
    mocker.patch(
        "robida.blueprints.micropub.api.uuid4",
        side_effect=[
            UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            UUID("c35ad471-6c6c-488b-9ffc-8854607192f0"),
        ],
    )
    mocker.patch("robida.helpers.dispatcher")
    mocker.patch("robida.blueprints.micropub.api.aiofiles")

    # h=entry&content=hello+world&category[]=foo&category[]=bar
    response = await client.post(
        "/micropub",
        form={
            "h": "entry",
            "content": "hello world",
            "category[]": "foo",
        },
        files={"photo": FileStorage(BytesIO(b"bytes"), "photo.jpg")},
        auth=Authorization("bearer", token="create"),
    )

    assert response.status_code == 201

    async with db.execute("SELECT * FROM entries") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "uuid": "c35ad4716c6c488b9ffc8854607192f0",
        "published": 1,
        "visibility": "public",
        "sensitive": 0,
        "author": "http://example.com/",
        "location": "http://example.com/feed/c35ad471-6c6c-488b-9ffc-8854607192f0",
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "content": ["hello world"],
                    "category": ["foo"],
                    "photo": [
                        "http://example.com/media/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                    ],
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
                    "url": [
                        "http://example.com/feed/c35ad471-6c6c-488b-9ffc-8854607192f0"
                    ],
                    "uid": ["c35ad471-6c6c-488b-9ffc-8854607192f0"],
                },
            },
            separators=(",", ":"),
        ),
        "read": 0,
        "deleted": 0,
        "created_at": "2024-01-01 00:00:00+00:00",
        "last_modified_at": "2024-01-01 00:00:00+00:00",
    }


async def test_index(client: testing.QuartClient) -> None:
    """
    Test the query endpoint.
    """
    response = await client.get("/micropub")

    assert response.status_code == 400
    assert await response.json == {
        "error": "invalid_request",
        "error_description": "Missing query",
    }


async def test_index_config(client: testing.QuartClient) -> None:
    """
    Test fetching the configuration.
    """
    response = await client.get("/micropub", query_string={"q": "config"})

    assert response.status_code == 200
    assert await response.json == {
        "media-endpoint": "http://example.com/media",
        "syndicate-to": [],
    }


async def test_index_syndicate_to(client: testing.QuartClient) -> None:
    """
    Test fetching the list of syndication targets.
    """
    response = await client.get("/micropub", query_string={"q": "syndicate-to"})

    assert response.status_code == 200
    assert await response.json == {"syndicate-to": []}


@freeze_time("2024-01-01 00:00:00")
async def test_index_source(mocker: MockerFixture, client: testing.QuartClient) -> None:
    """
    Test fetching information about an entry.
    """
    mocker.patch(
        "robida.blueprints.micropub.api.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    mocker.patch("robida.helpers.dispatcher")

    response = await client.post(
        "/micropub",
        json={
            "type": ["h-entry"],
            "properties": {
                "published": ["2016-02-21T12:50:53-08:00"],
                "content": ["Hello World"],
                "category": ["foo", "bar"],
                "author": [
                    {
                        "type": ["h-card"],
                        "properties": {
                            "url": ["http://example.com/"],
                        },
                    }
                ],
            },
        },
        auth=Authorization("bearer", token="create"),
    )
    url = response.headers["Location"]

    response = await client.get(
        f"/micropub?q=source&properties[]=published&properties[]=category&url={url}"
    )

    assert response.status_code == 200
    assert await response.json == {
        "properties": {
            "category": ["foo", "bar"],
            "published": ["2016-02-21T12:50:53-08:00"],
        }
    }

    response = await client.get("/micropub", query_string={"q": "source", "url": url})
    assert response.status_code == 200
    assert await response.json == {
        "properties": {
            "author": [
                {"properties": {"url": ["http://example.com/"]}, "type": ["h-card"]}
            ],
            "category": ["foo", "bar"],
            "content": ["Hello World"],
            "published": ["2016-02-21T12:50:53-08:00"],
            "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
            "updated": ["2024-01-01T00:00:00+00:00"],
            "url": ["http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"],
        },
        "type": ["h-entry"],
    }


async def test_index_invalid(client: testing.QuartClient) -> None:
    """
    Test the query endpoint.
    """
    response = await client.get("/micropub", query_string={"q": "invalid"})

    assert response.status_code == 400
    assert await response.json == {
        "error": "invalid_request",
        "error_description": "Unknown query: invalid",
    }


async def test_delete_and_undelete(
    mocker: MockerFixture,
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test deleting and undeleting an entry.
    """
    mocker.patch("robida.helpers.dispatcher")

    response = await client.post(
        "/micropub",
        json={
            "properties": {
                "content": ["hello world"],
                "category": ["foo", "bar"],
                "photo": ["https://photos.example.com/592829482876343254.jpg"],
            },
        },
        auth=Authorization("bearer", token="create"),
    )
    url = response.headers["Location"]
    uuid = UUID(urllib.parse.urlparse(url).path.split("/")[-1])

    async with db.execute(
        """
SELECT
    deleted
FROM
    entries
WHERE
    uuid = ?
        """,
        (uuid.hex,),
    ) as cursor:
        row = await cursor.fetchone()

    assert row[0] == 0

    response = await client.post(
        "/micropub",
        json={"url": url, "action": "delete"},
        auth=Authorization("bearer", token="delete"),
    )
    assert response.status_code == 204

    async with db.execute(
        """
SELECT
    deleted
FROM
    entries
WHERE
    uuid = ?
        """,
        (uuid.hex,),
    ) as cursor:
        row = await cursor.fetchone()

    assert row[0] == 1

    response = await client.post(
        "/micropub",
        json={"url": url, "action": "undelete"},
        auth=Authorization("bearer", token="undelete"),
    )
    assert response.status_code == 204

    async with db.execute(
        """
SELECT
    deleted
FROM
    entries
WHERE
    uuid = ?
        """,
        (uuid.hex,),
    ) as cursor:
        row = await cursor.fetchone()

    assert row[0] == 0


async def test_delete_not_found(client: testing.QuartClient) -> None:
    """
    Test deleting an entry that doesn't exist.
    """
    response = await client.post(
        "/micropub",
        json={
            "url": "http://example.com/feed/96135d01-f6be-4e1c-99d0-cc5a6a4f1d10",
            "action": "delete",
        },
        auth=Authorization("bearer", token="delete"),
    )

    assert response.status_code == 404


async def test_undelete_not_found(client: testing.QuartClient) -> None:
    """
    Test undeleting an entry that doesn't exist.
    """
    response = await client.post(
        "/micropub",
        json={
            "url": "http://example.com/feed/96135d01-f6be-4e1c-99d0-cc5a6a4f1d10",
            "action": "undelete",
        },
        auth=Authorization("bearer", token="undelete"),
    )

    assert response.status_code == 404


async def test_update(
    mocker: MockerFixture,
    client: testing.QuartClient,
    db: Connection,
) -> None:
    """
    Test updating an entry.
    """
    mocker.patch(
        "robida.blueprints.micropub.api.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    mocker.patch("robida.helpers.dispatcher")

    with freeze_time("2024-01-01 00:00:00"):
        response = await client.post(
            "/micropub",
            json={
                "properties": {
                    "content": ["hello world"],
                    "category": ["foo", "bar"],
                    "photo": ["https://photos.example.com/592829482876343254.jpg"],
                },
            },
            auth=Authorization("bearer", token="create"),
        )
    url = response.headers["Location"]
    uuid = UUID(urllib.parse.urlparse(url).path.split("/")[-1])

    with freeze_time("2024-01-02 00:00:00"):
        response = await client.post(
            "/micropub",
            json={
                "action": "update",
                "url": url,
                "replace": {
                    "content": ["hello world, updated"],
                },
                "add": {
                    "category": ["baz"],
                },
                "delete": {
                    "photo": ["https://photos.example.com/592829482876343254.jpg"],
                },
            },
            auth=Authorization("bearer", token="update"),
        )
    assert response.status_code == 204

    async with db.execute(
        """
SELECT
    content,
    last_modified_at
FROM
    entries
WHERE
    uuid = ?
        """,
        (uuid.hex,),
    ) as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "content": ["hello world, updated"],
                    "category": ["foo", "bar", "baz"],
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
                    "updated": ["2024-01-02T00:00:00+00:00"],
                    "url": [
                        "http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                    ],
                    "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                },
            },
            separators=(",", ":"),
        ),
        "last_modified_at": "2024-01-02 00:00:00+00:00",
    }


async def test_update_not_found(client: testing.QuartClient) -> None:
    """
    Test updating an entry that doesn't exist.
    """
    with freeze_time("2024-01-02 00:00:00"):
        response = await client.post(
            "/micropub",
            json={
                "action": "update",
                "url": "http://example.com/entry/92cdeabd-8278-43ad-871d-0214dcb2d12e",
                "replace": {
                    "content": ["hello world, updated"],
                },
                "add": {
                    "category": ["baz"],
                },
                "delete": {
                    "photo": ["https://photos.example.com/592829482876343254.jpg"],
                },
            },
            auth=Authorization("bearer", token="update"),
        )

    assert response.status_code == 404


async def test_invalid_action(client: testing.QuartClient) -> None:
    """
    Test error response when user passes an invalid action.
    """
    response = await client.post("/micropub", json={"action": "invalid"})

    assert response.status_code == 400
    assert await response.json == {
        "error": "invalid_request",
        "error_description": "Invalid action: invalid",
    }
