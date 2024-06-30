"""
Category models.
"""

from dataclasses import dataclass


@dataclass
class CategoryRequest:
    """
    Represents a category request.
    """

    page: int = 1
    page_size: int | None = None
