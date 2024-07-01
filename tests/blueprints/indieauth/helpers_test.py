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
        url="https://example.com",
        name="Example App",
        logo="https://example.com/logo.png",
        summary=None,
        author=None,
        redirect_uris={"https://example.com/redirect2", "https://example.com/redirect"},
    )


async def test_get_client_info_with_summary_and_hcard(httpx_mock: HTTPXMock) -> None:
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
    <div class="h-app h-x-app">
        <link class="u-url" href="https://github.com/betodealmeida/robida.net/" />

        <div class="p-author h-card">
            <link rel="canonical" class="u-url" href="http://localhost:5001/"/>
            <img src="/static/img/photo.jpg" class="u-photo" alt="Photo of a male presenting white person, with shoulder-length hair and a beard. They are wearing a red t-shirt where the word &#34;TEAM&#34; can be read, and an open grey hoodie. The background is blurred, but the blue sky can be seen, as well as an umbrella."/>
            <p>My name is <strong><span class="p-name">Beto Dealmeida</strong></span> <a rel="me" class="u-email" href="mailto:contact@robida.net">📧</a>. <span class="p-note">I'm a <a rel="me" href="https://thefishermenandthepriestess.com/">musician</a> 🎸 and an <a rel="me" href="https://home.apache.org/phonebook.html?uid=beto">Apache PMC member</a>, passionate about <a href="https://www.vegansociety.com/go-vegan/definition-veganism">veganism</a>, <a href="https://www.gnu.org/software/">free software</a>, and the <a href="https://indieweb.org/">IndieWeb</a>.</span></p>
        </div>

        <img class="u-logo" src="/static/img/robida.svg" alt="rob⋯ida"/>
        <p class="p-summary">This is my <mark>very minimal website</mark>, <strong><span class="p-name">rob⋯ida</span></strong>. You can see my <a href="/feed.html">latest posts</a> (also available as <a href="/feed.rss">RSS 2.0</a>, <a href="/feed.xml">Atom</a>, <a href="/feed.json">JSON Feed</a>, or <a href="https://www.w3.org/TR/websub/">WebSub</a>). You can leave a comment by posting a <a href="https://www.w3.org/TR/webmention/">WebMention</a> or using the form at the bottom of ach post.</p>
    </div>
</body>
</html>
    """,
    )

    client_info = await get_client_info("https://example.com")
    assert client_info == ClientInfo(
        url="https://example.com",
        name="rob⋯ida",
        logo="https://example.com/static/img/robida.svg",
        summary=(
            "This is my very minimal website, rob⋯ida. You can see my latest posts (also "
            "available as RSS 2.0, Atom, JSON Feed, or WebSub). You can leave a comment "
            "by posting a WebMention or using the form at the bottom of ach post."
        ),
        author="Beto Dealmeida",
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
