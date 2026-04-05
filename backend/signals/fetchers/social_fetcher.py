"""Social Media Fetcher — fetches signals from social platform APIs.

Supports Twitter/X API and Reddit API. ~10% of signals.
Uses platform-specific auth and rate limiting.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from backend.config import get_settings
from backend.signals.fetchers.base import BaseFetcher, FetchError, FetchResult
from backend.signals.provider_presets import resolve_social_provider_config

logger = logging.getLogger(__name__)


class SocialFetcher(BaseFetcher):
    """Fetches signals from social media platform APIs.

    extraction_config schema:
    {
        "platform": "twitter",              # "twitter" or "reddit"
        "signal_type": "social",
        "auth": {
            "bearer_token": "..."            # Platform-specific auth
        },
        "params": {                          # Platform-specific query params
            "query": "fintech disruption",
            "max_results": 25
        },
        "min_engagement": 10                 # Min likes/upvotes to include
    }
    """

    source_type = "social"

    async def fetch(
        self,
        source_url: str,
        extraction_config: dict[str, Any],
    ) -> list[FetchResult] | FetchError:
        """Fetch signals from social media APIs."""
        source_url, extraction_config = resolve_social_provider_config(
            source_url, extraction_config
        )
        self.configure_timeout(extraction_config)
        platform = str(extraction_config.get("platform", "x")).strip().lower()

        if platform in {"twitter", "x"}:
            return await self._fetch_twitter(source_url, extraction_config)
        elif platform == "reddit":
            return await self._fetch_reddit(source_url, extraction_config)
        else:
            return FetchError(
                message=f"Unsupported social platform: {platform}",
                retryable=False,
            )

    async def _fetch_twitter(
        self,
        source_url: str,
        config: dict[str, Any],
    ) -> list[FetchResult] | FetchError:
        """Fetch from X API v2."""
        client = await self._get_client()
        auth = config.get("auth", {})
        bearer_token = auth.get("bearer_token", "") or get_settings().x_bearer_token
        params = dict(config.get("params", {}))
        signal_type = config.get("signal_type", "social")
        min_engagement = config.get("min_engagement", 0)

        if not bearer_token:
            return FetchError(
                message="X bearer_token not configured",
                retryable=False,
            )

        # Twitter API v2 search endpoint
        api_url = source_url or "https://api.twitter.com/2/tweets/search/recent"
        headers = {"Authorization": f"Bearer {bearer_token}"}

        # Default tweet fields for richer data
        if "tweet.fields" not in params:
            params["tweet.fields"] = "created_at,public_metrics,author_id,lang"
        if "max_results" not in params:
            params["max_results"] = 25

        try:
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            return FetchError(
                message=f"X API error: {e}",
                retryable=True,
            )

        tweets = data.get("data", [])
        results: list[FetchResult] = []

        for tweet in tweets:
            text = tweet.get("text", "")
            metrics = tweet.get("public_metrics", {})
            engagement = (
                metrics.get("like_count", 0)
                + metrics.get("retweet_count", 0)
                + metrics.get("reply_count", 0)
            )

            if engagement < min_engagement:
                continue

            published_at = self._safe_parse_date(tweet.get("created_at"))

            results.append(
                FetchResult(
                    title=text[:120] + "..." if len(text) > 120 else text,
                    content=text,
                    source_url=f"https://x.com/i/status/{tweet.get('id', '')}",
                    published_at=published_at,
                    signal_type=signal_type,
                    extracted_data={
                        "author_id": tweet.get("author_id"),
                        "engagement": engagement,
                        "likes": metrics.get("like_count", 0),
                        "retweets": metrics.get("retweet_count", 0),
                        "replies": metrics.get("reply_count", 0),
                        "lang": tweet.get("lang"),
                    },
                    metadata={
                        "source_type": "social",
                        "provider": "x",
                        "platform": "x",
                        "tweet_id": tweet.get("id"),
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )

        logger.info("Social fetcher extracted %s X posts", len(results))
        return results

    async def _fetch_reddit(
        self,
        source_url: str,
        config: dict[str, Any],
    ) -> list[FetchResult] | FetchError:
        """Fetch from Reddit JSON API (no auth required for public subreddits)."""
        client = await self._get_client()
        params = config.get("params", {})
        signal_type = config.get("signal_type", "social")
        min_engagement = config.get("min_engagement", 0)

        # Reddit JSON API — append .json to subreddit URL
        api_url = source_url
        if not api_url.endswith(".json"):
            api_url = api_url.rstrip("/") + ".json"

        if "limit" not in params:
            params["limit"] = 25

        try:
            response = await client.get(
                api_url,
                params=params,
                headers={"User-Agent": "ESIP/1.0 (Signal Intelligence)"},
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            return FetchError(
                message=f"Reddit API error: {e}",
                retryable=True,
            )

        # Reddit response structure
        posts = []
        if isinstance(data, dict) and "data" in data:
            posts = data["data"].get("children", [])
        elif isinstance(data, list) and data:
            posts = data[0].get("data", {}).get("children", [])

        results: list[FetchResult] = []

        for post_wrapper in posts:
            post = post_wrapper.get("data", {})
            if post.get("stickied"):
                continue

            title = post.get("title", "")
            content = post.get("selftext", "") or title
            score = post.get("score", 0)
            num_comments = post.get("num_comments", 0)
            engagement = score + num_comments

            if engagement < min_engagement:
                continue

            created_utc = post.get("created_utc")
            published_at = (
                datetime.fromtimestamp(created_utc, tz=timezone.utc)
                if created_utc
                else None
            )

            permalink = post.get("permalink", "")
            post_url = f"https://reddit.com{permalink}" if permalink else source_url

            # Truncate
            if len(content) > 10000:
                content = content[:10000]

            results.append(
                FetchResult(
                    title=str(title)[:500],
                    content=content,
                    source_url=post_url,
                    published_at=published_at,
                    signal_type=signal_type,
                    extracted_data={
                        "subreddit": post.get("subreddit"),
                        "author": post.get("author"),
                        "score": score,
                        "num_comments": num_comments,
                        "upvote_ratio": post.get("upvote_ratio"),
                        "domain": post.get("domain"),
                        "flair": post.get("link_flair_text"),
                    },
                    metadata={
                        "source_type": "social",
                        "platform": "reddit",
                        "post_id": post.get("id"),
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )

        logger.info(f"Reddit fetcher extracted {len(results)} posts")
        return results
