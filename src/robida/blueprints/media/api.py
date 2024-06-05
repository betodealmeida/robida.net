"""
Media Endpoint blueprint.

https://indieweb.org/Micropub
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import aiofiles
import puremagic
from quart import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    request,
)
from quart.helpers import make_response, safe_join, send_from_directory, url_for

from robida.blueprints.micropub.api import ErrorType

blueprint = Blueprint("media", __name__, url_prefix="/media")


@blueprint.route("/", methods=["POST"])
async def upload() -> Response:
    """
    Upload a file to the Media Endpoint.
    """
    files = await request.files
    if "file" not in files:
        return (
            jsonify(
                {
                    "error": ErrorType.INVALID_REQUEST,
                    "error_description": (
                        "Part name `file` not found in multipart/form-data request."
                    ),
                },
            ),
            400,
        )

    uuid = uuid4()
    file_path = Path(current_app.config["MEDIA"]) / uuid.hex
    file = files["file"]

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file.read())

    response = await make_response("")
    response.status_code = 201
    response.headers["Location"] = url_for(
        "media.download",
        filename=uuid.hex,
        _external=True,
    )

    return response


@blueprint.route("/<filename>", methods=["GET"])
async def download(filename) -> Response:
    """
    Serve a file from the Media Endpoint.
    """
    mimetype = puremagic.from_file(safe_join(current_app.config["MEDIA"], filename))[0][
        1
    ]

    return await send_from_directory(
        current_app.config["MEDIA"],
        filename,
        mimetype=mimetype,
        conditional=True,
    )
