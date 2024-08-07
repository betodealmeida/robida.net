"""
Main application.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from nh3 import clean  # pylint: disable=no-member, no-name-in-module
from quart import Quart, Response, g, request, session, url_for
from quart_schema import QuartSchema

from robida.blueprints.auth import api as auth
from robida.blueprints.categories import api as categories
from robida.blueprints.crud import api as crud
from robida.blueprints.feed import api as feed
from robida.blueprints.homepage import api as homepage
from robida.blueprints.indieauth import api as indieauth
from robida.blueprints.media import api as media
from robida.blueprints.micropub import api as micropub
from robida.blueprints.robots import api as robots
from robida.blueprints.search import api as search
from robida.blueprints.webmention import api as webmention
from robida.blueprints.websub import api as websub
from robida.blueprints.wellknown import api as wellknown
from robida.constants import links
from robida.db import init_db, load_entries
from robida.helpers import (
    XForwardedProtoMiddleware,
    fetch_hcard,
    get_type_emoji,
    iso_to_rfc822,
    summarize,
)

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
    app.register_blueprint(auth.blueprint)
    app.register_blueprint(categories.blueprint)
    app.register_blueprint(crud.blueprint)
    app.register_blueprint(feed.blueprint)
    app.register_blueprint(homepage.blueprint)
    app.register_blueprint(indieauth.blueprint)
    app.register_blueprint(media.blueprint)
    app.register_blueprint(micropub.blueprint)
    app.register_blueprint(robots.blueprint)
    app.register_blueprint(search.blueprint)
    app.register_blueprint(webmention.blueprint)
    app.register_blueprint(websub.blueprint)
    app.register_blueprint(wellknown.blueprint)

    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.enable_async = True
    app.jinja_env.globals.update(
        {
            "fetch_hcard": fetch_hcard,
            "iso_to_rfc822": iso_to_rfc822,
            "get_type_emoji": get_type_emoji,
            "summarize": summarize,
        }
    )
    app.jinja_env.filters.update(
        {
            "summarize": summarize,
            "clean": clean,
            "json": json.dumps,
        },
    )

    # create MEDIA directory
    if not Path(app.config["MEDIA"]).exists():
        Path(app.config["MEDIA"]).mkdir()  # pragma: no cover

    @app.route("/health")
    async def health() -> dict[str, str]:
        """
        Health check.
        """
        return {
            "debug": app.config["DEBUG"] == "TRUE",
            "environment": app.config["ENVIRONMENT"],
            "testing": app.config["TESTING"] == "TRUE",
        }

    @app.before_request
    def before_request() -> None:
        """
        Store access token, if any.
        """
        authorization = request.headers.get("Authorization")

        g.access_token = (
            authorization.split(" ", 1)[1]
            if authorization and authorization.startswith("Bearer ")
            else None
        )

    @app.context_processor
    def inject_config() -> dict[str, Any]:
        """
        Inject app config (and more) into all templates.
        """
        return {"config": app.config, "session": session, "links": links}

    @app.after_request
    def add_links(response: Response) -> Response:
        """
        Add Link headers to responses.
        """
        # rel links
        response.headers.extend(
            [
                (
                    "Link",
                    f'<{url_for(link["endpoint"], _external=True)}>; rel="{link["rel"]}"',
                )
                for link in links
            ]
        )

        # no AI crawling, please
        response.headers.extend(
            [
                ("X-Robots-Tag", "noai"),
                ("X-Robots-Tag", "noimageai"),
            ]
        )

        return response

    # this is needed to run behind nginx
    app.asgi_app = XForwardedProtoMiddleware(app.asgi_app)

    return app


def init_db_sync():
    """
    Synchronous wrapper of `init_db` for Poetry.
    """
    app = create_app()
    asyncio.run(init_db(app))


def load_entries_sync() -> None:
    """
    Synchronous wrapper of `load_entries` for Poetry.
    """
    app = create_app()
    asyncio.run(load_entries(app))


def run() -> None:
    """
    Main app.
    """
    app = create_app()
    app.run("0.0.0.0", port=5001)
