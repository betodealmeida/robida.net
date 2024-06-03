"""
Homepage blueprint.
"""

from quart import Blueprint, Response, make_response, render_template, url_for

blueprint = Blueprint("homepage", __name__, url_prefix="/")


# mapping between blueprint endpoints and rels
rels = {
    "self": "homepage.index",
    "micropub": "micropub.index",
    "indieauth-metadata": "wellknown.oauth_authorization_server",
    "authorization_endpoint": "indieauth.authorization",
    "token_endpoint": "indieauth.token",
}


@blueprint.route("/", methods=["GET"])
async def index() -> Response:
    """
    Serve the main homepage.
    """
    links = {rel: url_for(endpoint, _external=True) for rel, endpoint in rels.items()}

    headers = {"Link": [f'<{url}>; rel="{rel}"' for rel, url in links.items()]}

    rendered = await render_template("index.html", links=links)
    response = await make_response(rendered)
    response.headers.update(headers)

    return response
