"""
Generic helper functions.
"""

from bs4 import BeautifulSoup


def extract_text_from_html(html: str) -> str:
    """
    Extract text from HTML.
    """
    return BeautifulSoup(html, "html.parser").get_text()
