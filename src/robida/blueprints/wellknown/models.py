"""
Models for well-known responses.
"""

from typing import Annotated

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, HttpUrl, UrlConstraints
from pydantic.functional_validators import AfterValidator


def no_query(url: AnyUrl) -> AnyUrl:
    """
    Prevent query string in URL.
    """
    assert url.query is None, "Query string is not allowed in URL"
    return url


def no_fragment(url: AnyUrl) -> AnyUrl:
    """
    Prevent fragment in URL.
    """
    assert url.fragment is None, "Fragment is not allowed in URL"
    return url


IssuerUrl = Annotated[
    AnyUrl,
    UrlConstraints(allowed_schemes=["http", "https"]),
    AfterValidator(no_query),
    AfterValidator(no_fragment),
]


class ServerMetadataResponse(BaseModel):
    """
    Server metadata response.

    https://indieauth.spec.indieweb.org/#indieauth-server-metadata
    """

    model_config = ConfigDict(extra="ignore")

    issuer: IssuerUrl
    authorization_endpoint: HttpUrl
    token_endpoint: HttpUrl
    introspection_endpoint: HttpUrl
    introspection_endpoint_auth_methods_supported: list[str] | None = None
    revocation_endpoint: HttpUrl | None = None
    revocation_endpoint_auth_methods_supported: list[str] | None = None
    scopes_supported: list[str] | None = None
    response_types_supported: list[str] | None = None
    grant_types_supported: list[str] | None = None
    service_documentation: HttpUrl | None = None
    code_challenge_methods_supported: list[str] = Field(default_factory=list)
    authorization_response_iss_parameter_supported: bool | None = None
    userinfo_endpoint: HttpUrl | None = None
