"""
Tests for the RelMeAuth API.
"""

from bs4 import BeautifulSoup
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture
from quart import testing


async def test_login(client: testing.QuartClient) -> None:
    """
    Test the login page.

    Not much here.
    """
    response = await client.get("/login")
    soup = BeautifulSoup(await response.data, "html.parser")

    assert response.status_code == 200
    assert soup.find("input", {"name": "me"})


async def test_logout(mocker: MockerFixture, client: testing.QuartClient) -> None:
    """
    Test the logout page.

    Not much here.
    """
    session = {"me": "https://me.example.com"}
    mocker.patch("robida.blueprints.auth.api.session", new=session)

    response = await client.get("/logout")

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert session == {}


async def test_submit(client: testing.QuartClient, httpx_mock: HTTPXMock) -> None:
    """
    Test the submit page.
    """
    httpx_mock.add_response(
        url="https://me.example.com/",
        html="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Minimal HTML5</title>
</head>
<body>
    <p>Hi! You can email me at <a rel="me" href="mailto:me@example.com"/>me@example.com</a>.</p>
</body>
</html>
    """,
    )

    response = await client.post("/login", form={"me": "https://me.example.com"})

    assert response.status_code == 302
    assert response.headers["Location"] == "/relmeauth/email/login"


async def test_submit_no_provider(
    client: testing.QuartClient, httpx_mock: HTTPXMock
) -> None:
    """
    Test the submit page when no provider is found.
    """
    httpx_mock.add_response(
        url="https://me.example.com/",
        html="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Minimal HTML5</title>
</head>
<body>
    <p>Hi! You can email me at <a href="mailto:me@example.com"/>me@example.com</a>.</p>
</body>
</html>
    """,
    )

    response = await client.post("/login", form={"me": "https://me.example.com"})

    assert response.status_code == 400
    assert await response.data == b"No provider found"
