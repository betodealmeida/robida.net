"""
Search-related models.
"""

from dataclasses import dataclass


@dataclass
class SearchRequest:
    """
    Represents a search request.
    """

    q: str
    page: int = 1
    page_size: int | None = None
