"""
Tests for the IndieAuth helper functions.
"""

from pytest_httpx import HTTPXMock

from robida.blueprints.indieauth.helpers import (
    ClientInfo,
    get_client_info,
    redirect_match,
    verify_code_challenge,
)


def test_direct_match() -> None:
    """
    Test the `redirect_match` helper function.
    """
    assert redirect_match("https://example.com", "https://example.com")
    assert redirect_match(
        "https://example.com:5000",
        "https://example.com:5000/some-path",
    )

    assert not redirect_match("http://example.com", "https://example.com")
    assert not redirect_match("https://example.com:443/", "https://example.com")


async def test_get_client_info(httpx_mock: HTTPXMock) -> None:
    """
    Test the `get_client_info` helper function.
    """
    httpx_mock.add_response(
        headers={"Link": '<https://example.com/redirect2>; rel="redirect_uri"'},
        html="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Minimal HTML5</title>
    <link rel="redirect_uri" href="https://example.com/redirect">
</head>
<body>
    <div class="h-app">
        <img src="/logo.png" class="u-logo">
        <a href="/" class="u-url p-name">Example App</a>
    </div>
</body>
</html>
    """,
    )

    client_info = await get_client_info("https://example.com")
    assert client_info == ClientInfo(
        name="Example App",
        url="https://example.com/",
        image="https://example.com/logo.png",
        redirect_uris={"https://example.com/redirect2", "https://example.com/redirect"},
    )


def test_verify_code_challenge() -> None:
    """
    Test the PKCE verification.
    """
    assert verify_code_challenge(
        "hjooUY_1tBlE_dBuCKGUK8XuSRrc_zNByH-roC5sIXA",
        "S256",
        "zo6yP8H9te4I0lk2Uclcry47yPbTT9jRbdnIZPdMUfazH5iD8vkNw",
    )

    assert not verify_code_challenge(
        "hjooUY_1tBlE_dBuCKGUK8XuSRrc_zNByH-roC5sIXA",
        "plain",
        "hjooUY_1tBlE_dBuCKGUK8XuSRrc_zNByH-roC5sIXA",
    )
