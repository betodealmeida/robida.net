"""
Homepage blueprint.
"""

import yaml

from quart import Blueprint, Response, current_app, render_template

from robida.helpers import reformat_html

blueprint = Blueprint("homepage", __name__, url_prefix="/")


@blueprint.route("", methods=["GET"])
async def index() -> Response:
    """
    Serve the main homepage.
    """
    with open(current_app.config["HCARD"], "r", encoding="utf-8") as input:
        hcard = yaml.safe_load(input)

    html = await render_template("index.html", data=hcard)
    return reformat_html(html)
