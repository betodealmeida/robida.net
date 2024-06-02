"""
Feed for entries.
"""

from uuid import UUID

from quart import Blueprint

blueprint = Blueprint("feed", __name__, url_prefix="/feed")


@blueprint.route("/", methods=["GET"])
async def feed() -> dict:
    """
    Load the feed with entries.
    """
    return {"feed": "feed"}


@blueprint.route("/<uuid:uuid>", methods=["GET"])
async def entry(uuid: UUID) -> dict:
    """
    Load a single entry.
    """
    return {"entry": str(uuid)}
