"""
Homepage blueprint.
"""

from quart import Blueprint, Response, render_template

from robida.helpers import get_own_hcard, reformat_html

blueprint = Blueprint("homepage", __name__, url_prefix="/")


@blueprint.route("", methods=["GET"])
async def index() -> Response:
    """
    Serve the main homepage.
    """
    hcard = get_own_hcard()
    html = await render_template("index.html", data=hcard)
    return reformat_html(html)
