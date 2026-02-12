"""RSS/Atom Feed Fetcher — parses RSS and Atom feeds.

~15% of signals come from RSS feeds (news feeds, blog feeds,
government updates, press releases).
"""

import logging
from datetime import datetime, timezone
from time import mktime
from typing import Any

import feedparser

from backend.signals.fetchers.base import BaseFetcher, FetchError, FetchResult

logger = logging.getLogger(__name__)


class RSSFetcher(BaseFetcher):
    """Fetches and parses RSS/Atom feeds.

    extraction_config schema:
    {
        "signal_type": "news",              # Signal classification
        "max_items": 50,                    # Max items to return per fetch
        "content_field": "summary",         # "summary" or "content" for body
        "extra_tags": ["category", "author"]  # Extra fields to extract
    }
    """

    source_type = "rss"

    async def fetch(
        self,
        source_url: str,
        extraction_config: dict[str, Any],
    ) -> list[FetchResult] | FetchError:
        """Fetch and parse an RSS/Atom feed."""
        self.configure_timeout(extraction_config)
        client = await self._get_client()
        max_retries = extraction_config.get("retries", 2)
        last_error: FetchError | None = None

        for attempt in range(max_retries):
            try:
                response = await client.get(source_url)
                response.raise_for_status()
                raw_content = response.text
                break
            except Exception as e:
                last_error = FetchError(
                    message=f"Failed to fetch RSS feed {source_url} (attempt {attempt + 1}): {e}",
                    retryable=True,
                )
                if attempt < max_retries - 1:
                    import asyncio

                    await asyncio.sleep(2**attempt)
        else:
            return last_error or FetchError(
                message=f"RSS fetch failed: {source_url}", retryable=True
            )

        # Parse with feedparser (sync, but fast for parsed content)
        try:
            feed = feedparser.parse(raw_content)
        except Exception as e:
            return FetchError(
                message=f"Failed to parse RSS feed {source_url}: {e}",
                retryable=False,
            )

        if feed.bozo and not feed.entries:
            return FetchError(
                message=f"Malformed RSS feed {source_url}: {feed.bozo_exception}",
                retryable=False,
            )

        return self._parse_entries(feed, extraction_config, source_url)

    def _parse_entries(
        self,
        feed: Any,
        config: dict[str, Any],
        source_url: str,
    ) -> list[FetchResult]:
        """Parse feed entries into FetchResults."""
        signal_type = config.get("signal_type", "news")
        max_items = config.get("max_items", 50)
        content_field = config.get("content_field", "summary")
        extra_tags = config.get("extra_tags", [])

        feed_title = str(
            getattr(feed.feed, "title", "Unknown Feed")
            if hasattr(feed, "feed")
            else "Unknown Feed"
        )  # type: ignore[union-attr]
        results: list[FetchResult] = []

        entries = list(feed.entries[:max_items]) if hasattr(feed, "entries") else []  # type: ignore[index]

        for entry in entries:
            title = str(getattr(entry, "title", "") or "")
            link = str(getattr(entry, "link", source_url) or source_url)

            # Get content — try configured field, then fallback
            content = ""
            if (
                content_field == "content"
                and hasattr(entry, "content")
                and entry.content
            ):
                # Atom content is a list of dicts
                content_list = entry.content
                if isinstance(content_list, list) and content_list:
                    content = str(content_list[0].get("value", ""))
            if not content:
                content = str(
                    getattr(entry, "summary", "")
                    or getattr(entry, "description", "")
                    or ""
                )

            # Strip HTML tags for cleaner text (lightweight)
            content = self._strip_html(content)

            if not title and not content:
                continue

            # Parse publish date
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published_at = datetime.fromtimestamp(
                        mktime(entry.published_parsed),
                        tz=timezone.utc,  # type: ignore[arg-type]
                    )
                except (ValueError, OverflowError):
                    pub_str = str(getattr(entry, "published", "") or "")
                    published_at = self._safe_parse_date(pub_str) if pub_str else None
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                try:
                    published_at = datetime.fromtimestamp(
                        mktime(entry.updated_parsed),
                        tz=timezone.utc,  # type: ignore[arg-type]
                    )
                except (ValueError, OverflowError):
                    pass

            # Extract extra fields
            extracted: dict[str, Any] = {"feed_title": feed_title}
            for tag in extra_tags:
                value = getattr(entry, tag, None)
                if value:
                    extracted[tag] = value
            # Categories/tags
            if hasattr(entry, "tags") and entry.tags:
                extracted["categories"] = [
                    t.get("term", "") for t in entry.tags if t.get("term")
                ]

            # Truncate
            if len(content) > 10000:
                content = content[:10000]

            results.append(
                FetchResult(
                    title=str(title)[:500],
                    content=content,
                    source_url=str(link),
                    published_at=published_at,
                    signal_type=signal_type,
                    extracted_data=extracted,
                    metadata={
                        "source_type": "rss",
                        "feed_url": source_url,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )

        logger.info(f"RSS fetcher extracted {len(results)} entries from {source_url}")
        return results

    @staticmethod
    def _strip_html(text: str) -> str:
        """Lightweight HTML tag stripping without external dependencies."""
        import re

        clean = re.sub(r"<[^>]+>", " ", text)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean
