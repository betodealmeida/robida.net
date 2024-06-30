"""
Category API.
"""

from quart import Blueprint, Response, current_app, render_template
from quart.helpers import url_for
from quart_schema import validate_querystring

from robida.blueprints.feed.helpers import (
    hfeed_from_entries,
    make_conditional_response,
    reformat_html,
)

from .helpers import list_entries
from .models import CategoryRequest

blueprint = Blueprint("category", __name__, url_prefix="/")


@blueprint.route("/about", defaults={"category": "about"})
@blueprint.route("/contact", defaults={"category": "contact"})
@blueprint.route("/now", defaults={"category": "now"})
@blueprint.route("/category/<category>", methods=["GET"])
@validate_querystring(CategoryRequest)
async def index(category: str, query_args: CategoryRequest) -> Response:
    """
    Category for items.
    """
    compact = category not in {"about", "contact", "now"}

    entries = await list_entries(
        category,
        page=query_args.page - 1,
        page_size=query_args.page_size or int(current_app.config["PAGE_SIZE"]),
    )

    response = make_conditional_response(entries)
    if response.status_code == 304:
        return response

    hfeed = hfeed_from_entries(
        entries,
        url_for(
            "category.index",
            category=category,
            _external=True,
        ),
    )
    html = await render_template("feed/index.html", hfeed=hfeed, compact=compact)
    response.set_data(reformat_html(html))

    return response
