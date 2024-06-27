"""
Base OAuth provider
"""

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
    def match(cls, response: httpx.Response) -> bool:  # pylint: disable=unused-argument
        """
        Provider is present in the URL response.
        """
        return False

    @classmethod
    def register(cls) -> None:
        """
        Register blueprint, if needed.
        """
        if cls.blueprint.name not in current_app.blueprints:
            current_app.register_blueprint(cls.blueprint)

    def __init__(self, me: str, response: httpx.Response) -> None:
        self.me = me
        self.response = response

        session.update(self.get_scope())
        self.register()

    def get_scope(self) -> dict[str, str]:
        """
        Store scope for verification.
        """
        return {}

    def login(self) -> Response:
        """
        Redirect for authentication.
        """
        return redirect(url_for(self.login_endpoint))
