"""
Tests for the WebMention API.
"""

from uuid import UUID

from aiosqlite import Connection
from freezegun import freeze_time
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture
from quart import Quart, testing

from robida.helpers import get_entry, new_hentry, upsert_entry


@freeze_time("2024-01-01 00:00:00")
async def test_receive(
    mocker: MockerFixture,
    db: Connection,
    client: testing.QuartClient,
) -> None:
    """
    Test the WebMention API receive endpoint.
    """
    mocker.patch("robida.blueprints.webmention.api.process_webmention")
    mocker.patch(
        "robida.blueprints.webmention.api.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )

    response = await client.post(
        "/webmention",
        form={
            "source": "http://other.example.com/",
            "target": "http://example.com/",
        },
    )

    assert response.status_code == 201
    assert (
        response.headers["Location"]
        == "http://example.com/webmention/92cdeabd-8278-43ad-871d-0214dcb2d12e"
    )

    async with db.execute(
        "SELECT * FROM incoming_webmentions WHERE uuid = ?;",
        ("92cdeabd827843ad871d0214dcb2d12e",),
    ) as cursor:
        row = await cursor.fetchone()

    assert dict(row) == {
        "uuid": "92cdeabd827843ad871d0214dcb2d12e",
        "source": "http://other.example.com/",
        "target": "http://example.com/",
        "vouch": None,
        "status": "received",
        "message": "The webmention was received and is queued for processing.",
        "content": None,
        "created_at": "2024-01-01 00:00:00+00:00",
        "last_modified_at": "2024-01-01 00:00:00+00:00",
    }


@freeze_time("2024-01-01 00:00:00")
async def test_receive_existing(
    mocker: MockerFixture,
    httpx_mock: HTTPXMock,
    db: Connection,
    current_app: Quart,
    client: testing.QuartClient,
) -> None:
    """
    Test the WebMention API when it receives an update to an existing webmention.
    """
    mocker.patch("robida.blueprints.webmention.api.send_webmentions")
    mocker.patch(
        "robida.blueprints.webmention.helpers.is_domain_trusted",
        return_value=True,
    )

    # UUID for the new webmention (will be replaced by the existing one)
    mocker.patch(
        "robida.blueprints.webmention.api.uuid4",
        return_value=UUID("c35ad471-6c6c-488b-9ffc-8854607192f0"),
    )

    uuid = UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e")
    target = f"http://example.com/feed/{uuid}"
    source = "http://other.example.com/"

    httpx_mock.add_response(
        url=source,
        html=f"""
<div class="h-entry">
    <p class="p-content">
        <a href="{target}">This is SUPER cool</a>
    </p>
</div>
        """,
        headers={"Content-Type": "text/html"},
    )

    # create an entry
    async with current_app.app_context():
        hentry = new_hentry()
        hentry.properties.update(
            {
                "url": [target],
                "uid": [str(uuid)],
                "content": ["This is cool"],
            },
        )
        entry = await upsert_entry(db, hentry)
        assert entry.content.properties["content"][0] == "This is cool"

    # create an existing webmention
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
VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            uuid.hex,
            source,
            target,
            None,
            "received",
            "The webmention was received and is queued for processing.",
            "2024-01-01 00:00:00+00:00",
            "2024-01-01 00:00:00+00:00",
        ),
    )
    await db.commit()

    # Note: if we set an `auto_tick_seconds` value in the `freeze_time` decorator,
    # the background tasks might time out!
    async with current_app.test_app():
        await client.post(
            "/webmention",
            form={"source": source, "target": target},
        )

    # check that the entry was updated
    updated_entry = await get_entry(db, uuid)
    assert (
        updated_entry
        and updated_entry.content.properties["content"][0] == "This is SUPER cool"
    )


@freeze_time("2024-01-01 00:00:00")
async def test_receive_require_vouch(
    mocker: MockerFixture,
    current_app: Quart,
    client: testing.QuartClient,
) -> None:
    """
    Test the WebMention API receive endpoint when a `vouch` is required.
    """
    current_app.config["REQUIRE_VOUCH"] = "true"
    mocker.patch("robida.blueprints.webmention.api.process_webmention")
    mocker.patch(
        "robida.blueprints.webmention.api.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )

    response = await client.post(
        "/webmention",
        form={
            "source": "http://other.example.com/",
            "target": "http://example.com/",
        },
    )

    assert response.status_code == 449

    response = await client.post(
        "/webmention",
        form={
            "source": "http://other.example.com/",
            "target": "http://example.com/",
            "vouch": "http://alice.example.com/post/1",
        },
    )

    assert response.status_code == 201


async def test_receive_invalid(client: testing.QuartClient) -> None:
    """
    Test the WebMention API receive endpoint with an invalid request.
    """
    response = await client.post(
        "/webmention",
        form={
            "source": "gemini://other.example.com/",
            "target": "http://example.com/",
            "vouch": None,
        },
    )

    assert response.status_code == 400


@freeze_time("2024-01-01 00:00:00")
async def test_status(db: Connection, client: testing.QuartClient) -> None:
    """
    Test the WebMention API status endpoint.
    """
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
VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            "92cdeabd827843ad871d0214dcb2d12e",
            "http://other.example.com/",
            "http://example.com/",
            None,
            "received",
            "The webmention was received and is queued for processing.",
            "2024-01-01 00:00:00+00:00",
            "2024-01-01 00:00:00+00:00",
        ),
    )
    await db.commit()

    response = await client.get("/webmention/92cdeabd-8278-43ad-871d-0214dcb2d12e")

    assert response.status_code == 200
    assert await response.json == {
        "last_modified_at": "2024-01-01 00:00:00+00:00",
        "message": "The webmention was received and is queued for processing.",
        "status": "received",
    }

    response = await client.get("/webmention/37c9ed45-5c0c-43e4-b088-0e904ed849d7")

    assert response.status_code == 404
