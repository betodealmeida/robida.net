"""
Tests for the Micropub endpoint.
"""

import json
import urllib.parse
from io import BytesIO
from uuid import UUID

import aiosqlite
from freezegun import freeze_time
from pytest_mock import MockerFixture
from quart import Quart, testing
from quart.datastructures import FileStorage


@freeze_time("2024-01-01 00:00:00")
async def test_create_entry(
    mocker: MockerFixture,
    current_app: Quart,
    client: testing.QuartClient,
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

    async with aiosqlite.connect(current_app.config["DATABASE"]) as db:
        async with db.execute("SELECT * FROM entries") as cursor:
            row = await cursor.fetchone()

    assert row == (
        "92cdeabd-8278-43ad-871d-0214dcb2d12e",
        "http://robida.net/",
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
        0,
        0,
        "2024-01-01 00:00:00+00:00",
        "2024-01-01 00:00:00+00:00",
    )


@freeze_time("2024-01-01 00:00:00")
async def test_create_entry_no_type(
    mocker: MockerFixture,
    current_app: Quart,
    client: testing.QuartClient,
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

    async with aiosqlite.connect(current_app.config["DATABASE"]) as db:
        async with db.execute("SELECT * FROM entries") as cursor:
            row = await cursor.fetchone()

    assert row == (
        "92cdeabd-8278-43ad-871d-0214dcb2d12e",
        "http://robida.net/",
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
        0,
        0,
        "2024-01-01 00:00:00+00:00",
        "2024-01-01 00:00:00+00:00",
    )


@freeze_time("2024-01-01 00:00:00")
async def test_create_entry_from_json(
    mocker: MockerFixture,
    current_app: Quart,
    client: testing.QuartClient,
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

    async with aiosqlite.connect(current_app.config["DATABASE"]) as db:
        async with db.execute("SELECT * FROM entries") as cursor:
            row = await cursor.fetchone()

    assert row == (
        "92cdeabd-8278-43ad-871d-0214dcb2d12e",
        "http://robida.net/",
        json.dumps(
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
        0,
        0,
        "2024-01-01 00:00:00+00:00",
        "2024-01-01 00:00:00+00:00",
    )


@freeze_time("2024-01-01 00:00:00")
async def test_create_entry_from_json_no_type(
    mocker: MockerFixture,
    current_app: Quart,
    client: testing.QuartClient,
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

    async with aiosqlite.connect(current_app.config["DATABASE"]) as db:
        async with db.execute("SELECT * FROM entries") as cursor:
            row = await cursor.fetchone()

    assert row == (
        "92cdeabd-8278-43ad-871d-0214dcb2d12e",
        "http://robida.net/",
        json.dumps(
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
        0,
        0,
        "2024-01-01 00:00:00+00:00",
        "2024-01-01 00:00:00+00:00",
    )


@freeze_time("2024-01-01 00:00:00")
async def test_create_entry_with_file(
    mocker: MockerFixture,
    current_app: Quart,
    client: testing.QuartClient,
) -> None:
    """
    Test main endpoint.
    """
    mocker.patch(
        "robida.blueprints.micropub.api.uuid4",
        side_effect=[
            UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
            UUID("c35ad471-6c6c-488b-9ffc-8854607192f0"),
        ],
    )
    mocker.patch("robida.blueprints.media.api.aiofiles")

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

    async with aiosqlite.connect(current_app.config["DATABASE"]) as db:
        async with db.execute("SELECT * FROM entries") as cursor:
            row = await cursor.fetchone()

    assert row == (
        "c35ad471-6c6c-488b-9ffc-8854607192f0",
        "http://robida.net/",
        json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "content": ["hello world"],
                    "category": ["foo"],
                    "photo": [
                        "http://robida.net/media/92cdeabd-8278-43ad-871d-0214dcb2d12e"
                    ],
                },
            },
            separators=(",", ":"),
        ),
        0,
        0,
        "2024-01-01 00:00:00+00:00",
        "2024-01-01 00:00:00+00:00",
    )


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


async def test_delete_and_undelete(
    current_app: Quart,
    client: testing.QuartClient,
) -> None:
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

    async with aiosqlite.connect(current_app.config["DATABASE"]) as db:
        async with db.execute(
            "SELECT deleted FROM entries WHERE uuid = ?",
            (uuid,),
        ) as cursor:
            row = await cursor.fetchone()

    assert row[0] == 0

    response = await client.post("/micropub/", json={"url": url, "action": "delete"})
    assert response.status_code == 204

    async with aiosqlite.connect(current_app.config["DATABASE"]) as db:
        async with db.execute(
            "SELECT deleted FROM entries WHERE uuid = ?",
            (uuid,),
        ) as cursor:
            row = await cursor.fetchone()

    assert row[0] == 1

    response = await client.post("/micropub/", json={"url": url, "action": "undelete"})
    assert response.status_code == 204

    async with aiosqlite.connect(current_app.config["DATABASE"]) as db:
        async with db.execute(
            "SELECT deleted FROM entries WHERE uuid = ?",
            (uuid,),
        ) as cursor:
            row = await cursor.fetchone()

    assert row[0] == 0


async def test_update(
    current_app: Quart,
    client: testing.QuartClient,
) -> None:
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

    async with aiosqlite.connect(current_app.config["DATABASE"]) as db:
        async with db.execute(
            "SELECT content, last_modified_at FROM entries WHERE uuid = ?",
            (uuid,),
        ) as cursor:
            row = await cursor.fetchone()

    assert row == (
        json.dumps(
            {
                "type": ["h-entry"],
                "properties": {
                    "content": ["hello world, updated"],
                    "category": ["foo", "bar", "baz"],
                },
            },
            separators=(",", ":"),
        ),
        "2024-01-02 00:00:00+00:00",
    )


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
