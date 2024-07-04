"""
CRUD blueprint.
"""

from quart import Blueprint, Response, current_app, render_template, request
from quart.helpers import redirect, url_for
from quart_schema import validate_querystring

from robida.blueprints.auth.helpers import protected
from robida.db import get_db
from robida.helpers import upsert_entry

from .helpers import create_hentry
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
    hentry = await create_hentry(data)
    async with get_db(current_app) as db:
        entry = await upsert_entry(db, hentry)

    return redirect(url_for("feed.entry", uuid=entry.uuid))


@blueprint.route("/template", methods=["GET"])
@validate_querystring(TemplateRequest)
async def template(query_args: TemplateRequest) -> Response:
    """
    Serve the entry template.
    """
    return await render_template(f"crud/{query_args.template}.html")
