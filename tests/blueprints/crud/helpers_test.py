"""
Tests for the CRUD functions.
"""

import json
from uuid import UUID

from bs4 import BeautifulSoup
from freezegun import freeze_time
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture
from quart import Quart

from robida.blueprints.crud.helpers import (
    create_hentry,
    get_author,
    get_content,
    get_metadata,
    get_title,
    get_type_properties,
    update_hentry,
)
from robida.blueprints.crud.models import ExternalSitePayload
from robida.models import Microformats2


async def test_get_metadata_with_microformats(httpx_mock: HTTPXMock) -> None:
    """
    Test the `get_metadata` function when the page uses microformats.
    """
    httpx_mock.add_response(
        url="http://example.com/",
        html="""
<article class="h-entry">
    <p class="p-content e-content">Hello, world!</p>
    <footer>
        <p>
            Published by <a class="h-card" href="http://example.com/">Beto Dealmeida</a>
            <a class="u-url" href="http://example.com/feed/1d4f24cc-8c6a-442e-8a42-bc208cb16534">
                <time class="dt-published" datetime="2024-06-30T19:02:06.057649+00:00">
                    Sun, 30 Jun 2024 19:02:06 +0000
                </time>
            </a>
            <a class="p-category" href="/category/note">note</a>
        </p>
    </footer>
</article>
        """,
    )

    data = ExternalSitePayload(url="http://example.com/")
    assert await get_metadata(data) == {
        "name": ["http://example.com/"],
        "post": {"author": ["http://example.com/"], "content": ["Hello, world!"]},
    }


async def test_get_metadata_error(httpx_mock: HTTPXMock) -> None:
    """
    Test the `get_metadata` function when the page errors.
    """
    httpx_mock.add_response(
        url="http://example.com/",
        status_code=400,
    )

    data = ExternalSitePayload(url="http://example.com/")
    assert await get_metadata(data) == {"post": {}}


async def test_get_metadata_with_title(httpx_mock: HTTPXMock) -> None:
    """
    Test the `get_metadata` function when we specify a title.
    """
    httpx_mock.add_response(
        url="http://example.com/",
        html="""
<html>
    <head>
        <meta name="title" content="Website title">
    </head>
</html>
        """,
    )

    data = ExternalSitePayload(
        url="http://example.com/",
        title="Example",
    )
    assert await get_metadata(data) == {
        "name": ["Example"],
        "post": {
            "author": ["http://example.com/"],
            "content": [
                {
                    "html": '<a href="http://example.com/">http://example.com/</a>',
                    "value": "http://example.com/",
                }
            ],
        },
    }


async def test_get_metadata_no_title(httpx_mock: HTTPXMock) -> None:
    """
    Test the `get_metadata` function when we don't specify a title.
    """
    httpx_mock.add_response(
        url="http://example.com/",
        html="""
<html>
    <head>
        <meta name="title" content="Website title">
    </head>
</html>
        """,
    )

    data = ExternalSitePayload(url="http://example.com/")
    assert await get_metadata(data) == {
        "name": ["Website title"],
        "post": {
            "author": ["http://example.com/"],
            "content": [
                {
                    "html": '<a href="http://example.com/">http://example.com/</a>',
                    "value": "http://example.com/",
                }
            ],
        },
    }


@freeze_time("2024-01-01 00:00:00")
async def test_create_article(mocker: MockerFixture, current_app: Quart) -> None:
    """
    Test the `create_article` function.
    """
    mocker.patch(
        "robida.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )

    data = {
        "template": "article",
        "title": "My test article",
        "content": "This is a *test* article\n\nTest.",
        "summary": "Just a test.",
        "category": "blog, meta",
        "visibility": "public",
        "published": "on",
    }

    async with current_app.app_context():
        hentry = await create_hentry(data)

    assert hentry == Microformats2(
        type=["h-entry"],
        value=None,
        properties={
            "author": [
                {
                    "type": ["h-card"],
                    "value": "http://example.com/",
                    "properties": {
                        "name": ["Beto Dealmeida"],
                        "url": ["http://example.com/"],
                        "photo": [
                            {
                                "alt": "This is my photo",
                                "value": "http://example.com/static/img/photo.jpg",
                            }
                        ],
                        "email": ["me@example.com"],
                        "note": ["I like turtles."],
                    },
                    "children": [],
                }
            ],
            "published": ["2024-01-01T00:00:00+00:00"],
            "updated": ["2024-01-01T00:00:00+00:00"],
            "url": ["http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"],
            "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
            "post-template": ["article"],
            "post-status": ["published"],
            "visibility": ["public"],
            "sensitive": ["false"],
            "name": ["My test article"],
            "summary": ["Just a test."],
            "content": [
                {
                    "html": "<p>This is a <em>test</em> article</p>\n<p>Test.</p>\n",
                    "value": "This is a test article\nTest.\n",
                    "data-markdown": "This is a *test* article\n\nTest.",
                }
            ],
            "category": ["blog", "meta"],
        },
        children=[],
    )


@freeze_time("2024-01-01 00:00:00")
async def test_create_generic(mocker: MockerFixture, current_app: Quart) -> None:
    """
    Test the `create_generic` function.
    """
    mocker.patch(
        "robida.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )

    data = {
        "template": "generic",
        "published": "on",
        "visibility": "public",
        "sensitive": "false",
        "properties": json.dumps({"name": ["Title"]}),
    }

    hentry = Microformats2(
        type=["h-entry"],
        properties={
            "post-status": ["draft"],
            "visibility": ["private"],
            "name": ["This is the title"],
            "summary": ["Just an article"],
            "content": [
                {"html": "<p>This is the content</p>", "value": "This is the content"}
            ],
        },
    )

    async with current_app.app_context():
        hentry = await update_hentry(hentry, data)

    assert hentry == Microformats2(
        type=["h-entry"],
        value=None,
        properties={
            "post-status": ["published"],
            "visibility": ["public"],
            "name": ["Title"],
            "summary": ["Just an article"],
            "content": [
                {"html": "<p>This is the content</p>", "value": "This is the content"}
            ],
            "post-template": ["generic"],
            "sensitive": ["false"],
        },
        children=[],
    )


@freeze_time("2024-01-01 00:00:00")
async def test_create_bookmark(mocker: MockerFixture, current_app: Quart) -> None:
    """
    Test the `create_bookmark` function.
    """
    mocker.patch(
        "robida.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    mocker.patch(
        "robida.blueprints.crud.helpers.get_metadata",
        return_value={
            "name": ["http://example.com/"],
            "post": {"author": ["http://example.com"], "content": ["Hello, world!"]},
        },
    )

    data = {
        "template": "bookmark",
        "url": "http://alice.example.com/",
        "title": "Alice's restaurant",
        "category": "blog, food",
        "visibility": "public",
        "published": "on",
    }

    async with current_app.app_context():
        hentry = await create_hentry(data)

    assert hentry == Microformats2(
        type=["h-entry"],
        value=None,
        properties={
            "author": [
                {
                    "type": ["h-card"],
                    "value": "http://example.com/",
                    "properties": {
                        "name": ["Beto Dealmeida"],
                        "url": ["http://example.com/"],
                        "photo": [
                            {
                                "alt": "This is my photo",
                                "value": "http://example.com/static/img/photo.jpg",
                            }
                        ],
                        "email": ["me@example.com"],
                        "note": ["I like turtles."],
                    },
                    "children": [],
                }
            ],
            "published": ["2024-01-01T00:00:00+00:00"],
            "updated": ["2024-01-01T00:00:00+00:00"],
            "url": ["http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"],
            "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
            "post-template": ["bookmark"],
            "post-status": ["published"],
            "visibility": ["public"],
            "sensitive": ["false"],
            "name": ["http://example.com/"],
            "summary": ["Bookmark of http://alice.example.com/"],
            "bookmark-of": [
                {
                    "type": ["h-cite"],
                    "value": "http://alice.example.com/",
                    "properties": {
                        "url": ["http://alice.example.com/"],
                        "author": ["http://example.com"],
                        "content": ["Hello, world!"],
                    },
                }
            ],
            "category": ["blog", "food"],
        },
        children=[],
    )


@freeze_time("2024-01-01 00:00:00")
async def test_create_like(mocker: MockerFixture, current_app: Quart) -> None:
    """
    Test the `create_like` function.
    """
    mocker.patch(
        "robida.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    mocker.patch(
        "robida.blueprints.crud.helpers.get_metadata",
        return_value={
            "name": ["http://example.com/"],
            "post": {"author": ["http://example.com"], "content": ["Hello, world!"]},
        },
    )

    data = {
        "template": "like",
        "url": "http://alice.example.com/",
        "title": "Alice's restaurant",
        "visibility": "public",
        "published": "on",
    }

    async with current_app.app_context():
        hentry = await create_hentry(data)

    assert hentry == Microformats2(
        type=["h-entry"],
        value=None,
        properties={
            "author": [
                {
                    "type": ["h-card"],
                    "value": "http://example.com/",
                    "properties": {
                        "name": ["Beto Dealmeida"],
                        "url": ["http://example.com/"],
                        "photo": [
                            {
                                "alt": "This is my photo",
                                "value": "http://example.com/static/img/photo.jpg",
                            }
                        ],
                        "email": ["me@example.com"],
                        "note": ["I like turtles."],
                    },
                    "children": [],
                }
            ],
            "published": ["2024-01-01T00:00:00+00:00"],
            "updated": ["2024-01-01T00:00:00+00:00"],
            "url": ["http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"],
            "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
            "post-template": ["like"],
            "post-status": ["published"],
            "visibility": ["public"],
            "sensitive": ["false"],
            "name": ["http://example.com/"],
            "summary": ["Like of http://alice.example.com/"],
            "like-of": [
                {
                    "type": ["h-cite"],
                    "value": "http://alice.example.com/",
                    "properties": {
                        "url": ["http://alice.example.com/"],
                        "author": ["http://example.com"],
                        "content": ["Hello, world!"],
                    },
                }
            ],
        },
        children=[],
    )


@freeze_time("2024-01-01 00:00:00")
async def test_create_note(mocker: MockerFixture, current_app: Quart) -> None:
    """
    Test the `create_note` function.
    """
    mocker.patch(
        "robida.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )

    data = {
        "template": "note",
        "content": "This is a *test* note.",
        "category": "blog, meta",
        "visibility": "public",
        "published": "on",
    }

    async with current_app.app_context():
        hentry = await create_hentry(data)

    assert hentry == Microformats2(
        type=["h-entry"],
        value=None,
        properties={
            "author": [
                {
                    "type": ["h-card"],
                    "value": "http://example.com/",
                    "properties": {
                        "name": ["Beto Dealmeida"],
                        "url": ["http://example.com/"],
                        "photo": [
                            {
                                "alt": "This is my photo",
                                "value": "http://example.com/static/img/photo.jpg",
                            }
                        ],
                        "email": ["me@example.com"],
                        "note": ["I like turtles."],
                    },
                    "children": [],
                }
            ],
            "published": ["2024-01-01T00:00:00+00:00"],
            "updated": ["2024-01-01T00:00:00+00:00"],
            "url": ["http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"],
            "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
            "post-template": ["note"],
            "post-status": ["published"],
            "visibility": ["public"],
            "sensitive": ["false"],
            "content": [
                {
                    "html": "<p>This is a <em>test</em> note.</p>\n",
                    "value": "This is a test note.\n",
                    "data-markdown": "This is a *test* note.",
                }
            ],
            "category": ["blog", "meta"],
        },
        children=[],
    )


def test_get_content_microformats() -> None:
    """
    Test the `get_content` function when the page has microformats.
    """
    hentries = [
        {
            "type": ["h-entry"],
            "value": None,
            "properties": {
                "name": ["Hello, world!"],
                "content": ["Hello, world!"],
            },
            "children": [],
        },
    ]
    html = "<meta name='description' content='This is a test'>"
    soup = BeautifulSoup(html, "html.parser")
    assert get_content(soup, hentries, "http://example.com/") == "Hello, world!"


def test_get_content_meta() -> None:
    """
    Test the `get_content` function when the page has `<meta>` elements.
    """
    html = "<meta name='description' content='This is a test'>"
    soup = BeautifulSoup(html, "html.parser")
    assert get_content(soup, [], "http://example.com/") == "This is a test"

    html = "<meta property='og:description' content='This is a test'>"
    soup = BeautifulSoup(html, "html.parser")
    assert get_content(soup, [], "http://example.com/") == "This is a test"

    html = "<meta name='twitter:description' content='This is a test'>"
    soup = BeautifulSoup(html, "html.parser")
    assert get_content(soup, [], "http://example.com/") == "This is a test"


def test_get_content_none() -> None:
    """
    Test the `get_content` function when the page has no metadata.
    """
    html = "Hello, world!"
    soup = BeautifulSoup(html, "html.parser")
    assert get_content(soup, [], "http://example.com/") == {
        "html": '<a href="http://example.com/">http://example.com/</a>',
        "value": "http://example.com/",
    }


def test_get_title_microformats() -> None:
    """
    Test the `get_title` function when the page has microformats.
    """
    hentries = [
        {
            "type": ["h-entry"],
            "value": None,
            "properties": {
                "name": ["Hello, world!"],
                "content": ["Hello, beautiful world!"],
            },
            "children": [],
        },
    ]
    html = "Hello, world!"
    soup = BeautifulSoup(html, "html.parser")
    assert get_title(soup, hentries, "http://example.com/") == "Hello, world!"


def test_get_title_meta() -> None:
    """
    Test the `get_title` function when the page has `<meta>` elements.
    """
    html = "<meta name='title' content='This is a test'>"
    soup = BeautifulSoup(html, "html.parser")
    assert get_title(soup, [], "http://example.com/") == "This is a test"

    html = "<meta property='og:title' content='This is a test'>"
    soup = BeautifulSoup(html, "html.parser")
    assert get_title(soup, [], "http://example.com/") == "This is a test"

    html = "<meta name='twitter:title' content='This is a test'>"
    soup = BeautifulSoup(html, "html.parser")
    assert get_title(soup, [], "http://example.com/") == "This is a test"


def test_get_title_none() -> None:
    """
    Test the `get_title` function when the page has no metadata.
    """
    html = "Hello, world!"
    soup = BeautifulSoup(html, "html.parser")
    assert get_title(soup, [], "http://example.com/") == "http://example.com/"


def test_get_title_element() -> None:
    """
    Test the `get_title` function when the page has only a `<title>` element.
    """
    html = "<title>Hello, world!</title>"
    soup = BeautifulSoup(html, "html.parser")
    assert get_title(soup, [], "http://example.com/") == "Hello, world!"


def test_get_author_microformats() -> None:
    """
    Test the `get_author` function when the page has microformats.
    """
    hentries = [
        {
            "type": ["h-entry"],
            "value": None,
            "properties": {
                "name": ["Hello, world!"],
                "content": ["Hello, world!"],
                "author": [
                    {
                        "type": ["h-card"],
                        "value": "http://example.com/",
                    },
                ],
            },
            "children": [],
        },
    ]
    hcards = [
        {
            "type": ["h-card"],
            "value": "http://example.com/",
            "properties": {
                "name": ["Beto Dealmeida"],
                "url": ["http://example.com/"],
            },
            "children": [],
        },
    ]

    # use author for hentries first, if available
    assert get_author(hentries, hcards, "http://example.com/") == {
        "type": ["h-card"],
        "value": "http://example.com/",
    }

    # otherwise use hcards
    assert get_author([], hcards, "http://example.com/") == {
        "children": [],
        "properties": {"name": ["Beto Dealmeida"], "url": ["http://example.com/"]},
        "type": ["h-card"],
        "value": "http://example.com/",
    }


def test_get_author_none() -> None:
    """
    Test the `get_author` function when the page has no metadata.
    """
    assert get_author([], [], "http://example.com/posts/1") == "http://example.com/"


async def test_update_hentry(mocker: MockerFixture, current_app: Quart) -> None:
    """
    Test the `update_hentry` function.
    """
    mocker.patch(
        "robida.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )

    data = {
        "template": "note",
        "content": "This is a *test* note.",
        "category": "blog, meta",
        "visibility": "public",
        "published": "on",
    }

    hentry = Microformats2(
        type=["h-entry"],
        properties={
            "post-status": ["draft"],
            "visibility": ["private"],
            "name": ["This is the title"],
            "summary": ["Just an article"],
            "content": [
                {"html": "<p>This is the content</p>", "value": "This is the content"}
            ],
        },
    )

    async with current_app.app_context():
        hentry = await update_hentry(hentry, data)

    assert hentry == Microformats2(
        type=["h-entry"],
        value=None,
        properties={
            "post-status": ["published"],
            "visibility": ["public"],
            "content": [
                {
                    "html": "<p>This is a <em>test</em> note.</p>\n",
                    "value": "This is a test note.\n",
                    "data-markdown": "This is a *test* note.",
                }
            ],
            "post-template": ["note"],
            "sensitive": ["false"],
            "category": ["blog", "meta"],
        },
        children=[],
    )


async def test_get_type_properties_invalid_type():
    """
    Test the `get_type_properties` function when the type is invalid.
    """
    assert await get_type_properties("invalid", {}) == {}
