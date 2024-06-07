"""
Test the .well-known endpoints.
"""

from quart import testing


async def test_oauth_authorization_server(client: testing.QuartClient) -> None:
    """
    Test the OAuth2 endpoint.
    """
    response = await client.get("/.well-known/oauth-authorization-server")

    assert response.status_code == 200
    assert await response.json == {
        "authorization_endpoint": "http://example.com/auth",
        "authorization_response_iss_parameter_supported": True,
        "code_challenge_methods_supported": ["S256"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "introspection_endpoint": "http://example.com/introspect",
        "introspection_endpoint_auth_methods_supported": ["client_secret_basic"],
        "issuer": "http://example.com/.well-known/oauth-authorization-server",
        "response_types_supported": ["code", "id"],
        "revocation_endpoint": "http://example.com/revoke",
        "revocation_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": [
            "create",
            "draft",
            "update",
            "delete",
            "undelete",
            "media",
            "read",
            "follow",
            "mute",
            "block",
            "channels",
            "profile",
            "email",
        ],
        "service_documentation": "https://indieauth.spec.indieweb.org/",
        "token_endpoint": "http://example.com/token",
        "userinfo_endpoint": "http://example.com/userinfo",
    }
