"""
Tests for the generic helper functions.
"""

import pytest
from pytest_httpx import HTTPXMock

from robida.helpers import (
    canonicalize_url,
    compute_challenge,
    fetch_hcard,
    get_type_emoji,
    iso_to_rfc822,
    rfc822_to_iso,
)


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
        == '<span title="An article (h-entry)">📄</span>'
    )
    assert (
        get_type_emoji(
            {
                "type": ["h-entry"],
                "properties": {
                    "in-reply-to": "http://example.com/",
                    "name": ["A title"],
                },
            }
        )
        == '<span title="A reply (h-entry)">💬</span>'
    )
    assert (
        get_type_emoji({"type": ["h-entry"], "properties": {}})
        == '<span title="A note (h-entry)">📔</span>'
    )
    assert (
        get_type_emoji({"type": ["h-new"], "properties": {}})
        == '<span title="A generic post">📝</span>'
    )


async def test_iso_to_rfc822() -> None:
    """
    Test the `iso_to_rfc822` function.
    """
    assert iso_to_rfc822("2022-01-01T00:00:00Z") == "Sat, 01 Jan 2022 00:00:00 +0000"
    assert (
        iso_to_rfc822("2022-01-01T00:00:00+00:00") == "Sat, 01 Jan 2022 00:00:00 +0000"
    )
    assert (
        iso_to_rfc822("2022-01-01T00:00:00+01:00") == "Sat, 01 Jan 2022 00:00:00 +0100"
    )


async def test_rfc822_to_iso() -> None:
    """
    Test the `rfc822_to_iso` function.
    """
    assert (
        rfc822_to_iso("Sat, 01 Jan 2022 00:00:00 +0000") == "2022-01-01T00:00:00+00:00"
    )
    assert (
        rfc822_to_iso("Sat, 01 Jan 2022 00:00:00 +0000") == "2022-01-01T00:00:00+00:00"
    )
    assert (
        rfc822_to_iso("Sat, 01 Jan 2022 00:00:00 +0100") == "2022-01-01T00:00:00+01:00"
    )


def test_canonicalize_url() -> None:
    """
    Test the `canonicalize_url` function.
    """
    assert canonicalize_url("https://example.com") == "https://example.com/"
    assert canonicalize_url("https://example.com/") == "https://example.com/"
    assert canonicalize_url("https://example.com/page") == "https://example.com/page"
    assert canonicalize_url("https://example.com/page/") == "https://example.com/page/"
    assert canonicalize_url("example.com") == "https://example.com/"
    assert canonicalize_url("example.com/page") == "https://example.com/page"
    assert canonicalize_url("example.com/page/") == "https://example.com/page/"


def test_compute_challenge() -> None:
    """
    Test the `compute_challenge` function.
    """
    assert compute_challenge("secret", "plain") == "secret"
    assert (
        compute_challenge("secret", "S256")
        == "K7gNU3sdo-OL0wNhqoVWhr3g6s1xYv72ol_pe_Unols"
    )

    with pytest.raises(ValueError) as excinfo:
        compute_challenge("secret", "unknown")
    assert str(excinfo.value) == "Invalid code challenge method"
