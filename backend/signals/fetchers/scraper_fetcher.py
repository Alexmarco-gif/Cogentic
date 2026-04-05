"""Web Scraper Fetcher — scrapes structured data from web pages.

Uses httpx + selectolax for fast HTML parsing. ~35% of signals
come from web scraping (company sites, press releases, job boards).
"""

import ipaddress
import logging
import socket
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from selectolax.parser import HTMLParser

from backend.signals.fetchers.base import BaseFetcher, FetchError, FetchResult
from backend.signals.provider_presets import resolve_scraper_provider_config

logger = logging.getLogger(__name__)

# Private / link-local / loopback networks that must never be fetched
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # AWS/GCP/Azure metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_safe_url(url: str) -> bool:
    """Return True only if the URL is safe to fetch (public HTTPS hostname)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    # Resolve the hostname and check every returned address
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False

    for info in infos:
        addr_str = info[4][0]
        try:
            addr = ipaddress.ip_address(addr_str)
        except ValueError:
            return False
        for net in _BLOCKED_NETWORKS:
            if addr in net:
                logger.warning(
                    "SSRF blocked: %s resolved to private address %s", url, addr_str
                )
                return False

    return True


class ScraperFetcher(BaseFetcher):
    """Scrapes structured data from web pages using CSS selectors.

    extraction_config schema:
    {
        "signal_type": "market",
        "item_selector": "article.post",      # CSS selector for each item
        "title_selector": "h2.title",          # CSS selector for title within item
        "content_selector": "div.body",        # CSS selector for content
        "url_selector": "a.link",              # CSS selector for link (href attribute)
        "url_attribute": "href",               # Attribute to get URL from
        "date_selector": "time.published",     # CSS selector for date
        "date_attribute": "datetime",          # Attribute for date value
        "extra_selectors": {                   # Additional fields to extract
            "author": "span.author",
            "category": "span.category"
        },
        "pagination": {                        # Optional pagination
            "next_selector": "a.next",
            "max_pages": 3
        }
    }
    """

    source_type = "scraper"

    async def fetch(
        self,
        source_url: str,
        extraction_config: dict[str, Any],
    ) -> list[FetchResult] | FetchError:
        """Fetch and parse web page(s) using CSS selectors."""
        source_url, extraction_config = resolve_scraper_provider_config(
            source_url, extraction_config
        )
        if not _is_safe_url(source_url):
            return FetchError(
                message=f"URL blocked by SSRF protection: {source_url}",
                retryable=False,
            )
        self.configure_timeout(extraction_config)
        client = await self._get_client()
        all_results: list[FetchResult] = []
        max_retries = extraction_config.get("retries", 2)
        request_headers = extraction_config.get("headers", {})

        # Pagination support
        pagination = extraction_config.get("pagination", {})
        max_pages = pagination.get("max_pages", 1)
        next_selector = pagination.get("next_selector")

        current_url = source_url

        for page in range(max_pages):
            response_text: str | None = None
            for attempt in range(max_retries):
                try:
                    response = await client.get(current_url, headers=request_headers)
                    response.raise_for_status()
                    response_text = response.text
                    break
                except httpx.TimeoutException:
                    if attempt < max_retries - 1:
                        import asyncio

                        await asyncio.sleep(2**attempt)
                        continue
                    if page == 0:
                        return FetchError(
                            message=f"Timeout scraping {current_url} after {max_retries} attempts",
                            retryable=True,
                        )
                    break
                except httpx.HTTPStatusError as e:
                    if page == 0:
                        retryable = e.response.status_code >= 500
                        return FetchError(
                            message=f"HTTP {e.response.status_code} scraping {current_url}",
                            status_code=e.response.status_code,
                            retryable=retryable,
                        )
                    break
                except Exception as e:
                    if page == 0 and attempt == max_retries - 1:
                        return FetchError(
                            message=f"Error scraping {current_url}: {e}",
                            retryable=True,
                        )
                    if attempt < max_retries - 1:
                        import asyncio

                        await asyncio.sleep(2**attempt)
                        continue
                    break

            if response_text is None:
                break

            html_content = response_text

            # Parse HTML
            page_results = self._parse_html(
                html_content, extraction_config, current_url
            )
            all_results.extend(page_results)

            # Check for next page
            if not next_selector or page >= max_pages - 1:
                break

            tree = HTMLParser(html_content)
            next_node = tree.css_first(next_selector)
            if next_node and next_node.attributes.get("href"):
                next_href = next_node.attributes["href"]
                # Handle relative URLs
                if next_href.startswith("/"):
                    from urllib.parse import urlparse

                    parsed = urlparse(current_url)
                    current_url = f"{parsed.scheme}://{parsed.netloc}{next_href}"
                elif next_href.startswith("http"):
                    if not _is_safe_url(next_href):
                        logger.warning("SSRF blocked on pagination URL %s", next_href)
                        break
                    current_url = next_href
                else:
                    break
            else:
                break

        logger.info(
            f"Scraper fetcher extracted {len(all_results)} items from {source_url}"
        )
        return all_results

    def _parse_html(
        self,
        html: str,
        config: dict[str, Any],
        page_url: str,
    ) -> list[FetchResult]:
        """Parse HTML page into FetchResults using CSS selectors."""
        tree = HTMLParser(html)

        signal_type = config.get("signal_type", "market")
        provider = config.get("provider", "generic")
        item_selector = config.get("item_selector", "article")
        title_selector = config.get("title_selector", "h2")
        content_selector = config.get("content_selector", "p")
        url_selector = config.get("url_selector", "a")
        url_attribute = config.get("url_attribute", "href")
        date_selector = config.get("date_selector")
        date_attribute = config.get("date_attribute", "datetime")
        extra_selectors = config.get("extra_selectors", {})

        items = tree.css(item_selector)
        results: list[FetchResult] = []

        for item in items:
            # Title
            title_node = item.css_first(title_selector)
            title = title_node.text(strip=True) if title_node else ""

            # Content
            content_node = item.css_first(content_selector)
            content = content_node.text(strip=True) if content_node else ""

            if not title and not content:
                continue

            # URL
            url_node = item.css_first(url_selector)
            item_url = page_url
            if url_node:
                href = url_node.attributes.get(url_attribute, "")
                if href:
                    if href.startswith("http"):
                        item_url = href
                    elif href.startswith("/"):
                        from urllib.parse import urlparse

                        parsed = urlparse(page_url)
                        item_url = f"{parsed.scheme}://{parsed.netloc}{href}"

            # Date
            published_at = None
            if date_selector:
                date_node = item.css_first(date_selector)
                if date_node:
                    date_str = date_node.attributes.get(
                        date_attribute
                    ) or date_node.text(strip=True)
                    published_at = self._safe_parse_date(date_str)

            # Extra fields
            extracted: dict[str, Any] = {}
            for field_name, selector in extra_selectors.items():
                node = item.css_first(selector)
                if node:
                    extracted[field_name] = node.text(strip=True)

            # Truncate
            if len(content) > 10000:
                content = content[:10000]

            results.append(
                FetchResult(
                    title=str(title)[:500],
                    content=content,
                    source_url=item_url,
                    published_at=published_at,
                    signal_type=signal_type,
                    extracted_data=extracted,
                    metadata={
                        "source_type": "scraper",
                        "provider": provider,
                        "page_url": page_url,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )

        return results
