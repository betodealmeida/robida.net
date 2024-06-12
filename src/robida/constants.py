"""
Constants for the application
"""

# mapping between blueprint endpoints and rels
links = [
    {"rel": "micropub", "endpoint": "micropub.index"},
    {"rel": "indieauth-metadata", "endpoint": "wellknown.oauth_authorization_server"},
    {"rel": "authorization_endpoint", "endpoint": "indieauth.authorization"},
    {"rel": "token_endpoint", "endpoint": "indieauth.token"},
    {"rel": "hub", "endpoint": "websub.hub"},
    {
        "rel": "alternate",
        "endpoint": "feed.json_index",
        "type": "application/feed+json",
    },
    {
        "rel": "alternate",
        "endpoint": "feed.rss_index",
        "type": "application/rss+xml",
    },
    {
        "rel": "alternate",
        "endpoint": "feed.atom_index",
        "type": "application/atom+xml",
    },
    {
        "rel": "alternate",
        "endpoint": "feed.html_index",
        "type": "text/mf2+html",
    },
]

MAX_PAGE_SIZE = 100
