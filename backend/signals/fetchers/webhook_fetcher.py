"""Webhook delivery fetcher.

Unlike source-based fetchers (API, RSS, Scraper, Social), a webhook contract
does not pull data from an external source.  Instead, once signals are stored
the acquisition pipeline pushes them to the endpoint stored in
``contract.source_url`` via :func:`backend.job_handlers.send_webhook_notification`.

This fetcher returns an empty list so that the normal store/dedup pipeline
remains a no-op for webhook contracts.  The actual outbound delivery is
triggered as a post-store step in
:meth:`backend.services.signal_acquisition.SignalAcquisitionService.fetch_contract`.
"""

import logging
from typing import Any

from backend.signals.fetchers.base import BaseFetcher, FetchError, FetchResult

logger = logging.getLogger(__name__)


class WebhookFetcher(BaseFetcher):
    """Delivery fetcher for webhook-type signal contracts.

    ``fetch()`` always returns an empty list — webhook contracts have no
    inbound data source.  Signal delivery to the configured endpoint is
    performed by the acquisition service after signals are stored.
    """

    source_type = "webhook"

    async def fetch(
        self,
        source_url: str,
        extraction_config: dict[str, Any],
    ) -> list[FetchResult] | FetchError:
        """Return an empty result list.

        Outbound delivery to *source_url* is handled by the acquisition
        service, not here.
        """
        logger.debug(
            "WebhookFetcher called for %s — no inbound data to pull; "
            "outbound delivery handled post-store",
            source_url,
        )
        return []
