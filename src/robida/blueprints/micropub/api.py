"""
Micropub blueprint.

https://indieweb.org/Micropub
"""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import aiofiles
from quart import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    request,
)
from quart.helpers import url_for
from werkzeug.datastructures import MultiDict

from robida.blueprints.indieauth.helpers import requires_scope
from robida.db import get_db
from robida.helpers import (
    delete_entry,
    get_entry,
    get_hcard,
    undelete_entry,
    upsert_entry,
)
from robida.models import Microformats2

from .helpers import process_form
from .models import ActionType, ErrorType

blueprint = Blueprint("micropub", __name__, url_prefix="/micropub")


@blueprint.route("", methods=["GET"])
async def index() -> Response:
    """
    Query the Micropub endpoint.
    """
    q = request.args.get("q")

    if q == "config":
        return jsonify(
            {
                "media-endpoint": url_for("media.upload", _external=True),
                "syndicate-to": [],
            }
        )

    if q == "syndicate-to":
        return jsonify({"syndicate-to": []})

    if q == "source":
        url = request.args.get("url")
        uuid = UUID(urllib.parse.urlparse(url).path.split("/")[-1])

        async with get_db(current_app) as db:
            async with db.execute(
                """
SELECT
    content
FROM
    entries
WHERE
    uuid = ?
            """,
                (uuid.hex,),
            ) as cursor:
                row = await cursor.fetchone()

        data = Microformats2.model_validate_json(row["content"])

        properties = request.args.getlist("properties[]")
        if not properties:
            return jsonify(data.model_dump(exclude_unset=True))

        return jsonify(
            {
                "properties": {
                    key: value
                    for key, value in data.properties.items()
                    if key in properties
                },
            }
        )

    description = f"Unknown query: {q}" if q else "Missing query"
    return (
        jsonify(
            {
                "error": ErrorType.INVALID_REQUEST,
                "error_description": description,
            },
        ),
        400,
    )


@blueprint.route("", methods=["POST"])
async def post() -> Response:
    """
    Dispatcher for creating, updating, deleting, and undeleting Micropub entries.
    """
    actions = {
        ActionType.UPDATE: update,
        ActionType.DELETE: delete,
        ActionType.UNDELETE: undelete,
    }

    if request.content_type == "application/json":
        payload = await request.json
    else:
        payload = await request.form

    if action := payload.get("action"):
        if action not in actions:
            return (
                jsonify(
                    {
                        "error": ErrorType.INVALID_REQUEST,
                        "error_description": f"Invalid action: {action}",
                    },
                ),
                400,
            )

        return await actions[action](payload)

    # set detault type for new entry
    if request.content_type == "application/json":
        payload.setdefault("type", ["h-entry"])
        data = Microformats2(**payload)
    else:
        payload = MultiDict(payload)
        payload.setdefault("h", "entry")
        data = process_form(payload)

    files = await request.files
    for name, file in files.items():
        uuid = uuid4()
        file_path = Path(current_app.config["MEDIA"]) / str(uuid)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file.read())

        data.properties[name] = [
            url_for(
                "media.download",
                filename=str(uuid),
                _external=True,
            )
        ]

    return await create(data)


@requires_scope("create")
async def create(hentry: Microformats2) -> Response:
    """
    Create a new Micropub entry.
    """
    uuid = uuid4()
    created_at = last_modified_at = datetime.now(timezone.utc)
    url = url_for("feed.entry", uuid=str(uuid), _external=True)
    hcard = get_hcard()

    hentry.properties.setdefault("author", [hcard.model_dump()])
    hentry.properties.setdefault("published", [created_at.isoformat()])
    hentry.properties.setdefault("updated", [last_modified_at.isoformat()])
    hentry.properties.setdefault("url", [url])
    hentry.properties.setdefault("uid", [str(uuid)])

    async with get_db(current_app) as db:
        await upsert_entry(db, hentry)

    return Response(status=201, headers={"Location": url})


@requires_scope("update")
async def update(payload) -> Response:
    """
    Update a Micropub entry.
    """
    url = payload["url"]
    uuid = UUID(urllib.parse.urlparse(url).path.split("/")[-1])

    async with get_db(current_app) as db:
        entry = await get_entry(db, uuid)

        if entry is None:
            return Response(status=404)

        data = entry.content

        data.properties["updated"] = [datetime.now(timezone.utc).isoformat()]

        if "replace" in payload:
            for key, value in payload["replace"].items():
                data.properties[key] = value

        if "add" in payload:
            for key, value in payload["add"].items():
                data.properties.setdefault(key, [])
                data.properties[key].extend(value)

        if "delete" in payload:
            for key, value in payload["delete"].items():
                data.properties[key] = [
                    item for item in data.properties[key] if item not in set(value)
                ]
                if not data.properties[key]:
                    del data.properties[key]

        await upsert_entry(db, data)

    return Response(
        status=204,
        headers={"Location": url_for("feed.entry", uuid=str(uuid), _external=True)},
    )


@requires_scope("delete")
async def delete(payload) -> Response:
    """
    Delete a Micropub entry.
    """
    url = payload["url"]
    uuid = UUID(urllib.parse.urlparse(url).path.split("/")[-1])

    async with get_db(current_app) as db:
        entry = await get_entry(db, uuid)
        if entry is None:
            return Response(status=404)

        await delete_entry(db, entry)

    return Response(status=204)


@requires_scope("undelete")
async def undelete(payload) -> Response:
    """
    Undelete a Micropub entry.
    """
    url = payload["url"]
    uuid = UUID(urllib.parse.urlparse(url).path.split("/")[-1])

    async with get_db(current_app) as db:
        entry = await get_entry(db, uuid)
        if entry is None:
            return Response(status=404)

        await undelete_entry(db, entry)

    return Response(status=204)
