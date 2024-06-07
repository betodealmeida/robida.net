"""
RelMeAuth models.
"""

from dataclasses import dataclass


@dataclass
class LoginRequest:
    """
    Data class for a login request.
    """

    me: str
