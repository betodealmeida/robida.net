"""
Homepage blueprint.
"""

from quart import Blueprint, Response, make_response, render_template, url_for

blueprint = Blueprint("homepage", __name__, url_prefix="/")


# mapping between blueprint endpoints and rels
rels = {
    "self": "homepage.index",
    "micropub": "micropub.index",
}


@blueprint.route("/", methods=["GET"])
async def index() -> Response:
    """
    Serve the main homepage.
    """
    headers = {
        "Link": [
            f'<{url_for(endpoint, _external=True)}>; rel="{rel}"'
            for rel, endpoint in rels.items()
        ],
    }

    rendered = await render_template("index.html")
    response = await make_response(rendered)
    response.headers.update(headers)

    return response
