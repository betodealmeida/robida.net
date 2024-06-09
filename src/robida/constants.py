"""
Constants for the application
"""

# mapping between blueprint endpoints and rels
rels = {
    "micropub": "micropub.index",
    "indieauth-metadata": "wellknown.oauth_authorization_server",
    "authorization_endpoint": "indieauth.authorization",
    "token_endpoint": "indieauth.token",
    "hub": "websub.hub",
}
