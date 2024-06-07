"""
Main application.
"""

import asyncio
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from quart import Quart, g, request, url_for
from quart_schema import QuartSchema

from robida.blueprints.entries import api as entries
from robida.blueprints.homepage import api as homepage
from robida.blueprints.indieauth import api as indieauth
from robida.blueprints.media import api as media
from robida.blueprints.micropub import api as micropub
from robida.blueprints.relmeauth import api as relmeauth
from robida.blueprints.wellknown import api as wellknown
from robida.db import get_db

quart_schema = QuartSchema()


def create_app(
    test_config: dict[str, str] | None = None,
    env: str = ".env",
) -> Quart:
    """
    Initialize the app, with extensions and blueprints.
    """
    app = Quart(__name__)

    # configuration
    app.config.update(dotenv_values(env))
    if test_config:
        app.config.from_mapping(test_config)

    # extensions
    quart_schema.init_app(app)

    # blueprints
    app.register_blueprint(entries.blueprint)
    app.register_blueprint(homepage.blueprint)
    app.register_blueprint(indieauth.blueprint)
    app.register_blueprint(media.blueprint)
    app.register_blueprint(micropub.blueprint)
    app.register_blueprint(relmeauth.blueprint)
    app.register_blueprint(wellknown.blueprint)

    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    # create MEDIA directory
    if not Path(app.config["MEDIA"]).exists():
        Path(app.config["MEDIA"]).mkdir()  # pragma: no cover

    @app.before_request
    def before_request() -> None:
        """
        Store access token, if any.
        """
        authorization = request.headers.get("Authorization")

        if authorization and authorization.startswith("Bearer "):
            g.access_token = authorization.split(" ", 1)[1]
        else:
            g.access_token = None

    @app.context_processor
    def inject_config() -> dict[str, Any]:
        """
        Inject app config into all templates.
        """
        return {
            "config": app.config,
            "links": {
                rel: url_for(endpoint, _external=True)
                for rel, endpoint in homepage.rels.items()
            },
        }

    # app.config["SERVER_NAME"] = "0082-172-58-129-44.ngrok-free.app"
    # app.config["PREFER_SECURE_URLS"] = True

    return app


async def init_db(app: Quart) -> None:
    """
    Create tables.
    """
    async with get_db(app) as db:
        with open(Path(app.root_path) / "schema.sql", encoding="utf-8") as file_:
            await db.executescript(file_.read())
        await db.commit()


def init_db_sync():
    """
    Synchronous wrapper of `init_db` for Poetry.
    """
    app = create_app()
    asyncio.run(init_db(app))


def run() -> None:
    """
    Main app.
    """
    app = create_app()
    app.run("0.0.0.0", port=5001)
