"""
Well-known endpoints.
"""

from quart import Blueprint
from quart.helpers import url_for
from quart_schema import validate_response

from .models import ServerMetadataResponse

blueprint = Blueprint("wellknown", __name__, url_prefix="/.well-known")

RESPONSE_TYPES_SUPPORTED = {"code", "id"}
GRANT_TYPES_SUPPORTED = {"authorization_code", "refresh_token"}
CODE_CHALLENGE_METHODS_SUPPORTED = {"S256"}
SCOPES_SUPPORTED = [
    # micropub
    "create",
    "draft",
    "update",
    "delete",
    "undelete",
    "media",
    # microsub
    "read",
    "follow",
    "mute",
    "block",
    "channels",
    # indieauth
    "profile",
    "email",
]


@blueprint.route("/oauth-authorization-server", methods=["GET"])
@validate_response(ServerMetadataResponse)
async def oauth_authorization_server() -> ServerMetadataResponse:
    """
    IndieAuth information.
    """
    return ServerMetadataResponse(
        issuer=url_for("wellknown.oauth_authorization_server", _external=True),
        authorization_endpoint=url_for("indieauth.authorization", _external=True),
        token_endpoint=url_for("indieauth.token", _external=True),
        introspection_endpoint=url_for("indieauth.introspect", _external=True),
        introspection_endpoint_auth_methods_supported=["client_secret_basic"],
        revocation_endpoint=url_for("indieauth.revoke", _external=True),
        revocation_endpoint_auth_methods_supported=["none"],
        scopes_supported=SCOPES_SUPPORTED,
        response_types_supported=sorted(RESPONSE_TYPES_SUPPORTED),
        grant_types_supported=sorted(GRANT_TYPES_SUPPORTED),
        service_documentation="https://indieauth.spec.indieweb.org/",
        code_challenge_methods_supported=sorted(CODE_CHALLENGE_METHODS_SUPPORTED),
        authorization_response_iss_parameter_supported=True,
        userinfo_endpoint=url_for("indieauth.userinfo", _external=True),
    )
