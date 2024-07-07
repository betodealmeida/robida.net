"""
Helper functions for the MicroPub endpoint.
"""

from typing import Any
from werkzeug.datastructures import MultiDict


def process_form(payload: MultiDict) -> dict[str, Any]:
    """
    Convert form data to Microformats 2 properties.

    See http://microformats.org/wiki/microformats2-json.
    """
    properties = {}

    for key, value in payload.to_dict(flat=False).items():
        if key == "h":
            continue

        if key.endswith("[]"):
            key = key[:-2]

        properties[key] = value

    return properties
