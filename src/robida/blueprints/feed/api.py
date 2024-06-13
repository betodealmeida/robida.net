"""
Feed for entries.
"""

# pylint: disable=no-value-for-parameter, unused-argument

from uuid import UUID

from quart import Blueprint, Response, current_app, render_template, request
from quart.helpers import url_for
from quart_schema import validate_querystring

from .helpers import (
    build_jsonfeed,
    get_entries,
    hfeed_from_entries,
    make_conditional_response,
    reformat_html,
)
from .models import FeedRequest

blueprint = Blueprint("feed", __name__, url_prefix="/")

LIMIT = 25


@blueprint.route("/feed", methods=["GET"])
@validate_querystring(FeedRequest)
async def index(query_args: FeedRequest) -> Response:
    """
    Load all the entries and build a feed.

    The feed can be:

      - A JSON Feed
      - RSS
      - Atom
      - An h-feed HTML page

    A specific version can be requested by appending a related prefix (e.g. `.json`) or
    using content negotiation via the `Accept` header.
    """
    if request.headers.get("Accept", "") in {
        "application/feed+json",
        "application/json",
    }:
        return await json_index()

    if request.headers.get("Accept", "") == "application/rss+xml":
        return await rss_index()

    if request.headers.get("Accept", "") == "application/atom+xml":
        return await atom_index()

    return await html_index()


@blueprint.route("/feed.html", methods=["GET"])
@validate_querystring(FeedRequest)
async def html_index(query_args: FeedRequest) -> Response:
    """
    Return an h-feed HTML page.

    http://microformats.org/wiki/h-feed
    """
    entries = await get_entries(
        query_args.since,
        page=query_args.page - 1,
        page_size=query_args.page_size or int(current_app.config["PAGE_SIZE"]),
    )

    response = make_conditional_response(entries)
    if response.status_code == 304:
        return response

    hfeed = hfeed_from_entries(entries, url_for("feed.html_index", _external=True))
    html = await render_template(
        "feed/index.html",
        hfeed=hfeed,
        title=f'h-feed for {current_app.config["SITE_NAME"]}',
    )
    response.set_data(reformat_html(html))

    # Only set the content to `text/mf2+html` if it's explicitly requested, otherwise the
    # browser will download the file instead of rendering it.
    content_type = (
        "text/mf2+html"
        if "text/mf2+html" in request.headers.get("Accept", "")
        else "text/html"
    )
    response.headers.update(
        {
            "Content-Type": content_type,
            "Link": f'<{url_for("feed.html_index", _external=True)}>; rel="self"',
        }
    )

    return response


@blueprint.route("/rss.xslt", methods=["GET"])
async def rss_xslt() -> Response:
    """
    Return an XSLT stylesheet for RSS.
    """
    xslt = await render_template("feed/rss.xslt")
    return Response(xslt, content_type="application/xslt+xml")


@blueprint.route("/atom.xslt", methods=["GET"])
async def atom_xslt() -> Response:
    """
    Return an XSLT stylesheet for Atom.
    """
    xslt = await render_template("feed/atom.xslt")
    return Response(xslt, content_type="application/xslt+xml")


@blueprint.route("/feed.rss", methods=["GET"])
@validate_querystring(FeedRequest)
async def rss_index(query_args: FeedRequest) -> Response:
    """
    Return an RSS feed.
    """
    entries = await get_entries(
        query_args.since,
        page=query_args.page - 1,
        page_size=query_args.page_size or int(current_app.config["PAGE_SIZE"]),
    )

    response = make_conditional_response(entries)
    if response.status_code == 304:
        return response

    hfeed = hfeed_from_entries(entries, url_for("feed.rss_index", _external=True))
    xml = await render_template(
        "feed/rss.xml",
        hfeed=hfeed,
        title=f'RSS 2.0 feed for {current_app.config["SITE_NAME"]}',
    )
    response.set_data(xml)

    # Only set the content to `application/rss+xml` if it's explicitly requested,
    # otherwise the browser will download the file instead of rendering it.
    content_type = (
        "application/rss+xml"
        if "application/rss+xml" in request.headers.get("Accept", "")
        else "application/xml"
    )
    response.headers.update(
        {
            "Content-Type": content_type,
            "Link": f'<{url_for("feed.rss_index", _external=True)}>; rel="self"',
        }
    )

    return response


@blueprint.route("/feed.xml", methods=["GET"])
@validate_querystring(FeedRequest)
async def atom_index(query_args: FeedRequest) -> Response:
    """
    Return an Atom feed.
    """
    entries = await get_entries(
        query_args.since,
        page=query_args.page - 1,
        page_size=query_args.page_size or int(current_app.config["PAGE_SIZE"]),
    )

    response = make_conditional_response(entries)
    if response.status_code == 304:
        return response

    hfeed = hfeed_from_entries(entries, url_for("feed.atom_index", _external=True))
    xml = await render_template(
        "feed/atom.xml",
        hfeed=hfeed,
        title=f'Atom feed for {current_app.config["SITE_NAME"]}',
    )
    response.set_data(xml)

    # Only set the content to `application/atom+xml` if it's explicitly requested,
    # otherwise the browser will download the file instead of rendering it.
    content_type = (
        "application/atom+xml"
        if "application/atom+xml" in request.headers.get("Accept", "")
        else "application/xml"
    )
    response.headers.update(
        {
            "Content-Type": content_type,
            "Link": f'<{url_for("feed.atom_index", _external=True)}>; rel="self"',
        }
    )

    return response


@blueprint.route("/feed.json", methods=["GET"])
@validate_querystring(FeedRequest)
async def json_index(query_args: FeedRequest) -> Response:
    """
    Return a JSON feed.

    https://www.jsonfeed.org/version/1.1/
    """
    entries = await get_entries(
        query_args.since,
        page=query_args.page - 1,
        page_size=query_args.page_size or int(current_app.config["PAGE_SIZE"]),
    )

    response = make_conditional_response(entries)
    if response.status_code == 304:
        return response

    feed = build_jsonfeed(entries, query_args)
    response.set_data(feed.model_dump_json(exclude_unset=True))
    response.headers.update(
        {
            "Content-Type": "application/feed+json",
            "Link": f'<{url_for("feed.json_index", _external=True)}>; rel="self"',
        }
    )

    return response


@blueprint.route("/feed/<uuid:uuid>", methods=["GET"])
async def entry(uuid: UUID) -> dict:
    """
    Load a single entry.
    """
    return {"entry": uuid.hex}
