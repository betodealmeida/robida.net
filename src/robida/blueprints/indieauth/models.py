"""
IndieAuth models.
"""

from dataclasses import dataclass


@dataclass
class AuthorizationRequest:
    """
    Authorization request data.
    """

    response_type: str
    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str
    code_challenge_method: str
    scope: str | None = None
    me: str | None = None
