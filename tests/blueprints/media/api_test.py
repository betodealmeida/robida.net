"""
Tests for the Media Endpoint.
"""

from io import BytesIO
from uuid import UUID

from pytest_mock import MockerFixture
from quart import Response, testing
from quart.datastructures import FileStorage
from werkzeug.datastructures import Authorization


async def test_media_upload(mocker: MockerFixture, client: testing.QuartClient) -> None:
    """
    Test media upload.
    """
    mocker.patch(
        "robida.blueprints.media.api.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    mocker.patch("robida.blueprints.media.api.aiofiles")

    response = await client.post(
        "/media/",
        files={"file": FileStorage(BytesIO(b"bytes"), "photo.jpg")},
        auth=Authorization("bearer", token="media"),
    )

    assert response.status_code == 201
    assert (
        response.headers["Location"]
        == "http://robida.net/media/92cdeabd827843ad871d0214dcb2d12e"
    )


async def test_media_upload_error(client: testing.QuartClient) -> None:
    """
    Test media upload error response.
    """
    response = await client.post(
        "/media/",
        files={"image": FileStorage(BytesIO(b"bytes"), "photo.jpg")},
        auth=Authorization("bearer", token="media"),
    )

    assert response.status_code == 400
    assert await response.json == {
        "error": "invalid_request",
        "error_description": "Part name `file` not found in multipart/form-data request.",
    }


async def test_media_download(
    mocker: MockerFixture,
    client: testing.QuartClient,
) -> None:
    """
    Test media download.
    """
    mocker.patch(
        "robida.blueprints.media.api.send_from_directory",
        return_value=Response(b"bytes", content_type="image/gif"),
    )
    mocker.patch(
        "robida.blueprints.media.api.puremagic.from_file",
        return_value=[
            [".gif", "image/gif", "Graphics interchange format file (GIF87a)", 0.7]
        ],
    )

    response = await client.get("/media/92cdeabd-8278-43ad-871d-0214dcb2d12e")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/gif"
    assert await response.get_data() == b"bytes"
