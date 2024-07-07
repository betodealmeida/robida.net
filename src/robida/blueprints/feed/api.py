"""
Feed for entries.
"""

# pylint: disable=no-value-for-parameter, unused-argument

from uuid import UUID

from quart import Blueprint, Response, current_app, render_template, request, session
from quart.helpers import redirect, url_for
from quart_schema import validate_querystring

from robida.constants import MAX_PAGE_SIZE
from robida.db import get_db
from robida.helpers import get_entry, hentry_from_entry, reformat_html

from .helpers import (
    build_jsonfeed,
    get_entries,
    get_feed_next_url,
    get_feed_previous_url,
    get_title,
    hfeed_from_entries,
    make_conditional_response,
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
    if query_args.page_size > MAX_PAGE_SIZE:
        return redirect(
            url_for("feed.html_index", page=query_args.page, page_size=MAX_PAGE_SIZE)
        )

    entries = await get_entries(
        query_args.since,
        offset=query_args.page_size * (query_args.page - 1),
        limit=query_args.page_size + 1,
    )
    next_url = get_feed_next_url("feed.html_index", query_args, len(entries))
    previous_url = get_feed_previous_url("feed.html_index", query_args)
    entries = entries[: query_args.page_size]

    response = make_conditional_response(entries)
    if response.status_code == 304:
        return response

    hfeed = hfeed_from_entries(entries, url_for("feed.html_index", _external=True))
    html = await render_template(
        "feed/index.html",
        hfeed=hfeed,
        title=f'h-feed for {current_app.config["SITE_NAME"]}',
        next_url=next_url,
        previous_url=previous_url,
        compact=True,
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
    if query_args.page_size > MAX_PAGE_SIZE:
        return redirect(
            url_for("feed.rss_index", page=query_args.page, page_size=MAX_PAGE_SIZE)
        )

    entries = await get_entries(
        query_args.since,
        offset=query_args.page_size * (query_args.page - 1),
        limit=query_args.page_size + 1,
    )
    next_url = get_feed_next_url(
        "feed.rss_index",
        query_args,
        len(entries),
        external=True,
    )
    previous_url = get_feed_previous_url("feed.rss_index", query_args, external=True)
    entries = entries[: query_args.page_size]

    response = make_conditional_response(entries)
    if response.status_code == 304:
        return response

    hfeed = hfeed_from_entries(entries, url_for("feed.rss_index", _external=True))
    xml = await render_template(
        "feed/rss.xml",
        hfeed=hfeed,
        title=f'RSS 2.0 feed for {current_app.config["SITE_NAME"]}',
        next_url=next_url,
        previous_url=previous_url,
        compact=True,
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
    if query_args.page_size > MAX_PAGE_SIZE:
        return redirect(
            url_for("feed.atom_index", page=query_args.page, page_size=MAX_PAGE_SIZE)
        )

    entries = await get_entries(
        query_args.since,
        offset=query_args.page_size * (query_args.page - 1),
        limit=query_args.page_size + 1,
    )
    next_url = get_feed_next_url("feed.atom_index", query_args, len(entries))
    previous_url = get_feed_previous_url("feed.atom_index", query_args)
    entries = entries[: query_args.page_size]

    response = make_conditional_response(entries)
    if response.status_code == 304:
        return response

    hfeed = hfeed_from_entries(entries, url_for("feed.atom_index", _external=True))
    xml = await render_template(
        "feed/atom.xml",
        hfeed=hfeed,
        title=f'Atom feed for {current_app.config["SITE_NAME"]}',
        next_url=next_url,
        previous_url=previous_url,
        compact=True,
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
    if query_args.page_size > MAX_PAGE_SIZE:
        return redirect(
            url_for("feed.json_index", page=query_args.page, page_size=MAX_PAGE_SIZE)
        )

    entries = await get_entries(
        query_args.since,
        offset=query_args.page_size * (query_args.page - 1),
        limit=query_args.page_size + 1,
    )
    next_url = get_feed_next_url(
        "feed.json_index",
        query_args,
        len(entries),
        external=True,
    )
    entries = entries[: query_args.page_size]

    response = make_conditional_response(entries)
    if response.status_code == 304:
        return response

    feed = build_jsonfeed(entries, next_url)
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
    authorized = session.get("me") == url_for("homepage.index", _external=True)

    # pylint: disable=redefined-outer-name
    async with get_db(current_app) as db:
        entry = await get_entry(db, uuid, include_private_children=authorized)

    if entry is None:
        return Response(status=404)

    if entry.deleted:
        html = await render_template(
            "feed/entry.html",
            hentry={
                "type": ["h-entry"],
                "properties": {
                    "uid": [str(uuid)],
                    "name": ["Entry deleted"],
                    "content": ["This entry has been deleted. 🗑️"],
                    "published": [entry.last_modified_at.isoformat()],
                },
            },
            title=f'Entry deleted — {current_app.config["SITE_NAME"]}',
        )
        return Response(html, status=410)

    if entry.visibility == "private" and not authorized:
        return Response("insufficient_scope", status=403)

    response = make_conditional_response([entry])
    if response.status_code == 304:
        return response

    hentry = hentry_from_entry(entry)
    title = get_title(hentry)
    html = await render_template(
        "feed/entry.html",
        hentry=hentry,
        title=f'{title} — {current_app.config["SITE_NAME"]}',
    )
    response.set_data(reformat_html(html))

    return response
