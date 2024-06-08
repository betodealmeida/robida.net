"""
WebSub API endpoints.

https://www.w3.org/TR/websub/
"""

from datetime import timedelta

from quart import Blueprint, Response, current_app
from quart.helpers import make_response, url_for
from quart_schema import DataSource, validate_request


from .helpers import distribute_content, validate_subscription
from .models import PublishRequest, SubscriptionRequest


blueprint = Blueprint("websub", __name__, url_prefix="/websub")


MAX_LEASE = timedelta(days=365)


@blueprint.route("", methods=["POST"])
@validate_request(SubscriptionRequest, source=DataSource)
async def hub(data: SubscriptionRequest) -> Response:
    """
    WebSub hub endpoint.
    """
    baseurl = url_for("feed.index", _external=True)
    if not getattr(data, "hub.topic").startswith(baseurl):
        return await make_response(f"Only URLs in {baseurl} are supported", 400)

    current_app.add_background_task(validate_subscription, data)
    return await make_response("", 202)


@blueprint.route("/publish", methods=["POST"])
@validate_request(PublishRequest, source=DataSource)
async def publish(data: PublishRequest) -> Response:
    """
    WebSub publish endpoint.
    """
    urls = getattr(data, "hub.url[]") or []
    if url := getattr(data, "hub.url"):
        urls.append(url)

    current_app.add_background_task(distribute_content, urls)
    return await make_response("", 202)
