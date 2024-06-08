"""
Homepage blueprint.
"""

from quart import Blueprint, Response, render_template

blueprint = Blueprint("homepage", __name__, url_prefix="/")


@blueprint.route("", methods=["GET"])
async def index() -> Response:
    """
    Serve the main homepage.
    """
    return await render_template("index.html")
