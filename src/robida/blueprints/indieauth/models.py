"""
IndieAuth models.
"""

from dataclasses import dataclass


@dataclass
class AuthorizationRequest:  # pylint: disable=too-many-instance-attributes
    """
    Authorization request data.
    """

    response_type: str
    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str | None = None
    code_challenge_method: str | None = None
    scope: str | None = None
    me: str | None = None


@dataclass
class RedeemCodeRequest:
    """
    Redeem code request data.
    """

    code: str
    client_id: str
    redirect_uri: str
    grant_type: str = "authorization_code"
    code_verifier: str | None = None


@dataclass
class RefreshTokenRequest:
    """
    Refresh token request data.
    """

    grant_type: str
    refresh_token: str
    client_id: str
    scope: str | None = None


@dataclass
class ProfileURLResponse:
    """
    Profile URL response data.
    """

    me: str


@dataclass
class AccessTokenResponse:
    """
    Access token response data.
    """

    access_token: str
    refresh_token: str
    me: str
    expires_in: int
    token_type: str
    scope: str


@dataclass
class ProfileResponse:
    """
    Profile information response.
    """

    name: str
    url: str
    photo: str
    email: str | None = None


@dataclass
class AccessTokenWithProfileResponse(AccessTokenResponse):
    """
    Access token response data with profile.
    """

    profile: ProfileResponse


@dataclass
class RefreshTokenResponse:
    """
    Access token response data.
    """

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str
    scope: str | None = None


@dataclass
class TokenRequest:
    """
    Token request data.

    Used for token introspection and revocation.
    """

    token: str


@dataclass
class TokenVerificationResponse:
    """
    Verification response for invalid tokens.
    """

    active: bool


@dataclass
class ValidTokenVerificationResponse(TokenVerificationResponse):
    """
    Verification response for valid tokens.
    """

    me: str
    client_id: str
    scope: str
    exp: int
    iat: int


@dataclass
class AuthRedirectRequest:
    """
    Authorization redirect request data.
    """

    code: str
    redirect_uri: str
    known: list[str] | str | None = None
    unknown: list[str] | str | None = None
    other: list[str] | str | None = None
