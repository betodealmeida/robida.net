"""
Feed for entries.
"""

from uuid import UUID

from quart import Blueprint

blueprint = Blueprint("entries", __name__, url_prefix="/entries")


@blueprint.route("/", methods=["GET"])
async def entries() -> dict:
    """
    Load all the entries.
    """
    return {"entries": "entries"}


@blueprint.route("/<uuid:uuid>", methods=["GET"])
async def entry(uuid: UUID) -> dict:
    """
    Load a single entry.
    """
    return {"entry": uuid.hex}
