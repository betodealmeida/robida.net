"""
IndieAuth blueprint.

https://indieauth.spec.indieweb.org/
https://aaronparecki.com/2020/12/03/1/indieauth-2020
"""

# pylint: disable=no-value-for-parameter, redefined-outer-name

import hashlib
import urllib.parse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from quart import Blueprint, Response, current_app, g, render_template, request, session
from quart.helpers import make_response, redirect, url_for
from quart_schema import (
    DataSource,
    validate_querystring,
    validate_request,
    validate_response,
)

from robida.blueprints.wellknown.api import (
    CODE_CHALLENGE_METHODS_SUPPORTED,
    GRANT_TYPES_SUPPORTED,
    RESPONSE_TYPES_SUPPORTED,
    SCOPES_SUPPORTED,
)
from robida.db import get_db

from .helpers import (
    get_client_info,
    get_scopes,
    redirect_match,
    requires_scope,
    verify_code_challenge,
)
from .models import (
    AccessTokenResponse,
    AccessTokenWithProfileResponse,
    AuthorizationRequest,
    AuthRedirectRequest,
    ProfileResponse,
    ProfileURLResponse,
    RedeemCodeRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    TokenRequest,
    TokenVerificationResponse,
    ValidTokenVerificationResponse,
)

blueprint = Blueprint("indieauth", __name__, url_prefix="/")

VERIFICATION_METHODS = {
    "S256": hashlib.sha256,
}
CODE_EXPIRATION = timedelta(minutes=10)
ACCESS_TOKEN_EXPIRATION = timedelta(hours=1)
REFRESH_TOKEN_EXPIRATION = timedelta(days=365)


@blueprint.route("/auth", methods=["GET"])
@validate_querystring(AuthorizationRequest)
async def authorization(query_args: AuthorizationRequest) -> Response:
    """
    Handle the authorization request
    """
    # If for some reason the user is logged as someone else, log them out. This could
    # happen because we're using RelMeAuth to login, so technically anyone could log in
    # to the website.
    if session.get("me") and session["me"] != url_for("homepage.index", _external=True):
        session.pop("me")
        return await make_response("insufficient_scope", 403)

    # If the user is not logged in, store the payload to continue the flow later, and
    # redirect them to the login page.
    if "me" not in session:
        session["next"] = url_for("indieauth.authorization", **asdict(query_args))
        return redirect(url_for("relmeauth.login"))

    if query_args.response_type not in RESPONSE_TYPES_SUPPORTED or (
        query_args.code_challenge_method not in CODE_CHALLENGE_METHODS_SUPPORTED
    ):
        return await make_response("invalid_request", 400)

    client_info = await get_client_info(query_args.client_id)

    if (
        not redirect_match(query_args.client_id, query_args.redirect_uri)
        and query_args.redirect_uri not in client_info.redirect_uris
    ):
        return await make_response("invalid_request", 400)

    code = uuid4().hex
    created_at = datetime.now(timezone.utc)

    async with get_db(current_app) as db:
        await db.execute(
            """
INSERT INTO oauth_authorization_codes (
    code,
    client_id,
    redirect_uri,
    scope,
    code_challenge,
    code_challenge_method,
    used,
    expires_at,
    created_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                query_args.client_id,
                query_args.redirect_uri,
                query_args.scope,
                query_args.code_challenge,
                query_args.code_challenge_method,
                False,
                created_at + CODE_EXPIRATION,
                created_at,
            ),
        )
        await db.commit()

    parsed = urllib.parse.urlparse(query_args.redirect_uri)
    query_params: dict[str, Any] = urllib.parse.parse_qs(parsed.query)
    query_params.update(
        {
            "code": code,
            "state": query_args.state,
            "iss": url_for("wellknown.oauth_authorization_server", _external=True),
        }
    )
    query = urllib.parse.urlencode(query_params)
    redirect_uri = parsed._replace(query=query).geturl()

    supported_scopes = set(SCOPES_SUPPORTED)
    requested_scopes = set(query_args.scope.split(" ")) if query_args.scope else set()
    known_requested_scopes = sorted(requested_scopes & supported_scopes)
    unknown_requested_scopes = sorted(requested_scopes - supported_scopes)
    other_scopes = sorted(supported_scopes - requested_scopes)

    return await render_template(
        "indieauth/auth.html",
        me=query_args.me,
        client_info=client_info,
        code=code,
        known_requested_scopes=known_requested_scopes,
        unknown_requested_scopes=unknown_requested_scopes,
        other_scopes=other_scopes,
        redirect_uri=redirect_uri,
    )


@blueprint.route("/auth/redirect", methods=["POST"])
@validate_request(AuthRedirectRequest, source=DataSource.FORM)
async def auth_redirect(data: AuthRedirectRequest) -> Response:
    """
    Redirect user to the client application.

    This allows the user to modify the requested scope.
    """
    scopes = []
    for group in [data.known, data.unknown, data.other]:
        if group:
            if isinstance(group, str):
                scopes.append(group)
            else:
                scopes.extend(group)

    scope = " ".join(sorted(scopes))

    async with get_db(current_app) as db:
        await db.execute(
            """
UPDATE
    oauth_authorization_codes
SET
    scope = ?
WHERE
    code = ?
            """,
            (scope, data.code),
        )
        await db.commit()

    return redirect(data.redirect_uri)


@blueprint.route("/auth", methods=["POST"])
@validate_request(RedeemCodeRequest, source=DataSource.FORM)
@validate_response(ProfileURLResponse)
async def profile_url(data: RedeemCodeRequest) -> ProfileURLResponse:
    """
    Return profile URL.
    """
    if data.grant_type not in GRANT_TYPES_SUPPORTED:
        return await make_response("invalid_request", 400)

    async with get_db(current_app) as db:
        async with db.execute(
            """
SELECT
    code_challenge,
    code_challenge_method
FROM
    oauth_authorization_codes
WHERE
    code = ? AND
    client_id = ? AND
    redirect_uri = ? AND
    used IS FALSE AND
    expires_at > ?
            """,
            (
                data.code,
                data.client_id,
                data.redirect_uri,
                datetime.now(timezone.utc),
            ),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return await make_response("invalid_grant", 400)

        if not verify_code_challenge(
            row["code_challenge"],
            row["code_challenge_method"],
            data.code_verifier,
        ):
            return await make_response("invalid_request", 400)

        await db.execute(
            """
UPDATE
    oauth_authorization_codes
SET
    used = TRUE
WHERE
    code = ?
            """,
            (data.code,),
        )
        await db.commit()

    return ProfileURLResponse(me=url_for("homepage.index", _external=True))


@blueprint.route("/token", methods=["POST"])
async def token() -> Response:
    """
    Dispatcher for access token and refresh token requests.
    """
    payload = await request.form
    grant_type = payload.get("grant_type")

    if grant_type not in GRANT_TYPES_SUPPORTED:
        return await make_response("invalid_request", 400)

    if grant_type == "authorization_code":
        return await access_token()

    if grant_type == "refresh_token":
        return await refresh_token()

    return await make_response("unsupported_grant_type", 400)


@validate_request(RedeemCodeRequest, source=DataSource.FORM)
@validate_response(AccessTokenResponse)
async def access_token(data: RedeemCodeRequest) -> AccessTokenResponse:
    """
    Handle the access token request
    """
    async with get_db(current_app) as db:
        async with db.execute(
            """
SELECT
    scope,
    code_challenge,
    code_challenge_method
FROM
    oauth_authorization_codes
WHERE
    code = ? AND
    client_id = ? AND
    redirect_uri = ? AND
    used IS FALSE AND
    expires_at > ?
            """,
            (
                data.code,
                data.client_id,
                data.redirect_uri,
                datetime.now(timezone.utc),
            ),
        ) as cursor:
            row = await cursor.fetchone()

        if (
            row is None
            or not row["scope"]
            or not verify_code_challenge(
                row["code_challenge"],
                row["code_challenge_method"],
                data.code_verifier,
            )
        ):
            return await make_response("invalid_request", 400)

        # generate tokens
        access_token = f"ra_{uuid4().hex}"
        refresh_token = f"rr_{uuid4().hex}"
        created_at = datetime.now(timezone.utc)
        token_type = "Bearer"

        await db.execute(
            """
INSERT INTO oauth_tokens (
    client_id,
    token_type,
    access_token,
    refresh_token,
    scope,
    expires_at,
    last_refresh_at,
    created_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.client_id,
                token_type,
                access_token,
                refresh_token,
                row["scope"],
                created_at + ACCESS_TOKEN_EXPIRATION,
                created_at,
                created_at,
            ),
        )
        await db.commit()

    parameters = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "me": url_for("homepage.index", _external=True),
        "expires_in": int(ACCESS_TOKEN_EXPIRATION.total_seconds()),
        "token_type": token_type,
        "scope": row["scope"],
    }

    scopes = set(row["scope"].split(" "))
    if "profile" not in scopes:
        return AccessTokenResponse(**parameters)

    parameters["profile"] = {
        "name": current_app.config["NAME"],
        "url": url_for("homepage.index", _external=True),
        "photo": url_for("static", filename="photo.jpg", _external=True),
    }
    if "email" in scopes:
        parameters["profile"]["email"] = current_app.config["EMAIL"]

    return AccessTokenWithProfileResponse(**parameters)


@validate_request(RefreshTokenRequest, source=DataSource.FORM)
@validate_response(RefreshTokenResponse)
async def refresh_token(data: RefreshTokenRequest) -> RefreshTokenResponse:
    """
    Handle the token refresh request
    """
    async with get_db(current_app) as db:
        async with db.execute(
            """
SELECT
    scope,
    last_refresh_at
FROM
    oauth_tokens
WHERE
    client_id = ? AND
    refresh_token = ?
            """,
            (data.client_id, data.refresh_token),
        ) as cursor:
            row = await cursor.fetchone()

        now = datetime.now(timezone.utc)

        # check that the refresh token has been used recently
        last_refresh = datetime.fromisoformat(row["last_refresh_at"])
        if last_refresh + REFRESH_TOKEN_EXPIRATION < now:
            return await make_response("invalid_grant", 400)

        # scope can only be reduced
        if data.scope:
            if not set(data.scope.split(" ")) <= set(row["scope"].split(" ")):
                return await make_response("invalid_scope", 400)
        else:
            data.scope = row["scope"]

        # generate tokens
        access_token = f"ra_{uuid4().hex}"
        refresh_token = f"rr_{uuid4().hex}"
        token_type = "Bearer"

        await db.execute(
            """
UPDATE
    oauth_tokens
SET
    access_token = ?,
    refresh_token = ?,
    scope = ?,
    expires_at = ?,
    last_refresh_at = ?
WHERE
    client_id = ? AND
    refresh_token = ?
            """,
            (
                access_token,
                refresh_token,
                data.scope,
                now + ACCESS_TOKEN_EXPIRATION,
                now,
                data.client_id,
                data.refresh_token,
            ),
        )
        await db.commit()

    return RefreshTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(ACCESS_TOKEN_EXPIRATION.total_seconds()),
        token_type=token_type,
        scope=data.scope,
    )


@blueprint.route("/introspect", methods=["POST"])
@validate_request(TokenRequest, source=DataSource.FORM)
@validate_response(TokenVerificationResponse)
async def introspect(data: TokenRequest) -> TokenVerificationResponse:
    """
    Handle token introspection
    """
    async with get_db(current_app) as db:
        async with db.execute(
            """
SELECT
    client_id,
    scope,
    expires_at,
    created_at
FROM
    oauth_tokens
WHERE
    access_token = ?
            """,
            (data.token,),
        ) as cursor:
            row = await cursor.fetchone()

    if datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
        return TokenVerificationResponse(active=False)

    exp = int(datetime.fromisoformat(row["expires_at"]).timestamp())
    iat = int(datetime.fromisoformat(row["created_at"]).timestamp())

    return ValidTokenVerificationResponse(
        active=True,
        me=url_for("homepage.index", _external=True),
        client_id=row["client_id"],
        scope=row["scope"],
        exp=exp,
        iat=iat,
    )


@blueprint.route("/revoke", methods=["POST"])
@validate_request(TokenRequest, source=DataSource.FORM)
async def revoke(data: TokenRequest) -> Response:
    """
    Revokes a token
    """
    async with get_db(current_app) as db:
        await db.execute(
            """
UPDATE
    oauth_tokens
SET
    expires_at = ?
WHERE
    access_token = ?
            """,
            (datetime.now(timezone.utc), data.token),
        )

        await db.commit()
    return await make_response("", 200)


@blueprint.route("/userinfo", methods=["GET"])
@requires_scope("profile")
@validate_response(ProfileResponse)
async def userinfo() -> ProfileResponse:
    """
    Returns user information
    """
    response = ProfileResponse(
        name=current_app.config["NAME"],
        url=url_for("homepage.index", _external=True),
        photo=url_for("static", filename="photo.jpg", _external=True),
    )

    scopes = await get_scopes(g.access_token)
    if "email" in scopes:
        response.email = current_app.config["EMAIL"]

    return response
