"""
Helper functions for the MicroPub endpoint.
"""

from typing import Any
from werkzeug.datastructures import MultiDict

from robida.models import Microformats2


def process_form(payload: MultiDict) -> Microformats2:
    """
    Convert form data to Microformats 2 JSON.

    See http://microformats.org/wiki/microformats2-json.
    """
    data: dict[str, Any] = {
        "type": [f'h-{payload["h"]}'],
        "properties": {},
    }
    for key, value in payload.to_dict(flat=False).items():
        if key == "h":
            continue

        if key.endswith("[]"):
            key = key[:-2]

        data["properties"][key] = value

    return Microformats2(**data)
