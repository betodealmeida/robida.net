"""
Micropub models.
"""

from enum import Enum


class ErrorType(str, Enum):
    """
    Micropub error types.

    See https://www.w3.org/TR/micropub/#error-response-li-3.
    """

    FORBIDDEN = "forbidden"
    UNAUTHORIZED = "unauthorized"
    INSUFFICIENT_SCOPE = "insufficient_scope"
    INVALID_REQUEST = "invalid_request"


class ActionType(str, Enum):
    """
    Micropub action types.
    """

    UPDATE = "update"
    DELETE = "delete"
    UNDELETE = "undelete"


class UpdateProperty(str, Enum):
    """
    Micropub update properties.
    """

    ADD = "add"
    REPLACE = "replace"
    DELETE = "delete"
