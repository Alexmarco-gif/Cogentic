"""Base fetcher interface for signal acquisition.

All fetcher types (API, Scraper, RSS, Social) inherit from BaseFetcher
and implement the `fetch()` method.
"""

import hashlib
import ipaddress
import logging
import socket
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

_HOP_BY_HOP_HEADERS = {
    "connection",
    "host",
    "proxy-authorization",
    "proxy-connection",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


@dataclass
class FetchResult:
    """Normalized result from any fetcher type.

    Every fetcher returns a list of FetchResults regardless of source type.
    These are then processed through extraction and dedup before becoming Signals.
    """

    title: str
    content: str
    source_url: str
    published_at: datetime | None = None
    signal_type: str = "news"  # news, social, regulatory, financial, market, technology
    extracted_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    content_hash: str | None = None

    def __post_init__(self):
        """Compute content hash if not provided."""
        if not self.content_hash and self.content:
            self.content_hash = hashlib.sha256(
                self._normalize(self.content).encode("utf-8")
            ).hexdigest()

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize whitespace for stable hashing across sources."""
        return " ".join(text.split()).strip().lower()


@dataclass
class FetchError:
    """Error details from a failed fetch attempt."""

    message: str
    status_code: int | None = None
    retryable: bool = True


class BaseFetcher(ABC):
    """Abstract base for all signal fetchers.

    Each fetcher gets an httpx.AsyncClient for connection pooling
    and respects rate limits defined in the signal contract.
    """

    # Subclasses should set this
    source_type: str = "unknown"

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client
        self._owns_client = client is None
        self._custom_timeout: float | None = None
        self._max_redirects = 5
        self._max_response_bytes = 2_000_000

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with optional custom timeout."""
        if self._client is None:
            timeout_val = self._custom_timeout or 30.0
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(timeout_val, connect=10.0),
                follow_redirects=False,
                headers={"User-Agent": "ESIP/1.0 (Signal Intelligence Platform)"},
            )
        return self._client

    def configure_timeout(self, extraction_config: dict[str, Any]) -> None:
        """Apply per-contract timeout from extraction_config if present."""
        custom = extraction_config.get("timeout")
        if custom and isinstance(custom, (int, float)) and custom > 0:
            self._custom_timeout = float(custom)
        max_redirects = extraction_config.get("max_redirects")
        if isinstance(max_redirects, int) and 0 <= max_redirects <= 10:
            self._max_redirects = max_redirects
        max_bytes = extraction_config.get("max_response_bytes")
        if isinstance(max_bytes, int) and 1_024 <= max_bytes <= 10_000_000:
            self._max_response_bytes = max_bytes

    @staticmethod
    def _is_safe_url(url: str) -> bool:
        """Return True only for public HTTP(S) hosts."""
        try:
            parsed = urlparse(url)
        except Exception:
            return False

        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.hostname:
            return False

        try:
            infos = socket.getaddrinfo(parsed.hostname, None)
        except socket.gaierror:
            return False

        for info in infos:
            addr_str = info[4][0]
            try:
                addr = ipaddress.ip_address(addr_str)
            except ValueError:
                return False
            if any(addr in network for network in _BLOCKED_NETWORKS):
                logger.warning(
                    "SSRF blocked: %s resolved to blocked address %s",
                    url,
                    addr_str,
                )
                return False
        return True

    @staticmethod
    def _safe_headers(headers: dict[str, Any]) -> dict[str, str]:
        """Drop hop-by-hop headers and coerce remaining header values to strings."""
        safe: dict[str, str] = {}
        for key, value in headers.items():
            normalized = str(key).lower()
            if normalized in _HOP_BY_HOP_HEADERS:
                continue
            safe[str(key)] = str(value)
        return safe

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
    ) -> httpx.Response:
        """Make an HTTP request with SSRF checks on URL and every redirect."""
        if not self._is_safe_url(url):
            raise ValueError(f"URL blocked by SSRF protection: {url}")

        client = await self._get_client()
        current_url = url
        request_headers = self._safe_headers(headers or {})

        for redirect_count in range(self._max_redirects + 1):
            response = await client.request(
                method,
                current_url,
                headers=request_headers,
                params=params if redirect_count == 0 else None,
                json=json_body if redirect_count == 0 else None,
            )
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > self._max_response_bytes:
                await response.aclose()
                raise ValueError("Response exceeds configured byte limit")

            if response.is_redirect:
                if redirect_count >= self._max_redirects:
                    await response.aclose()
                    raise ValueError("Too many redirects")
                location = response.headers.get("location")
                await response.aclose()
                if not location:
                    raise ValueError("Redirect response missing Location header")
                next_url = urljoin(current_url, location)
                if not self._is_safe_url(next_url):
                    raise ValueError(f"Redirect blocked by SSRF protection: {next_url}")
                current_url = next_url
                continue

            if len(response.content) > self._max_response_bytes:
                await response.aclose()
                raise ValueError("Response exceeds configured byte limit")
            return response

        raise ValueError("Too many redirects")

    async def close(self):
        """Close owned HTTP client."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    @abstractmethod
    async def fetch(
        self,
        source_url: str,
        extraction_config: dict[str, Any],
    ) -> list[FetchResult] | FetchError:
        """Fetch signals from the source.

        Args:
            source_url: The URL to fetch from.
            extraction_config: Source-specific extraction rules
                (JSON paths, CSS selectors, API params, etc.)

        Returns:
            List of FetchResult on success, or FetchError on failure.
        """
        ...

    def _make_hash(self, content: str) -> str:
        """SHA-256 hash for deduplication (whitespace-normalized)."""
        normalized = " ".join(content.split()).strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _safe_parse_date(self, date_str: str | None) -> datetime | None:
        """Try to parse a date string, return None on failure."""
        if not date_str:
            return None
        # Try common formats
        for fmt in (
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822
            "%a, %d %b %Y %H:%M:%S GMT",
        ):
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        logger.debug(f"Could not parse date: {date_str}")
        return None
