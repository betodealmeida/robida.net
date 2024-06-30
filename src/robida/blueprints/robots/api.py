"""
Blueprint for `robots.txt`.
"""

import asyncio
from random import random
from uuid import uuid4

from quart import Blueprint, Response
from quart.helpers import url_for

blueprint = Blueprint("robots", __name__, url_prefix="/")

# from https://raw.githubusercontent.com/ai-robots-txt/ai.robots.txt/main/robots.txt
ai_bots = [
    "AdsBot-Google",
    "Amazonbot",
    "anthropic-ai",
    "Applebot-Extended",
    "Bytespider",
    "CCBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-Web",
    "cohere-ai",
    "Diffbot",
    "FacebookBot",
    "FriendlyCrawler",
    "Google-Extended",
    "GoogleOther",
    "GPTBot",
    "img2dataset",
    "omgili",
    "omgilibot",
    "peer39_crawler",
    "peer39_crawler/1.0",
    "PerplexityBot",
    "YouBot",
]


@blueprint.route("robots.txt", methods=["GET"])
async def robots() -> Response:
    """
    Serve the `robots.txt` page.
    """
    content = "\n".join(f"User-agent: {bot}" for bot in ai_bots) + "\nDisallow: /"

    return Response(content, content_type="text/plain; charset=utf-8")


@blueprint.route("secret/<secret>", methods=["GET"])
async def honeypot(secret: str) -> Response:
    """
    Honeypot for misbehaving bots.
    """
    uuid = uuid4().hex
    next_ = url_for("robots.honeypot", secret=uuid)
    await asyncio.sleep(random() * 60)

    return Response(f'from {secret} to <a href="{next_}">page {uuid}</a>')
