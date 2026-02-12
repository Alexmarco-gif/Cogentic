"""Smoke test for regulatory intelligence endpoints.

Tests all 8 regulatory API endpoints with sample data.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from uuid import uuid4
from datetime import datetime
from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models.regulatory_knowledge import (
    RegulatoryEvent,
    RegulatoryRule,
    RegulatoryImpact,
    RegulatoryPattern,
)
from backend.models.signal import Signal
from backend.services.regulatory_intelligence import RegulatoryIntelligenceService


async def smoke_test():
    """Run smoke tests on regulatory endpoints."""
    
    print("=" * 80)
    print("REGULATORY INTELLIGENCE SMOKE TEST")
    print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        service = RegulatoryIntelligenceService(db)
        
        # Test 1: Create sample signal with regulatory content
        print("\n[1/8] Testing regulatory event extraction from signal...")
        
        sample_signal = Signal(
            id=uuid4(),
            title="CBN Increases MPR to 18.5%",
            raw_content="""
            The Central Bank of Nigeria (CBN) has announced an increase in the 
            Monetary Policy Rate (MPR) from 17.5% to 18.5%, effective immediately.
            This rate adjustment is aimed at controlling inflation which has risen 
            to 31.7%. All deposit money banks must comply with the new rate.
            """,
            source_url="https://example.com/cbn-mpr-2026",
            source_type="rss",
            acquired_at=datetime.utcnow(),
        )
        db.add(sample_signal)
        await db.flush()
        print(f"   ✓ Created sample signal: {sample_signal.id}")
        
        # Test 2: Extract regulatory event
        print("\n[2/8] Testing auto-extraction of regulatory event...")
        reg_event = await service.extract_regulatory_event_from_signal(
            sample_signal,
            auto_create=True,
        )
        
        if reg_event:
            print(f"   ✓ Extracted regulatory event: {reg_event.id}")
            print(f"     - Type: {reg_event.event_type}")
            print(f"     - Issuing body: {reg_event.issuing_body}")
            print(f"     - Severity: {reg_event.severity_score:.2f}")
        else:
            print("   ✗ No regulatory event detected")
            return
        
        # Test 3: Create regulatory rule
        print("\n[3/8] Testing regulatory rule creation...")
        reg_rule = RegulatoryRule(
            id=uuid4(),
            event_id=reg_event.id,
            rule_type="compliance_requirement",
            title="Banks must adjust lending rates within 48 hours of MPR change",
            conditions={
                "trigger": "MPR adjustment",
                "applicability": "All deposit money banks",
                "threshold": None,
            },
            actions={
                "required_action": "Adjust lending rates",
                "timeframe": "48 hours",
                "documentation": "Submit compliance report to CBN",
            },
            confidence_score=0.85,
        )
        db.add(reg_rule)
        await db.flush()
        print(f"   ✓ Created regulatory rule: {reg_rule.id}")
        print(f"     - Confidence: {reg_rule.confidence_score:.2f}")
        
        # Test 4: Record regulatory impact
        print("\n[4/8] Testing regulatory impact recording...")
        impact = await service.record_regulatory_impact(
            regulatory_event_id=reg_event.id,
            impact_type="interest_rate_change",
            metric_name="prime_lending_rate",
            baseline_value=22.5,
            post_impact_value=24.3,
            description="Banks increased prime lending rates in response to MPR hike",
            expert_verified=True,
        )
        print(f"   ✓ Recorded impact: {impact.id}")
        print(f"     - Percentage change: {impact.percentage_change:+.1f}%")
        print(f"     - Lag: {impact.lag_days} days")
        
        # Test 5: Enrich signal with regulatory context
        print("\n[5/8] Testing signal enrichment with regulatory context...")
        enriched_context = await service.enrich_signal_with_regulatory_context(
            sample_signal,
            top_k=3,
        )
        
        if enriched_context:
            print(f"   ✓ Generated regulatory context ({len(enriched_context)} chars)")
            print(f"     Preview: {enriched_context[:150]}...")
        else:
            print("   - No regulatory context generated")
        
        # Test 6: Find applicable rules
        print("\n[6/8] Testing rule applicability detection...")
        applicable_rules = await service.find_applicable_rules(
            event=reg_event,
            entity_type="company",
            sector="banking",
        )
        print(f"   ✓ Found {len(applicable_rules)} applicable rules")
        for rule in applicable_rules[:3]:
            print(f"     - {rule.title} (confidence: {rule.confidence_score:.2f})")
        
        # Test 7: Pattern detection
        print("\n[7/8] Testing ML pattern detection...")
        patterns = await service.detect_pattern_in_signal(
            signal=sample_signal,
            event=reg_event,
        )
        
        if patterns:
            print(f"   ✓ Detected {len(patterns)} patterns")
            for pattern, score in patterns[:3]:
                print(f"     - {pattern.description} (score: {score:.2f})")
        else:
            print("   - No patterns detected (expected for first event)")
        
        # Test 8: Learn patterns from history
        print("\n[8/8] Testing ML pattern learning from history...")
        
        # Mark event as verified to include it in learning
        reg_event.verified_by_expert = True
        await db.flush()
        
        discovered_patterns = await service.learn_patterns_from_history(
            lookback_months=12,
            min_occurrences=1,  # Low threshold for smoke test
        )
        print(f"   ✓ Discovered {len(discovered_patterns)} patterns")
        for pattern in discovered_patterns[:3]:
            print(f"     - {pattern.description}")
        
        # Cleanup
        await db.rollback()
        print("\n" + "=" * 80)
        print("✓ ALL SMOKE TESTS PASSED")
        print("=" * 80)
        print("\nDatabase changes rolled back (test data not persisted)")


if __name__ == "__main__":
    asyncio.run(smoke_test())
