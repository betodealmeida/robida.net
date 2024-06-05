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

    # h=entry&content=hello+world&category[]=foo&category[]=bar
    response = await client.post(
        "/micropub/",
        form=[
            ("h", "entry"),
            ("content", "hello world"),
            ("category[]", "foo"),
            ("category[]", "bar"),
        ],
    )

    assert response.status_code == 201

    async with db.execute("SELECT * FROM entries") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "uuid": "92cdeabd827843ad871d0214dcb2d12e",
        "author": "http://robida.net/",
        "location": "http://robida.net/entries/92cdeabd827843ad871d0214dcb2d12e",
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {"content": ["hello world"], "category": ["foo", "bar"]},
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

    # h=entry&content=hello+world&category[]=foo&category[]=bar
    response = await client.post(
        "/micropub/",
        form=[
            ("content", "hello world"),
            ("category[]", "foo"),
            ("category[]", "bar"),
        ],
    )

    assert response.status_code == 201

    async with db.execute("SELECT * FROM entries") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "uuid": "92cdeabd827843ad871d0214dcb2d12e",
        "author": "http://robida.net/",
        "location": "http://robida.net/entries/92cdeabd827843ad871d0214dcb2d12e",
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {"content": ["hello world"], "category": ["foo", "bar"]},
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

    # https://www.w3.org/TR/micropub/#json-syntax
    response = await client.post(
        "/micropub/",
        json={
            "type": ["h-entry"],
            "properties": {
                "content": ["hello world"],
                "category": ["foo", "bar"],
                "photo": ["https://photos.example.com/592829482876343254.jpg"],
            },
        },
    )

    assert response.status_code == 201

    async with db.execute("SELECT * FROM entries") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "uuid": "92cdeabd827843ad871d0214dcb2d12e",
        "author": "http://robida.net/",
        "location": "http://robida.net/entries/92cdeabd827843ad871d0214dcb2d12e",
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "content": ["hello world"],
                    "category": ["foo", "bar"],
                    "photo": ["https://photos.example.com/592829482876343254.jpg"],
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

    # https://www.w3.org/TR/micropub/#json-syntax
    response = await client.post(
        "/micropub/",
        json={
            "properties": {
                "content": ["hello world"],
                "category": ["foo", "bar"],
                "photo": ["https://photos.example.com/592829482876343254.jpg"],
            },
        },
    )

    assert response.status_code == 201

    async with db.execute("SELECT * FROM entries") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "uuid": "92cdeabd827843ad871d0214dcb2d12e",
        "author": "http://robida.net/",
        "location": "http://robida.net/entries/92cdeabd827843ad871d0214dcb2d12e",
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "content": ["hello world"],
                    "category": ["foo", "bar"],
                    "photo": ["https://photos.example.com/592829482876343254.jpg"],
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
    mocker.patch("robida.blueprints.micropub.api.aiofiles")

    # h=entry&content=hello+world&category[]=foo&category[]=bar
    response = await client.post(
        "/micropub/",
        form={
            "h": "entry",
            "content": "hello world",
            "category[]": "foo",
        },
        files={"photo": FileStorage(BytesIO(b"bytes"), "photo.jpg")},
    )

    assert response.status_code == 201

    async with db.execute("SELECT * FROM entries") as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "uuid": "c35ad4716c6c488b9ffc8854607192f0",
        "author": "http://robida.net/",
        "location": "http://robida.net/entries/c35ad4716c6c488b9ffc8854607192f0",
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "content": ["hello world"],
                    "category": ["foo"],
                    "photo": [
                        "http://robida.net/media/92cdeabd827843ad871d0214dcb2d12e"
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


async def test_index(client: testing.QuartClient) -> None:
    """
    Test the query endpoint.
    """
    response = await client.get("/micropub/")

    assert response.status_code == 400
    assert await response.json == {
        "error": "invalid_request",
        "error_description": "Missing query",
    }


async def test_index_config(client: testing.QuartClient) -> None:
    """
    Test fetching the configuration.
    """
    response = await client.get("/micropub/", query_string={"q": "config"})

    assert response.status_code == 200
    assert await response.json == {
        "media-endpoint": "http://robida.net/media/",
        "syndicate-to": [],
    }


async def test_index_syndicate_to(client: testing.QuartClient) -> None:
    """
    Test fetching the list of syndication targets.
    """
    response = await client.get("/micropub/", query_string={"q": "syndicate-to"})

    assert response.status_code == 200
    assert await response.json == {"syndicate-to": []}


async def test_index_source(client: testing.QuartClient) -> None:
    """
    Test fetching information about an entry.
    """
    response = await client.post(
        "/micropub/",
        json={
            "type": ["h-entry"],
            "properties": {
                "published": ["2016-02-21T12:50:53-08:00"],
                "content": ["Hello World"],
                "category": ["foo", "bar"],
            },
        },
    )
    url = response.headers["Location"]

    response = await client.get(
        f"/micropub/?q=source&properties[]=published&properties[]=category&url={url}"
    )

    assert response.status_code == 200
    assert await response.json == {
        "properties": {
            "category": ["foo", "bar"],
            "published": ["2016-02-21T12:50:53-08:00"],
        }
    }

    response = await client.get(f"/micropub/?q=source&url={url}")
    assert response.status_code == 200
    assert await response.json == {
        "type": ["h-entry"],
        "properties": {
            "category": ["foo", "bar"],
            "content": ["Hello World"],
            "published": ["2016-02-21T12:50:53-08:00"],
        },
    }


async def test_index_invalid(client: testing.QuartClient) -> None:
    """
    Test the query endpoint.
    """
    response = await client.get("/micropub/", query_string={"q": "invalid"})

    assert response.status_code == 400
    assert await response.json == {
        "error": "invalid_request",
        "error_description": "Unknown query: invalid",
    }


async def test_delete_and_undelete(client: testing.QuartClient, db: Connection) -> None:
    """
    Test deleting and undeleting an entry.
    """
    response = await client.post(
        "/micropub/",
        json={
            "properties": {
                "content": ["hello world"],
                "category": ["foo", "bar"],
                "photo": ["https://photos.example.com/592829482876343254.jpg"],
            },
        },
    )
    url = response.headers["Location"]
    uuid = urllib.parse.urlparse(url).path.split("/")[-1]

    async with db.execute(
        "SELECT deleted FROM entries WHERE uuid = ?",
        (uuid,),
    ) as cursor:
        row = await cursor.fetchone()

    assert row[0] == 0

    response = await client.post("/micropub/", json={"url": url, "action": "delete"})
    assert response.status_code == 204

    async with db.execute(
        "SELECT deleted FROM entries WHERE uuid = ?",
        (uuid,),
    ) as cursor:
        row = await cursor.fetchone()

    assert row[0] == 1

    response = await client.post("/micropub/", json={"url": url, "action": "undelete"})
    assert response.status_code == 204

    async with db.execute(
        "SELECT deleted FROM entries WHERE uuid = ?",
        (uuid,),
    ) as cursor:
        row = await cursor.fetchone()

    assert row[0] == 0


async def test_update(client: testing.QuartClient, db: Connection) -> None:
    """
    Test updating an entry.
    """
    with freeze_time("2024-01-01 00:00:00"):
        response = await client.post(
            "/micropub/",
            json={
                "properties": {
                    "content": ["hello world"],
                    "category": ["foo", "bar"],
                    "photo": ["https://photos.example.com/592829482876343254.jpg"],
                },
            },
        )
    url = response.headers["Location"]
    uuid = urllib.parse.urlparse(url).path.split("/")[-1]

    with freeze_time("2024-01-02 00:00:00"):
        response = await client.post(
            "/micropub/",
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
        )
    assert response.status_code == 204

    async with db.execute(
        "SELECT content, last_modified_at FROM entries WHERE uuid = ?",
        (uuid,),
    ) as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "content": json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "content": ["hello world, updated"],
                    "category": ["foo", "bar", "baz"],
                },
            },
            separators=(",", ":"),
        ),
        "last_modified_at": "2024-01-02 00:00:00+00:00",
    }


async def test_invalid_action(client: testing.QuartClient) -> None:
    """
    Test error response when user passes an invalid action.
    """
    response = await client.post("/micropub/", json={"action": "invalid"})

    assert response.status_code == 400
    assert await response.json == {
        "error": "invalid_request",
        "error_description": "Invalid action: invalid",
    }
