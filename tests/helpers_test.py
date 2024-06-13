"""
Tests for the generic helper functions.
"""

from pytest_httpx import HTTPXMock

from robida.helpers import fetch_hcard, get_type_emoji


async def test_fetch_hcard_not_found(httpx_mock: HTTPXMock) -> None:
    """
    Test the `render_microformat` function when the h-card is not found.
    """
    httpx_mock.add_response(url="https://tantek.com/", status_code=404)

    assert await fetch_hcard("https://tantek.com/") == {
        "type": ["h-card"],
        "properties": {
            "name": ["https://tantek.com/"],
            "url": ["https://tantek.com/"],
        },
    }


async def test_get_type_emoji() -> None:
    """
    Test the `get_type_emoji` function.
    """

    assert (
        get_type_emoji({"type": ["h-entry"], "properties": {"name": ["A title"]}})
        == '<span title="An article (h-entry)">📝</span>'
    )
    assert (
        get_type_emoji({"type": ["h-entry"], "properties": {}})
        == '<span title="A note (h-entry)">🗒️</span>'
    )
    assert (
        get_type_emoji({"type": ["h-new"], "properties": {}})
        == '<span title="A generic post">📝</span>'
    )
