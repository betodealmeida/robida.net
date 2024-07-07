"""
CRUD blueprint.
"""

from uuid import UUID

from quart import Blueprint, Response, current_app, render_template, request
from quart.helpers import redirect, url_for
from quart_schema import validate_querystring

from robida.blueprints.auth.helpers import protected
from robida.db import get_db
from robida.helpers import delete_entry, get_entry, upsert_entry

from .helpers import create_hentry, update_hentry
from .models import TemplateRequest

blueprint = Blueprint("crud", __name__, url_prefix="/crud")


@blueprint.route("", methods=["GET"])
@protected
async def new() -> Response:
    """
    Serve the "new entry" page.
    """
    return await render_template("crud/new.html")


@blueprint.route("", methods=["POST"])
@protected
async def submit() -> Response:
    """
    Process the new entry form.
    """
    payload = await request.form
    data = {key: value for key, value in payload.items() if value.strip() != ""}
    uuid = UUID(data.pop("uuid")) if "uuid" in data else None

    async with get_db(current_app) as db:
        if uuid:
            entry = await get_entry(db, uuid)
            if entry is None:
                return Response(status=404)
            hentry = await update_hentry(entry.content, data)
        else:
            hentry = await create_hentry(data)

        entry = await upsert_entry(db, hentry)

    return redirect(url_for("feed.entry", uuid=entry.uuid))


@blueprint.route("/<uuid:uuid>", methods=["GET"])
@protected
async def edit(uuid: UUID) -> Response:
    """
    Edit an entry.
    """
    async with get_db(current_app) as db:
        if entry := await get_entry(db, uuid):
            return await render_template("crud/edit.html", data=entry.content)

    return Response(status=404)


@blueprint.route("/<uuid:uuid>", methods=["DELETE"])
@protected
async def delete(uuid: UUID) -> Response:
    """
    Delete an entry.
    """
    async with get_db(current_app) as db:
        if entry := await get_entry(db, uuid):
            await delete_entry(db, entry)

            # WTF can't return 204 to htmx otherwise it won't animate
            return Response(status=200)

    return Response(status=404)


@blueprint.route("/template", methods=["GET"])
@validate_querystring(TemplateRequest)
async def template(query_args: TemplateRequest) -> Response:
    """
    Serve the entry template.
    """
    return await render_template(f"crud/{query_args.template}.html")
