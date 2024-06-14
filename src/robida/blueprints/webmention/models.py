"""
WebMention models.
"""

from dataclasses import dataclass
from enum import Enum


class WebMentionStatus(str, Enum):
    """
    WebMention status.
    """

    # generic
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"

    # for incoming only:
    RECEIVED = "received"
    PENDING_MODERATION = "pending_moderation"

    # for outgoing only:
    NO_ENDPOINT = "no_endpoint"


@dataclass
class WebMentionRequest:
    """
    A WebMention request.
    """

    source: str
    target: str
    vouch: str | None = None
