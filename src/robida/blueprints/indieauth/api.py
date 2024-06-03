"""
IndieAuth blueprint.
"""

import urllib.parse
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from quart import Blueprint, Response, render_template, request
from quart.helpers import make_response
from quart_schema import validate_request

from robida.blueprints.wellknown.api import (
    CODE_CHALLENGE_METHODS_SUPPORTED,
    RESPONSE_TYPES_SUPPORTED,
)
from robida.db import get_db

from .helpers import get_client_info
from .models import AuthorizationRequest

blueprint = Blueprint("indieauth", __name__, url_prefix="/")


@blueprint.route("/auth", methods=["GET"])
@validate_request(AuthorizationRequest)
async def authorization() -> Response:
    """
    handle the authorization request
    """
    authorization_request = AuthorizationRequest(**request.args)

    if authorization_request.response_type not in RESPONSE_TYPES_SUPPORTED or (
        authorization_request.code_challenge_method
        not in CODE_CHALLENGE_METHODS_SUPPORTED
    ):
        return make_response("invalid_request", 400)

    app_info, redirect_uris = get_client_info(authorization_request.client_id)

    parsed_client_id = urllib.parse.urlparse(authorization_request.client_id)
    parsed_redirect_uri = urllib.parse.urlparse(authorization_request.redirect_uri)
    if (
        parsed_client_id.scheme != parsed_redirect_uri.scheme
        or parsed_client_id.hostname != parsed_redirect_uri.hostname
        or parsed_client_id.port != parsed_redirect_uri.port
    ) and authorization_request.redirect_uri not in redirect_uris:
        return make_response("invalid_request", 400)

    code = str(uuid4())
    created_at = datetime.now(timezone.utc)

    async with get_db() as db:
        await db.execute(
            "INSERT INTO oauth_authorization_codes "
            "(code, client_id, redirect_uri, code_challenge, "
            "code_challenge_method, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                code,
                authorization_request.client_id,
                authorization_request.redirect_uri,
                authorization_request.code_challenge,
                authorization_request.code_challenge_method,
                created_at + timedelta(minutes=10),
                created_at,
            ),
        )
        await db.commit()

    parsed = urllib.parse.urlparse(authorization_request.redirect_uri)
    query_params = urllib.parse.parse_qs(parsed.query)
    query_params.update(
        {
            "code": [code],
            "state": [authorization_request.state],
        }
    )
    query = urllib.parse.urlencode(query_params)
    redirect_url = urllib.parse.urlunparse(parsed._replace(query=query))

    return render_template(
        "auth.html",
        me=authorization_request.me,
        app_info=app_info,
        scope=authorization_request.scope,
        redirect_url=redirect_url,
    )


@blueprint.route("/token", methods=["GET"])
async def token() -> dict:
    return {"version": "1.0", "type": "indieauth"}


@blueprint.route("/introspect", methods=["GET"])
async def introspect() -> dict:
    return {"version": "1.0", "type": "indieauth"}


@blueprint.route("/revoke", methods=["GET"])
async def revoke() -> dict:
    return {"version": "1.0", "type": "indieauth"}


@blueprint.route("/userinfo", methods=["GET"])
async def userinfo() -> dict:
    return {"version": "1.0", "type": "indieauth"}
