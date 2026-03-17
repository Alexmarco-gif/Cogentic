#!/usr/bin/env python3
"""Test AI brief generation pipeline.

Connects to the database, checks for signals, and generates a brief
via the new synthesize_brief() method.

Run:
    python -m backend.scripts.test_ai_brief_generation
"""

import asyncio
import json
import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.synthesis import SynthesisService
from backend.database import AsyncSessionLocal
from backend.models.signal import Signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def count_signals(db: AsyncSession) -> int:
    """Count available signals in the database."""
    result = await db.execute(select(func.count(Signal.id)))
    return result.scalar() or 0


async def main():
    """Main test flow."""
    logger.info("=" * 70)
    logger.info("AI BRIEF GENERATION PIPELINE TEST")
    logger.info("=" * 70)

    async with AsyncSessionLocal() as db:
        # 1. Check signal availability
        signal_count = await count_signals(db)
        logger.info(f"\n📊 Signal Inventory: {signal_count} signals in database")

        if signal_count < 3:
            logger.warning(
                "⚠️  Not enough signals (<3) for reliable synthesis.\n"
                "   Seed some signals first: python -m backend.scripts.seed_nigeria_contracts"
            )
            return

        # 2. Initialize synthesis service
        logger.info("\n🔍 Initializing SynthesisService...")
        synthesis = SynthesisService(db)

        # 3. Test queries (NGA-focused)
        test_queries = [
            "How is Nigeria's central bank managing monetary policy?",
            "What is affecting Nigeria's foreign exchange market?",
            "What are Nigeria's key agricultural challenges?",
        ]

        for i, query in enumerate(test_queries, 1):
            logger.info(f"\n{'─' * 70}")
            logger.info(f"Test {i}: {query}")
            logger.info(f"{'─' * 70}")

            try:
                result = await synthesis.synthesize_brief(
                    topic=query,
                    top_k=5,
                    min_confidence=0.60,
                )

                # Validate schema
                required_keys = [
                    "title",
                    "bluf",
                    "findings",
                    "indicators",
                    "outlook",
                    "decision_lens",
                    "domain",
                    "tags",
                    "confidence",
                    "read_time",
                    "citations",
                ]
                missing = [k for k in required_keys if k not in result]

                if missing:
                    logger.error(f"❌ Missing schema keys: {missing}")
                    continue

                logger.info("✅ Schema valid — all required keys present")

                # Pretty-print the brief
                logger.info(f"\n📝 Generated Brief:\n")
                logger.info(f"  Title:      {result['title']}")
                logger.info(f"  BLUF:       {result['bluf'][:80]}...")
                logger.info(f"  Domain:     {result['domain']}")
                logger.info(f"  Confidence: {result['confidence']:.0f}%")
                logger.info(f"  Read Time:  {result['read_time']} min")

                # Findings
                findings = result.get("findings", [])
                logger.info(f"\n  📌 Findings ({len(findings)}):")
                for j, f in enumerate(findings, 1):
                    logger.info(f"     {j}. {f.get('finding', 'N/A')[:60]}...")
                    if f.get("evidence"):
                        logger.info(f"        Evidence: {len(f['evidence'])} sources")
                    if f.get("objection"):
                        logger.info(f"        Objection: {f['objection'][:50]}...")

                # Indicators
                indicators = result.get("indicators", [])
                logger.info(f"\n  📊 Indicators to Watch ({len(indicators)}):")
                for j, ind in enumerate(indicators, 1):
                    logger.info(f"     {j}. {ind.get('watch', 'N/A')[:60]}...")
                    logger.info(
                        f"        ✓ Confirms if: {ind.get('confirms_if', 'N/A')[:40]}..."
                    )
                    logger.info(
                        f"        ✗ Disconfirms if: {ind.get('disconfirms_if', 'N/A')[:40]}..."
                    )

                # Citations
                cites = result.get("citations", [])
                logger.info(f"\n  📚 Citations ({len(cites)}): {', '.join(cites[:2])}")

                # Full JSON output option
                if i == 1:
                    logger.info(f"\n  📄 Full JSON (first brief):")
                    logger.info(json.dumps(result, indent=2))

            except Exception as e:
                logger.error(f"❌ Synthesis failed: {e}", exc_info=True)

    logger.info(f"\n{'=' * 70}")
    logger.info("Test complete — check results above")
    logger.info(f"{'=' * 70}\n")


if __name__ == "__main__":
    asyncio.run(main())
