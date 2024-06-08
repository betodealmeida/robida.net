"""
WebSub helper functions.
"""

import asyncio
import hashlib
import hmac
import urllib.parse
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from quart import current_app
from quart.helpers import url_for

from robida.db import get_db

from .models import SubscriptionRequest


MAX_LEASE = timedelta(days=365)
DELIVERY_RETRIES = 3


async def validate_subscription(data: SubscriptionRequest) -> None:
    """
    Validates/verifies the subscription request.
    """
    if getattr(data, "hub.mode") == "subscribe":
        return await subscribe(data)

    return await unsubscribe(data)


async def subscribe(data: SubscriptionRequest) -> None:
    """
    Process subscription request.
    """
    if lease := getattr(data, "hub.lease_seconds"):
        lease = min(lease, int(MAX_LEASE.total_seconds()))
    else:
        lease = int(MAX_LEASE.total_seconds())
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=lease)
    challenge = uuid4().hex

    async with httpx.AsyncClient() as client:
        response = await client.get(
            getattr(data, "hub.callback"),
            params={
                "hub.mode": "subscribe",
                "hub.topic": getattr(data, "hub.topic"),
                "hub.challenge": challenge,
                "hub.lease_seconds": lease,
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return

        if response.content != challenge.encode():
            return

    async with get_db(current_app) as db:
        await db.execute(
            """
INSERT INTO websub_publisher (
    callback,
    topic,
    expires_at,
    secret,
    last_delivery_at
)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(callback, topic) DO UPDATE SET
    callback = EXCLUDED.callback,
    topic = EXCLUDED.topic,
    expires_at = EXCLUDED.expires_at,
    secret = EXCLUDED.secret
            """,
            (
                getattr(data, "hub.callback"),
                getattr(data, "hub.topic"),
                expires_at,
                getattr(data, "hub.secret"),
                datetime.now(timezone.utc),
            ),
        )
        await db.commit()


async def unsubscribe(data: SubscriptionRequest) -> None:
    """
    Process unsubscribe request.
    """
    challenge = uuid4().hex

    async with httpx.AsyncClient() as client:
        response = await client.get(
            getattr(data, "hub.callback"),
            params={
                "hub.mode": "unsubscribe",
                "hub.topic": getattr(data, "hub.topic"),
                "hub.challenge": challenge,
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return

        if response.content != challenge.encode():
            return

    async with get_db(current_app) as db:
        await db.execute(
            """
DELETE FROM
    websub_publisher
WHERE
    callback = ? AND
    topic = ?
            """,
            (
                getattr(data, "hub.callback"),
                getattr(data, "hub.topic"),
            ),
        )
        await db.commit()


async def distribute_content(urls: list[str]) -> None:
    """
    Broadcast URL change to subscribers.
    """
    now = datetime.now(timezone.utc)

    async with get_db(current_app) as db:
        placeholders = ", ".join("?" for _ in urls)
        async with db.execute(
            f"""
SELECT *
FROM
    websub_publisher
WHERE
    topic IN ({placeholders}) AND
    expires_at > ?
            """,
            (*urls, now),
        ) as cursor:
            rows = await cursor.fetchall()

    # use a test client to perform networkless request
    quart_client = current_app.test_client()

    transport = httpx.HTTPTransport(retries=DELIVERY_RETRIES)
    async with httpx.AsyncClient(transport=transport) as httpx_client:
        await asyncio.gather(
            *[send_to_subscriber(row, quart_client, httpx_client) for row in rows]
        )


def apply_parameters_to_url(url: str, **kwargs: list[str]) -> str:
    """
    Apply additional query parameters to a given URL.
    """
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    query_params.update(kwargs)
    query = urllib.parse.urlencode(query_params, doseq=True)

    return parsed._replace(query=query).geturl()


async def send_to_subscriber(row, quart_client, httpx_client) -> None:
    """
    Broadcast URL change to a single subscriber.
    """
    url = apply_parameters_to_url(row["topic"], since=[row["last_delivery_at"]])
    last_delivery_at = datetime.now(timezone.utc)
    response = await quart_client.get(url)
    content = await response.data
    headers = {
        "Content-Type": response.headers["Content-Type"],
        "Link": ", ".join(
            [
                f'<{url_for("websub.hub", _external=True)}>; rel="hub", '
                f'<{row["topic"]}>; rel="self"'
            ]
        ),
    }

    if row["secret"]:
        signature = hmac.new(
            row["secret"].encode(),
            content.encode(),
            hashlib.sha1,
        ).hexdigest()
        headers["X-Hub-Signature"] = f"sha1={signature}"

    await httpx_client.post(
        row["callback"],
        headers=headers,
        content=content,
    )

    # update `last_delivery_at`
    async with get_db(current_app) as db:
        await db.execute(
            """
UPDATE
    websub_publisher
SET
    last_delivery_at = ?
WHERE
    callback = ? AND
    topic = ?
            """,
            (last_delivery_at, row["callback"], row["topic"]),
        )
        await db.commit()
