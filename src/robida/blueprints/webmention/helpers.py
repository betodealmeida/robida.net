"""
WebMention helper functions.
"""

import asyncio
import logging
import re
import urllib.parse
from collections import defaultdict
from collections.abc import AsyncGenerator, Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx
import mf2py
from aiosqlite import Connection
from bs4 import BeautifulSoup
from quart import current_app
from quart.helpers import url_for

from robida.db import get_db
from robida.helpers import delete_entry, get_entry, rfc822_to_iso, upsert_entry
from robida.models import Entry, Microformats2

from .models import WebMentionStatus

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = {"http", "https"}

MODERATION_MESSAGE = (
    "The webmention was processed, but needs moderation before it can be displayed. "
    "Note that this endpoint supports the `vouch` extension to WebMention "
    "(https://indieweb.org/Vouch). If a `vouch` URL was not provided the existing "
    "webmention should be updated by posting a new webmention with the exact same "
    "`source` and `target` URLs, along with the `vouch` URL."
)


async def process_webmention(
    uuid: UUID,
    source: str,
    target: str,
    vouch: str | None = None,
) -> None:
    """
    Process an incoming webmention request.

    This function dispatches the validation to a separate task, and stores the status
    updates in the database so that the API can return them to the client.
    """
    async with get_db(current_app) as db:
        async for status, message in validate_webmention(
            db,
            uuid,
            source,
            target,
            vouch,
        ):
            await db.execute(
                """
UPDATE incoming_webmentions
SET
    status = ?,
    message = ?,
    last_modified_at = ?
WHERE
    uuid = ?;
                """,
                (
                    status,
                    message,
                    datetime.now(timezone.utc),
                    uuid.hex,
                ),
            )

            # Delete any existing entries when the webmention fails. This could happen
            # when a webmention is sent after a source has been deleted, or updated so
            # it no longer has incoming links.
            if status == WebMentionStatus.FAILURE:
                if entry := await get_entry(db, uuid):
                    await delete_entry(db, entry)

            await db.commit()


def verify_request(source: str, target: str) -> None:
    """
    Initial request verification of a webmention.

    This function does some very basic verification, namely checking if the suorce URL
    has a scheme that we understand, and if the target URL is a valid URL in the
    application.
    """
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f'Invalid scheme ("{parsed.scheme}") in source. '
            f'Must be one of: {", ".join(sorted(ALLOWED_SCHEMES))}'
        )

    if not is_url_in_app(target):
        raise ValueError(f'Target URL ("{target}") is not valid.')


async def validate_webmention(
    db: Connection,
    uuid: UUID,
    source: str,
    target: str,
    vouch: str | None = None,
) -> AsyncGenerator[tuple[WebMentionStatus, str], None]:
    """
    Webmention workflow.

    This function performs the actual validation of the webmention, and returns the
    status updates as they happen.
    """
    # This verification is already performed at the API level for an early error
    # message, but we still perform it here for the sake of consistency, in case the
    # function is called from somewhere else.
    try:
        verify_request(source, target)
    except ValueError as ex:
        yield WebMentionStatus.FAILURE, str(ex)
        return

    yield WebMentionStatus.PROCESSING, "The webmention is being processed."

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                source,
                headers={"Accept": "application/json, text/html;q=0.9, */*;q=0.8"},
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as ex:
            yield WebMentionStatus.FAILURE, f"Failed to fetch source URL: {ex}"
            return

        if not links_back(response, target):
            yield (
                WebMentionStatus.FAILURE,
                "The target URL is not mentioned in the source.",
            )
            return

        # create a proper entry for the webmention
        hentry = get_webmention_hentry(response, source, target, uuid)

        if not await is_domain_trusted(db, source) and not await is_vouch_valid(
            db,
            vouch,
            source,
        ):
            # mark the entry as private and pending moderation
            hentry.properties["visibility"] = ["private"]
            yield WebMentionStatus.PENDING_MODERATION, MODERATION_MESSAGE

        else:
            # re-send webmentions upstream
            await send_salmention(target)
            yield (
                WebMentionStatus.SUCCESS,
                "The webmention processed successfully and approved.",
            )

        await upsert_entry(db, hentry)


async def send_salmention(source: str) -> None:
    """
    Re-send webmentions when the source receives a webmention.
    """
    uuid = UUID(urllib.parse.urlparse(source).path.split("/")[-1])
    async with get_db(current_app) as db:
        if entry := await get_entry(db, uuid):
            await send_webmentions(new_entry=entry, old_entry=entry)


def get_webmention_hentry(
    response: httpx.Response,
    source: str,
    target: str,
    uuid: UUID,
) -> Microformats2:
    """
    Fetch the webmention payload from the source.

    This function tries to find a proper h-entry in the source, and falls back to a
    dummy entry if it can't find one.
    """
    hentry = Microformats2(
        type=["h-entry"],
        properties={
            "url": [source],
            "uid": [str(uuid)],
            "post-status": ["published"],
            "visibility": ["public"],
            "sensitive": ["true"],
            "content": [
                {
                    "html": f'<a rel="nofollow" href="{source}">{source}</a>',
                    "value": source,
                }
            ],
            "published": [
                (
                    rfc822_to_iso(response.headers["Last-Modified"])
                    if "Last-Modified" in response.headers
                    else datetime.now(timezone.utc).isoformat()
                )
            ],
        },
    )

    def matcher(content: str) -> bool:
        return target in content

    if "text/html" in response.headers.get("Content-Type", ""):
        parser = mf2py.Parser(response.text, url=str(response.url))

        for entry in parser.to_dict(filter_by_type="h-entry"):
            # find the h-entry that references the target URL
            if find_in_json(entry, matcher):
                hentry.properties.update(entry["properties"])

        return hentry

    # I have never seen a JSON webmention in the wild, so here I'm just assuming that
    # it would look like a Microformats2 JSON object.
    if "application/json" in response.headers.get("Content-Type", ""):
        root = response.json()
        queue = [root]
        while queue:
            element = queue.pop()

            if not isinstance(element, dict):
                break

            if element.get("type") == ["h-entry"] and find_in_json(element, matcher):
                hentry.properties.update(element.get("properties", {}))
                return hentry

            queue.extend(element.get("children", []))

    return hentry


async def is_domain_trusted(db: Connection, source: str) -> bool:
    """
    Check if a given source is from a trusted domain.
    """
    parsed = urllib.parse.urlparse(source)

    async with db.execute(
        "SELECT 1 FROM trusted_domains WHERE domain = ?;",
        (parsed.netloc,),
    ) as cursor:
        row = await cursor.fetchone()

    return row is not None


async def is_vouch_valid(db: Connection, vouch: str | None, source: str) -> bool:
    """
    Check if we can trust a vouch URL.
    """
    if vouch is None or not await is_domain_trusted(db, vouch):
        return False

    # check if source domain is actually mentioned in the vouch URL
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(vouch, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return False

        return links_back(response, source, domain_only=True)


def match_url(target: str, domain_only: bool = False) -> Callable[[str], bool]:
    """
    Helper function to find URL and domain matches.
    """
    left = urllib.parse.urlparse(target)

    def matcher(url: str) -> bool:
        """
        Check if a tag matches the URL.
        """
        right = urllib.parse.urlparse(url)
        return left.netloc == right.netloc if domain_only else left == right

    return matcher


def find_in_json(obj: dict[str, Any], test: Callable[[str], bool]) -> bool:
    """
    Traverse a JSON object testing for a match.
    """
    if isinstance(obj, dict):
        for value in obj.values():
            if test(value) or find_in_json(value, test):
                return True

    elif isinstance(obj, list):
        for value in obj:
            if test(value) or find_in_json(value, test):
                return True

    return False


def links_back(
    response: httpx.Response,
    target: str,
    domain_only: bool = False,
) -> bool:
    """
    Check if the target URL is present in the source.
    """
    if response.is_error:
        return False

    matcher = match_url(target, domain_only)
    content_type = response.headers.get("Content-Type", "<NULL>")

    if "text/html" in content_type:
        soup = BeautifulSoup(response.text, "html.parser")
        return bool(soup.find(href=matcher) or soup.find(src=matcher))

    if "application/json" in content_type:
        payload = response.json()
        return find_in_json(payload, matcher)

    if "text/plain" not in content_type:
        logger.warning(
            'Unknown content type "%s", falling back to text/plain',
            content_type,
        )

    return any(matcher(url) for url in find_urls(response.text))


def find_urls(text: str) -> list[str]:
    """
    Extract URLs from a string.
    """
    url_pattern = re.compile(
        r"http[s]?://"  # Match http:// or https://
        r"(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|"  # Domain name characters
        r"(?:%[0-9a-fA-F][0-9a-fA-F]))+"  # Percent-encoded characters
        r"(?:/[a-zA-Z0-9./?=&%-]*)?"  # Optional path and query string
        r"(?<![.,;!?()])"  # Negative lookbehind to exclude trailing punctuation
    )

    return url_pattern.findall(text)


def is_url_in_app(url: str) -> bool:
    """
    Checks if a given URL belongs to the application.

    Used to test if `target` is valid.
    """
    base_url = url_for("homepage.index", _external=True)
    if not url.startswith(base_url):
        return False

    url = url[len(base_url) :]
    if not url.startswith("/"):
        url = f"/{url}"

    adapter = current_app.url_map.bind("")
    return adapter.test(url, method="GET")


def extract_urls(data: Microformats2) -> set[str]:
    """
    Extract all URLs from a Microformats2 object.
    """
    urls = set()

    def traverse(value: Any) -> None:
        if isinstance(value, str):
            urls.update(find_urls(value))
        elif isinstance(value, dict):
            for k, v in value.items():
                if k == "url":
                    urls.update(v)
                elif k == "html":
                    soup = BeautifulSoup(v, "html.parser")
                    urls.update(element["href"] for element in soup.find_all(href=True))
                    urls.update(element["src"] for element in soup.find_all(src=True))
                else:
                    traverse(v)
        elif isinstance(value, list):
            for v in value:
                traverse(v)

    traverse(data.properties)

    return urls


async def send_webmentions(
    new_entry: Entry | None = None,
    old_entry: Entry | None = None,
) -> None:
    """
    Discover outgoing links and notify them with webmentions.
    """
    # do not send webmentions when testing
    if current_app.config["ENVIRONMENT"].lower() == "development":
        return

    # only send webmentions for entries authored by us
    me = url_for("homepage.index", _external=True)
    if (new_entry and new_entry.author != me) or (old_entry and old_entry.author != me):
        return

    targets: set[str] = set()
    source: str | None = None

    if old_entry:
        targets.update(
            target
            for target in extract_urls(old_entry.content)
            if target != old_entry.location
        )
        source = old_entry.location

    if new_entry:
        targets.update(
            target
            for target in extract_urls(new_entry.content)
            if target != new_entry.location
        )
        source = new_entry.location

    if source is None:
        return

    async with get_db(current_app) as db:
        async with httpx.AsyncClient() as client:
            await asyncio.gather(
                *[queue_webmention(db, client, source, target) for target in targets]
            )


async def find_endpoint(  # pylint: disable=too-many-return-statements
    client: httpx.AsyncClient,
    target: str,
) -> str | None:
    """
    Discover the webmention endpoint of a target.

    This function first does a `HEAD` request, to check the `Link` header. If no endoint
    is found it does a `GET` request and looks for a `link` or `a` tag in the HTML with
    the relevant `rel` attribute.
    """
    parsed = urllib.parse.urlparse(target)
    if parsed.scheme not in ALLOWED_SCHEMES:
        return None

    try:
        response = await client.head(
            target,
            headers={"User-Agent": "Webmention"},
            follow_redirects=True,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError:
        return None

    for rel, params in response.links.items():
        if rel == "webmention":
            return urllib.parse.urljoin(target, params["url"])

    if "text/html" not in response.headers.get("Content-Type", ""):
        return None

    try:
        response = await client.get(
            target,
            headers={"User-Agent": "Webmention"},
            follow_redirects=True,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in ["link", "a"]:
        link = soup.find(tag, rel="webmention", href=True)
        if link:
            return urllib.parse.urljoin(target, link["href"])

    return None


async def queue_webmention(
    db: Connection,
    client: httpx.AsyncClient,
    source: str,
    target: str,
) -> None:
    """
    Start the process of sending a webmention to a target.
    """
    uuid = uuid4()
    created_at = last_modified_at = datetime.now(timezone.utc)

    await db.execute(
        """
INSERT INTO outgoing_webmentions (
    uuid,
    source,
    target,
    vouch,
    status,
    message,
    created_at,
    last_modified_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (source, target) DO UPDATE SET
    status = excluded.status,
    message = excluded.message,
    last_modified_at = excluded.last_modified_at;
            """,
        (
            uuid.hex,
            source,
            target,
            None,
            WebMentionStatus.PROCESSING,
            "The webmention is being processed.",
            created_at,
            last_modified_at,
        ),
    )
    await db.execute(
        "INSERT OR IGNORE INTO trusted_domains (domain) VALUES (?);",
        (urllib.parse.urlparse(target).netloc,),
    )
    await db.commit()

    async for status, message, vouch in send_webmention(
        db,
        client,
        source,
        target,
    ):
        await db.execute(
            """
UPDATE outgoing_webmentions
SET
    status = ?,
    message = ?,
    vouch = ?,
    last_modified_at = ?
WHERE
    uuid = ?;
            """,
            (status, message, vouch, datetime.now(timezone.utc), uuid.hex),
        )
        await db.commit()


async def send_webmention(
    db: Connection,
    client: httpx.AsyncClient,
    source: str,
    target: str,
    vouch: str | None = None,
) -> AsyncGenerator[tuple[WebMentionStatus, str, str | None], None]:
    """
    Send a webmention to a target.

    This function handles the different status codes that can happen when trying to send
    a webmention, returning the status and messages as they happen.
    """
    endpoint = await find_endpoint(client, target)
    if endpoint is None:
        yield (
            WebMentionStatus.NO_ENDPOINT,
            "The target does not support webmentions.",
            vouch,
        )
        return

    payload = {"source": source, "target": target}
    if vouch is not None:
        payload["vouch"] = vouch

    response = await client.post(endpoint, data=payload)

    if response.status_code == 200:
        yield (
            WebMentionStatus.SUCCESS,
            "The webmention was successfully sent.",
            vouch,
        )
        return

    if response.status_code == 202:
        yield (
            WebMentionStatus.SUCCESS,
            "The webmention was accepted.",
            vouch,
        )
        return

    if response.status_code == 201:
        location = response.headers.get("Location")
        async for status, message in poll_webmention(client, location):
            yield status, message, vouch
        return

    if response.status_code == 449 and vouch is None:
        if vouch := await find_vouch(db, client, source, target):
            # try again, this time with a vouch
            async for update in send_webmention(
                db,
                client,
                source,
                target,
                vouch,
            ):
                yield update
        else:
            yield (
                WebMentionStatus.FAILURE,
                "The webmention failed and no vouch URL was found.",
                None,
            )
        return

    yield (
        WebMentionStatus.FAILURE,
        f"The webmention failed: {response.text}",
        None,  # do not store vouch if one was used
    )


async def poll_webmention(
    client: httpx.AsyncClient,
    location: str,
    retries: int = 10,
    interval: timedelta = timedelta(minutes=1),
    backoff: float = 2.0,
) -> AsyncGenerator[tuple[WebMentionStatus, str], None]:
    """
    Check a webmention status for updates.

    The default parameters give 10 tries, from 1 minute up to 8.5 hours.
    """
    yield (
        WebMentionStatus.PROCESSING,
        "The webmention is being processed.",
    )

    for retry in range(retries):
        await asyncio.sleep(interval.total_seconds() * (backoff**retry))

        response = await client.get(location)
        if response.status_code == 200:
            yield (
                WebMentionStatus.SUCCESS,
                "The webmention was successfully sent.",
            )
            return

    yield (
        WebMentionStatus.FAILURE,
        f"Gave up on checking webmention status after {retries} tries.",
    )


async def find_vouch(
    db: Connection,
    client: httpx.AsyncClient,
    source: str,
    target: str,
) -> str | None:
    """
    Find a vouch URL for a webmention.

    This function works by collecting all the incoming webmentions, and creating a set
    of their domains. Then, the target website is crawled, trying to find a link pointing
    to one of these domains, so we can use an incoming webmention as a vouch.
    """
    # Fetch all incoming links, sorted by most recent.
    async with db.execute(
        """
SELECT
    source
FROM
    incoming_webmentions
WHERE
    status = 'success'
ORDER BY last_modified_at DESC;
        """
    ) as cursor:
        rows = await cursor.fetchall()

    if not rows:
        return None

    # All the domains that link back to us, with their respective URLs.
    domains = defaultdict(list)
    for row in rows:
        domain = urllib.parse.urlparse(row["source"]).netloc
        domains[domain].append(row["source"])

    # Try to find links in `target` that point to one of the domains that link to us.
    async for external_link in crawl_website(client, target):
        domain = urllib.parse.urlparse(external_link).netloc
        if domain in domains:
            for incoming_url in domains[domain]:
                # Confirm that the link still points back to us. This might not be the
                # case if the source has been updated or deleted without sending a new
                # webmention, or even if the website no longer exists.
                response = await client.get(incoming_url)
                if links_back(response, source, domain_only=True):
                    return incoming_url

            del domains[domain]
            if not domains:
                break

    return None


async def crawl_website(  # pylint: disable=too-many-locals
    client: httpx.AsyncClient,
    target: str,
) -> AsyncGenerator[str, None]:
    """
    Crawl a website, yielding all external links.
    """
    parsed = urllib.parse.urlparse(target)
    target_root = parsed._replace(path="/").geturl()
    target_domain = parsed.netloc

    def is_internal_link(href: str) -> bool:
        parsed = urllib.parse.urlparse(href)
        return parsed.scheme == "" or parsed.netloc == target_domain

    def is_external_link(href: str) -> bool:
        parsed = urllib.parse.urlparse(href)
        return parsed.scheme != "" and parsed.netloc != target_domain

    # Now crawl the target website, trying to find a link to one of the domains.
    queue = [target_root, target]
    visited = set()
    yielded = set()
    while queue:
        page = queue.pop(0)
        if page in visited:
            continue
        visited.add(page)

        response = await client.get(page)
        content_type = response.headers.get("Content-Type", "")
        if response.is_error or "text/html" not in content_type:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup.find_all(href=is_external_link):
            url = element.attrs["href"]
            if url not in yielded:
                yield url
            yielded.add(url)

        queue.extend(
            urllib.parse.urljoin(target_root, element.attrs["href"])
            for element in soup.find_all("a", href=is_internal_link)
        )
