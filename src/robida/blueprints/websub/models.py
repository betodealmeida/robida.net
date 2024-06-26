"""
WebSub models.
"""

from typing import Literal

from pydantic import ConfigDict, create_model

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


SubscriptionRequest = create_model(
    "SubscriptionRequest",
    model_config=ConfigDict(extra="ignore"),
    **subscription_annotations,
)

PublishRequest = create_model(
    "PublishRequest",
    model_config=ConfigDict(extra="ignore"),
    **publish_annotations,
)
