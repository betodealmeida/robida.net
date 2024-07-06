"""
WebMention endpoints.

https://www.w3.org/TR/webmention/
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from quart import Blueprint, Response, current_app, jsonify
from quart.helpers import url_for
from quart_schema import DataSource, validate_request

from robida.db import get_db
from robida.events import EntryCreated, EntryDeleted, EntryUpdated, dispatcher

from .helpers import process_webmention, send_webmentions, verify_request
from .models import WebMentionRequest, WebMentionStatus

blueprint = Blueprint("webmention", __name__, url_prefix="/webmention")


@dispatcher.register(EntryCreated)
async def entry_created(event: EntryCreated) -> None:
    """
    Handle an entry being created.
    """
    await send_webmentions(new_entry=event.new_entry)


@dispatcher.register(EntryUpdated)
async def entry_updated(event: EntryUpdated) -> None:
    """
    Handle an entry being updated.
    """
    await send_webmentions(new_entry=event.new_entry, old_entry=event.old_entry)


@dispatcher.register(EntryDeleted)
async def entry_deleted(event: EntryDeleted) -> None:
    """
    Handle an entry being deleted.
    """
    await send_webmentions(old_entry=event.old_entry)


@blueprint.route("", methods=["POST"])
@validate_request(WebMentionRequest, source=DataSource.FORM)
async def receive(data: WebMentionRequest) -> Response:
    """
    Receive a webmention.

    https://www.w3.org/TR/webmention/#receiving-webmentions
    """
    try:
        verify_request(data.source, data.target)
    except ValueError as ex:
        response = jsonify(
            {
                "status": WebMentionStatus.FAILURE,
                "message": str(ex),
            },
        )
        response.status_code = 400
        return response

    if current_app.config["REQUIRE_VOUCH"].lower() == "true" and data.vouch is None:
        response = jsonify(
            {
                "status": WebMentionStatus.FAILURE,
                "message": "The webmention does not contain a `vouch` field.",
            },
        )
        response.status_code = 449
        return response

    uuid = uuid4()
    created_at = last_modified_at = datetime.now(timezone.utc)

    async with get_db(current_app) as db:
        async with db.execute(
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
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (source, target) DO UPDATE SET
    vouch = excluded.vouch,
    status = excluded.status,
    message = excluded.message,
    last_modified_at = excluded.last_modified_at
RETURNING uuid;
            """,
            (
                uuid.hex,
                data.source,
                data.target,
                data.vouch,
                WebMentionStatus.RECEIVED,
                "The webmention was received and is queued for processing.",
                created_at,
                last_modified_at,
            ),
        ) as cursor:
            row = await cursor.fetchone()
        await db.commit()

    current_app.add_background_task(
        process_webmention,
        UUID(row["uuid"]),
        data.source,
        data.target,
        data.vouch,
    )

    return Response(
        status=201,
        headers={
            "Location": url_for("webmention.status", uuid=str(uuid), _external=True)
        },
    )


@blueprint.route("/<uuid:uuid>", methods=["GET"])
async def status(uuid: UUID) -> Response:
    """
    Check the status of a webmention.

    https://www.w3.org/TR/webmention/#checking-the-status-of-a-webmention
    """
    async with get_db(current_app) as db:
        async with db.execute(
            """
SELECT
    status,
    message,
    last_modified_at
FROM
    incoming_webmentions
WHERE
    uuid = ?
            """,
            (uuid.hex,),
        ) as cursor:
            row = await cursor.fetchone()

    if row is None:
        return Response(status=404)

    return jsonify(
        {
            "status": row["status"],
            "message": row["message"],
            "last_modified_at": row["last_modified_at"],
        }
    )
