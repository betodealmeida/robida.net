"""
WebSub models.
"""

from typing import Literal

from pydantic import create_model

subscription_annotations = {
    "hub.callback": (str, ...),
    "hub.mode": (Literal["subscribe", "unsubscribe"], ...),
    "hub.topic": (str, ...),
    "hub.lease_seconds": (int | None, None),
    "hub.secret": (str | None, None),
}

publish_annotations = {
    "hub.mode": (Literal["publish"], ...),
    "hub.url": (str | None, None),
    "hub.url[]": (list[str] | None, None),
}


class Config:  # pylint: disable=too-few-public-methods
    """
    Ignore any extra query arguments.

    "Hubs MUST ignore additional request parameters they do not understand."
    https://www.w3.org/TR/websub/#subscriber-sends-subscription-request
    """

    extr = "ignore"


SubscriptionRequest = create_model(
    "SubscriptionRequest",
    __config__=Config,
    **subscription_annotations,
)

PublishRequest = create_model(
    "PublishRequest",
    __config__=Config,
    **publish_annotations,
)
