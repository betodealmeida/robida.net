"""
Fixtures for testing BYODB.
"""

from unittest.mock import patch

import pytest
from aiosqlite.core import Connection
from quart import Quart, testing

from robida.blueprints.indieauth.helpers import get_scopes
from robida.blueprints.wellknown.api import SCOPES_SUPPORTED
from robida.db import get_db
from robida.main import create_app, init_db


@pytest.fixture(name="current_app")
async def app(tmpdir) -> Quart:
    """
    Create and configure a new app instance for each test.
    """
    test_app = create_app(
        {
            "DATABASE": str(tmpdir.join("robida.sqlite")),
            "SERVER_NAME": "robida.net",
            "NAME": "Robida",
            "EMAIL": "robida@example.com",
        },
    )
    await init_db(test_app)

    yield test_app


@pytest.fixture
async def client(current_app: Quart) -> testing.QuartClient:
    """
    A test client for the app.
    """

    async def mock_get_scopes(token: str | None) -> set[str]:
        """
        Mock `get_scopes` to return the token as the scope.
        """
        if token in SCOPES_SUPPORTED:
            return {token}

        return await get_scopes(token)

    with patch("robida.blueprints.indieauth.helpers.get_scopes", mock_get_scopes):
        async with current_app.test_client() as test_client:
            yield test_client


@pytest.fixture
async def db(current_app: Quart) -> Connection:
    """
    A database connection for the app.
    """
    async with get_db(current_app) as test_db:
        yield test_db
