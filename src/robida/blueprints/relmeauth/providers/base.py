"""
Base OAuth provider
"""

from quart import Blueprint, Response, current_app, session
from quart.helpers import redirect, url_for


class Provider:
    """
    Base class for OAuth providers.
    """

    blueprint: Blueprint
    login_endpoint: str

    @classmethod
    def match(cls, url: str) -> bool:  # pylint: disable=unused-argument
        """
        Match `rel="me"` links pointing to the provider.
        """
        return False

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

    def get_scope(self) -> dict[str, str]:
        """
        Store scope for verification.
        """
        return {}

    def login(self) -> Response:
        """
        Redirect to ASF for authentication.
        """
        return redirect(url_for(self.login_endpoint))
