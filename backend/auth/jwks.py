"""
JWKS (JSON Web Key Set) client for Auth0 public key management.

Fetches and caches Auth0's public keys for JWT signature verification.
Implements automatic refresh and error handling.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
from jose import jwk

from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class JWKSClient:
    """
    Manages Auth0 JWKS (JSON Web Key Set) for JWT signature verification.

    Features:
    - Fetches public keys from Auth0 JWKS endpoint
    - Caches keys in memory (30min TTL)
    - Auto-refresh on cache miss or expiration
    - Thread-safe (async)
    """

    def __init__(self):
        self.jwks_uri = f"https://{settings.auth0_domain}/.well-known/jwks.json"
        self._keys: dict[str, Any] = {}
        self._last_fetch: datetime | None = None
        self._cache_ttl = timedelta(minutes=30)
        self._http_client = httpx.AsyncClient(timeout=10.0)
        self._lock = asyncio.Lock()

    async def get_signing_key(self, kid: str) -> Any:
        """
        Get signing key for given key ID (kid).

        Args:
            kid: Key ID from JWT header

        Returns:
            RSA public key for signature verification

        Raises:
            ValueError: If key not found or JWKS fetch fails
        """
        # Fast path: check cache without lock
        if self._is_cache_valid() and kid in self._keys:
            logger.debug(f"JWKS cache hit for kid={kid}")
            return self._keys[kid]

        # Slow path: acquire lock, double-check, then refresh
        async with self._lock:
            # Double-check after acquiring lock (another coroutine may have refreshed)
            if self._is_cache_valid() and kid in self._keys:
                logger.debug(f"JWKS cache hit after lock for kid={kid}")
                return self._keys[kid]

            # Cache miss or expired - refresh
            logger.info("JWKS cache miss or expired, fetching from Auth0")
            await self._fetch_jwks()

        # Check again after refresh
        if kid not in self._keys:
            logger.error(f"Key ID {kid} not found in JWKS after refresh")
            raise ValueError(f"Signing key {kid} not found in JWKS")

        return self._keys[kid]

    async def _fetch_jwks(self) -> None:
        """
        Fetch JWKS from Auth0 and update cache.

        Raises:
            ValueError: If fetch fails or response invalid
        """
        try:
            logger.info(f"Fetching JWKS from {self.jwks_uri}")
            response = await self._http_client.get(self.jwks_uri)
            response.raise_for_status()

            jwks_data = response.json()
            keys = jwks_data.get("keys", [])

            if not keys:
                raise ValueError("JWKS response contains no keys")

            # Parse and cache keys
            new_keys: dict[str, Any] = {}
            for key_data in keys:
                kid = key_data.get("kid")
                if not kid:
                    logger.warning("Skipping JWKS key without kid")
                    continue

                try:
                    # Convert JWK to RSA key
                    rsa_key = jwk.construct(key_data, algorithm="RS256")
                    new_keys[kid] = rsa_key
                    logger.debug(f"Cached signing key: {kid}")
                except Exception as e:
                    logger.error(f"Failed to parse key {kid}: {e}")

            if not new_keys:
                raise ValueError("No valid keys found in JWKS")

            self._keys = new_keys
            self._last_fetch = datetime.utcnow()
            logger.info(f"JWKS cache updated with {len(new_keys)} keys")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching JWKS: {e}")
            raise ValueError(f"Failed to fetch JWKS from Auth0: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching JWKS: {e}")
            raise ValueError(f"Failed to parse JWKS: {e}")

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._last_fetch:
            return False

        age = datetime.utcnow() - self._last_fetch
        is_valid = age < self._cache_ttl

        if not is_valid:
            logger.debug(f"JWKS cache expired (age: {age.total_seconds()}s)")

        return is_valid

    async def close(self) -> None:
        """Close HTTP client"""
        await self._http_client.aclose()

    def clear_cache(self) -> None:
        """Clear cached keys (for testing)"""
        self._keys.clear()
        self._last_fetch = None
        logger.info("JWKS cache cleared")


# Global JWKS client instance
_jwks_client: JWKSClient | None = None


async def get_jwks_client() -> JWKSClient:
    """
    Get global JWKS client instance (singleton).

    Usage:
        jwks = await get_jwks_client()
        key = await jwks.get_signing_key(kid)
    """
    global _jwks_client

    if _jwks_client is None:
        _jwks_client = JWKSClient()
        logger.info("JWKS client initialized")

    return _jwks_client


async def close_jwks_client() -> None:
    """Close global JWKS client (cleanup)"""
    global _jwks_client

    if _jwks_client:
        await _jwks_client.close()
        _jwks_client = None
        logger.info("JWKS client closed")
