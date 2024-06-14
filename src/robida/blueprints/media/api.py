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
from quart.helpers import safe_join, send_from_directory, url_for

from robida.blueprints.indieauth.helpers import requires_scope
from robida.blueprints.micropub.api import ErrorType

blueprint = Blueprint("media", __name__, url_prefix="/media")


@blueprint.route("", methods=["POST"])
@requires_scope("media")
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
    file_path = Path(current_app.config["MEDIA"]) / str(uuid)
    file = files["file"]

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file.read())

    return Response(
        status=201,
        headers={
            "Location": url_for("media.download", filename=str(uuid), _external=True),
        },
    )


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
