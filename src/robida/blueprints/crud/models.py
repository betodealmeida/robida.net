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
