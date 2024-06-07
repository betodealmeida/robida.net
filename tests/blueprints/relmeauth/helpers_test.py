"""
Tests for the RelMeAuth helper functions.
"""

from pytest_httpx import HTTPXMock

from robida.blueprints.relmeauth.helpers import get_profiles


async def test_get_profiles(httpx_mock: HTTPXMock) -> None:
    """
    Test the `get_profiles` helper function.
    """
    httpx_mock.add_response(
        url="https://me.example.com",
        html="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Minimal HTML5</title>
</head>
<body>
    <p>Hi! You can find me on the <a rel="me" href="https://home.apache.org/phonebook.html?uid=me">Apache Software Foundation</a>, or email me at <a rel="me" href="mailto:me@example.com"/>me@example.com</a>.</p>
</body>
</html>
    """,
    )
    httpx_mock.add_response(
        url="https://home.apache.org/phonebook.html?uid=me",
        html="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Minimal HTML5</title>
</head>
<body>
    <p>My homepage: <a href="https://me.example.com">me.example.com</a></p>
</body>
</html>
    """,
    )

    assert await get_profiles("https://me.example.com") == [
        "https://home.apache.org/phonebook.html?uid=me",
        "mailto:me@example.com",
    ]


async def test_get_profiles_backlink(httpx_mock: HTTPXMock) -> None:
    """
    Test the only links that link back are returned.
    """
    httpx_mock.add_response(
        url="https://me.example.com",
        html="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Minimal HTML5</title>
</head>
<body>
    <p>Hi! You can find me on the <a rel="me" href="https://home.apache.org/phonebook.html?uid=me">Apache Software Foundation</a>, or email me at <a rel="me" href="mailto:me@example.com"/>me@example.com</a>.</p>
</body>
</html>
    """,
    )
    httpx_mock.add_response(
        url="https://home.apache.org/phonebook.html?uid=me",
        html="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Minimal HTML5</title>
</head>
<body>
    <p>Nothing to see here…</p>
</body>
</html>
    """,
    )

    assert await get_profiles("https://me.example.com") == [
        "mailto:me@example.com",
    ]
