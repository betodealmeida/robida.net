"""
CRUD-related models.
"""

from dataclasses import dataclass


@dataclass
class TemplateRequest:
    """
    Represents a template request.
    """

    template: str


@dataclass
class GenericPayload:
    """
    Represents a generic payload from an unknown type.
    """

    properties: str


@dataclass
class ArticlePayload:
    """
    Payload from a new article.
    """

    # required
    title: str
    content: str

    # optional
    summary: str | None = None
    category: str | None = None


@dataclass
class ExternalSitePayload:
    """
    Payload from posts that reference an external site.
    """

    # required
    url: str

    # optional
    title: str | None = None


@dataclass
class BookmarkPayload(ExternalSitePayload):
    """
    Payload from a new bookmark.
    """

    # optional
    category: str | None = None


@dataclass
class LikePayload(ExternalSitePayload):
    """
    Payload from a new like.
    """


@dataclass
class NotePayload:
    """
    Payload from a new note.
    """

    # required
    content: str

    # optional
    category: str | None = None


@dataclass
class CheckinPayload:
    """
    A check-in.
    """

    coordinates: str
    name: str | None = None
    url: str | None = None
    content: str | None = None
    category: str | None = None
