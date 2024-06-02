"""
Main application.
"""

import asyncio
from pathlib import Path

import aiosqlite
from dotenv import dotenv_values
from quart import Quart
from quart_schema import QuartSchema

from robida.blueprints.feed import api as feed
from robida.blueprints.homepage import api as homepage
from robida.blueprints.media import api as media
from robida.blueprints.micropub import api as micropub

quart_schema = QuartSchema()


def create_app(test_config: dict[str, str] | None = None) -> Quart:
    """
    Initialize the app, with extensions and blueprints.
    """
    app = Quart(__name__)

    # configuration
    app.config.update(dotenv_values(".env"))
    if test_config:
        app.config.from_mapping(test_config)

    # extensions
    quart_schema.init_app(app)

    # blueprints
    app.register_blueprint(feed.blueprint)
    app.register_blueprint(homepage.blueprint)
    app.register_blueprint(media.blueprint)
    app.register_blueprint(micropub.blueprint)

    return app


async def init_db(app: Quart) -> None:
    """
    Create tables.
    """
    async with aiosqlite.connect(app.config["DATABASE"]) as db:
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
    app.run(port=5001)
