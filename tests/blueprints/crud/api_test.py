"""
Tests for the CRUD API.
"""

from uuid import UUID

from pytest_mock import MockerFixture
from quart import testing

from robida.models import Microformats2


async def test_new(authorized_client: testing.QuartClient) -> None:
    """
    Test the endpoint for creating new entries.
    """
    response = await authorized_client.get("/crud")

    assert response.status_code == 200


async def test_edit(
    mocker: MockerFixture,
    authorized_client: testing.QuartClient,
) -> None:
    """
    Test the endpoint for updating entries.
    """
    entry = mocker.MagicMock()
    entry.content = {
        "type": ["h-entry"],
        "properties": {
            "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
            "content": ["Hello, world!"],
        },
    }
    mocker.patch(
        "robida.blueprints.crud.api.get_entry",
        return_value=entry,
    )

    response = await authorized_client.get("/crud/92cdeabd-8278-43ad-871d-0214dcb2d12e")

    assert response.status_code == 200


async def test_edit_not_found(
    mocker: MockerFixture,
    authorized_client: testing.QuartClient,
) -> None:
    """
    Test the endpoint for updating entries when the entry is not found.
    """
    mocker.patch(
        "robida.blueprints.crud.api.get_entry",
        return_value=None,
    )

    response = await authorized_client.get("/crud/92cdeabd-8278-43ad-871d-0214dcb2d12e")

    assert response.status_code == 404


async def test_delete(
    mocker: MockerFixture,
    authorized_client: testing.QuartClient,
) -> None:
    """
    Test the endpoint for deleting entries.
    """
    entry = mocker.MagicMock()
    entry.content = {
        "type": ["h-entry"],
        "properties": {
            "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
            "content": ["Hello, world!"],
        },
    }
    mocker.patch(
        "robida.blueprints.crud.api.get_entry",
        return_value=entry,
    )
    mocker.patch("robida.blueprints.crud.api.delete_entry")

    response = await authorized_client.delete(
        "/crud/92cdeabd-8278-43ad-871d-0214dcb2d12e"
    )

    assert response.status_code == 200


async def test_delete_not_found(
    mocker: MockerFixture,
    authorized_client: testing.QuartClient,
) -> None:
    """
    Test the endpoint for deleting entries when the entry is not found.
    """
    mocker.patch(
        "robida.blueprints.crud.api.get_entry",
        return_value=None,
    )
    mocker.patch("robida.blueprints.crud.api.delete_entry")

    response = await authorized_client.delete(
        "/crud/92cdeabd-8278-43ad-871d-0214dcb2d12e"
    )

    assert response.status_code == 404


async def test_submit(
    mocker: MockerFixture,
    authorized_client: testing.QuartClient,
) -> None:
    """
    Test the endpoint for submitting new entries.
    """
    mocker.patch("robida.helpers.dispatcher")
    mocker.patch(
        "robida.helpers.uuid4",
        return_value=UUID("92cdeabd-8278-43ad-871d-0214dcb2d12e"),
    )
    mocker.patch(
        "robida.blueprints.crud.api.create_hentry",
        return_value=Microformats2(
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
                "published": ["2024-07-04T14:48:25.499453+00:00"],
                "updated": ["2024-07-04T14:48:25.499453+00:00"],
                "url": ["http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                "name": ["The Beatles Recording Reference Manuals"],
                "summary": [
                    "Bookmark of https://beatlesrecordingreferencemanuals.com/"
                ],
                "bookmark-of": [
                    {
                        "type": ["h-cite"],
                        "value": "https://beatlesrecordingreferencemanuals.com/",
                        "properties": {
                            "url": ["https://beatlesrecordingreferencemanuals.com/"],
                            "author": ["https://beatlesrecordingreferencemanuals.com/"],
                            "content": [
                                (
                                    "From first take to final remix, discover the making "
                                    "of the greatest pop recordings of all time in this "
                                    "best-selling series by author Jerry Hammack."
                                ),
                            ],
                        },
                    }
                ],
            },
            children=[],
        ),
    )

    response = await authorized_client.post(
        "/crud",
        form={
            "template": "bookmark",
            "url": "https://beatlesrecordingreferencemanuals.com/",
            "title": "",
            "category": "",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"


async def test_submit_update(
    mocker: MockerFixture,
    authorized_client: testing.QuartClient,
) -> None:
    """
    Test the endpoint for submitting updated entries.
    """
    mocker.patch("robida.helpers.dispatcher")
    entry = mocker.MagicMock()
    entry.content = {
        "type": ["h-entry"],
        "properties": {
            "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
            "content": ["Hello, world!"],
        },
    }
    mocker.patch("robida.blueprints.crud.api.get_entry", return_value=entry)
    mocker.patch(
        "robida.blueprints.crud.api.update_hentry",
        return_value=Microformats2(
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
                "published": ["2024-07-04T14:48:25.499453+00:00"],
                "updated": ["2024-07-04T14:48:25.499453+00:00"],
                "url": ["http://example.com/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                "uid": ["92cdeabd-8278-43ad-871d-0214dcb2d12e"],
                "name": ["The Beatles Recording Reference Manuals"],
                "summary": [
                    "Bookmark of https://beatlesrecordingreferencemanuals.com/"
                ],
                "bookmark-of": [
                    {
                        "type": ["h-cite"],
                        "value": "https://beatlesrecordingreferencemanuals.com/",
                        "properties": {
                            "url": ["https://beatlesrecordingreferencemanuals.com/"],
                            "author": ["https://beatlesrecordingreferencemanuals.com/"],
                            "content": [
                                (
                                    "From first take to final remix, discover the making "
                                    "of the greatest pop recordings of all time in this "
                                    "best-selling series by author Jerry Hammack."
                                ),
                            ],
                        },
                    }
                ],
            },
            children=[],
        ),
    )

    response = await authorized_client.post(
        "/crud",
        form={
            "template": "bookmark",
            "uuid": "92cdeabd-8278-43ad-871d-0214dcb2d12e",
            "url": "https://beatlesrecordingreferencemanuals.com/",
            "title": "",
            "category": "",
            "visibility": "public",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/feed/92cdeabd-8278-43ad-871d-0214dcb2d12e"


async def test_submit_update_not_found(
    mocker: MockerFixture,
    authorized_client: testing.QuartClient,
) -> None:
    """
    Test the endpoint for submitting updated entries when the entry is not found.
    """
    mocker.patch("robida.helpers.dispatcher")
    mocker.patch("robida.blueprints.crud.api.get_entry", return_value=None)

    response = await authorized_client.post(
        "/crud",
        form={
            "template": "bookmark",
            "uuid": "92cdeabd-8278-43ad-871d-0214dcb2d12e",
            "url": "https://beatlesrecordingreferencemanuals.com/",
            "title": "",
            "category": "",
            "visibility": "public",
        },
    )

    assert response.status_code == 404


async def test_template(client: testing.QuartClient) -> None:
    """
    Test the endpoint for creating new entries.
    """
    response = await client.get("/crud/template", query_string={"template": "note"})

    assert response.status_code == 200
    assert (
        await response.data
        == b"""<fieldset>
    <label>
        Note
        <input
            name="content"
            placeholder="Penny for your thoughts"
            tabindex="1"
            required
            autofocus
        />
        <small><a href="https://www.markdownguide.org/" tabindex="4">Markdown</a> supported.</small>
    </label>
    <label>
        Categories
        <input
            name="category"
            placeholder="foo, bar"
            tabindex="2"
        />
        <small>Comma separated list.</small>
    </label>
</fieldset>
<input type="submit" value="Create" tabindex="3"/>"""
    )
