"""
Base OAuth provider
"""

from __future__ import annotations

import httpx
from quart import Blueprint, Response, current_app, session
from quart.helpers import redirect, url_for


class Provider:
    """
    Base class for OAuth providers.
    """

    name: str
    description: str

    blueprint: Blueprint
    login_endpoint: str

    @classmethod
    # pylint: disable=unused-argument
    async def match(cls, me: str, client: httpx.AsyncClient) -> Provider | None:
        """
        Provider is represented in the URL response.
        """
        return None

    @classmethod
    def register(cls) -> None:
        """
        Register blueprint, if needed.
        """
        if cls.blueprint.name not in current_app.blueprints:
            current_app.register_blueprint(cls.blueprint)

    def __init__(self, me: str, profile: str) -> None:
        self.me = me
        self.profile = profile

        session.update(self.get_scope())
        self.register()

    def get_scope(self) -> dict[str, str | None]:
        """
        Store scope for verification.
        """
        return {}

    def login(self) -> Response:
        """
        Redirect for authentication.
        """
        return redirect(url_for(self.login_endpoint))
