"""
Search API.
"""

from quart import Blueprint, Response, current_app, render_template
from quart.helpers import url_for
from quart_schema import validate_querystring

from robida.blueprints.feed.helpers import (
    hfeed_from_entries,
    make_conditional_response,
    reformat_html,
)

from .helpers import search_entries
from .models import SearchRequest

blueprint = Blueprint("search", __name__, url_prefix="/search")


@blueprint.route("", methods=["GET"])
@validate_querystring(SearchRequest)
async def index(query_args: SearchRequest) -> Response:
    """
    Search for items.
    """
    entries = await search_entries(
        query_args.q,
        page=query_args.page - 1,
        page_size=query_args.page_size or int(current_app.config["PAGE_SIZE"]),
    )

    response = make_conditional_response(entries)
    if response.status_code == 304:
        return response

    hfeed = hfeed_from_entries(entries, url_for("search.index", _external=True))
    html = await render_template("feed/index.html", hfeed=hfeed, compact=True)
    response.set_data(reformat_html(html))

    return response
