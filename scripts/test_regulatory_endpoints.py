"""Smoke test for regulatory intelligence endpoints.

This script tests the new regulatory knowledge API endpoints to ensure:
- Event creation works
- Auto-extraction from signals works
- Pattern learning works
- Predictions work
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from backend.database import async_session_maker
from backend.models.regulatory_knowledge import (
    RegulatoryEvent,
    RegulatoryPattern,
    RegulatoryRule,
)
from backend.models.signal import Signal
from backend.services.regulatory_intelligence import RegulatoryIntelligenceService


async def test_event_extraction():
    """Test auto-extraction of regulatory events from signals."""
    print("\n🔍 Test 1: Auto-extract regulatory event from signal")
    print("=" * 60)
    
    async with async_session_maker() as db:
        service = RegulatoryIntelligenceService(db)
        
        # Create test signal with CBN policy content
        test_signal = Signal(
            id=uuid4(),
            title="CBN Increases MPR to 18.5%",
            raw_content=(
                "The Central Bank of Nigeria (CBN) has announced an increase in the "
                "Monetary Policy Rate (MPR) from 17.5% to 18.5%, effective immediately. "
                "This rate adjustment is aimed at curbing inflation and stabilizing the Naira. "
                "All Deposit Money Banks (DMBs) must comply with the new rate. "
                "Deadline for compliance is March 1, 2026."
            ),
            source_url="https://cbn.gov.ng/2026/02/mpr-increase",
            source="CBN Official Statement",
            acquired_at=datetime.utcnow(),
            signal_type="news",
        )
        
        db.add(test_signal)
        await db.flush()
        
        # Extract regulatory event
        event = await service.extract_regulatory_event_from_signal(test_signal)
        
        if event:
            print(f"✅ Successfully extracted regulatory event:")
            print(f"   Event Type: {event.event_type}")
            print(f"   Issuing Body: {event.issuing_body}")
            print(f"   Title: {event.title}")
            print(f"   Severity Score: {event.severity_score:.2f}")
            print(f"   Confidence: {event.confidence_score:.2f}")
            print(f"   Affected Sectors: {', '.join(event.affected_sectors) if event.affected_sectors else 'None'}")
        else:
            print("❌ Failed to extract regulatory event")
            return False
        
        await db.commit()
        return True


async def test_signal_enrichment():
    """Test enriching a signal with regulatory context."""
    print("\n🎯 Test 2: Enrich signal with regulatory context")
    print("=" * 60)
    
    async with async_session_maker() as db:
        service = RegulatoryIntelligenceService(db)
        
        # Get a signal with regulatory content
        query = select(Signal).where(Signal.source.like("%CBN%")).limit(1)
        result = await db.execute(query)
        signal = result.scalar_one_or_none()
        
        if not signal:
            print("⚠️  No CBN signals found, creating test signal...")
            signal = Signal(
                id=uuid4(),
                title="SEC Introduces New Listing Requirements",
                raw_content=(
                    "The Securities and Exchange Commission (SEC) has published draft "
                    "regulations for new listing requirements on the Nigerian Exchange. "
                    "Public consultation period runs until March 15, 2026."
                ),
                source_url="https://sec.gov.ng/2026/02/listing-requirements",
                source="SEC Press Release",
                acquired_at=datetime.utcnow(),
                signal_type="news",
            )
            db.add(signal)
            await db.flush()
        
        # Enrich signal
        enrichment = await service.enrich_signal_with_regulatory_context(signal)
        
        print(f"✅ Enrichment completed:")
        print(f"   Has regulatory implications: {enrichment.get('has_regulatory_implications')}")
        print(f"   Issuing body: {enrichment.get('issuing_body', 'N/A')}")
        print(f"   Event type: {enrichment.get('event_type', 'N/A')}")
        print(f"   Severity: {enrichment.get('severity_score', 0):.2f}")
        print(f"   Related events: {len(enrichment.get('regulatory_events', []))}")
        print(f"   Applicable rules: {len(enrichment.get('applicable_rules', []))}")
        
        if enrichment.get("interpretation"):
            print(f"\n   Interpretation preview:")
            print(f"   {enrichment['interpretation'][:200]}...")
        
        await db.commit()
        return True


async def test_pattern_learning():
    """Test ML pattern learning from historical events."""
    print("\n🧠 Test 3: Learn patterns from historical events")
    print("=" * 60)
    
    async with async_session_maker() as db:
        service = RegulatoryIntelligenceService(db)
        
        # First, create some test events to learn from
        print("   Creating test event sequence...")
        
        test_events = [
            {
                "event_type": "regulatory_consultation",
                "title": "CBN Public Consultation on New KYC Policy",
                "issuing_body": "CBN",
                "announced_at": datetime.utcnow() - timedelta(days=90),
            },
            {
                "event_type": "policy_change",
                "title": "CBN Issues Final KYC Policy Framework",
                "issuing_body": "CBN",
                "announced_at": datetime.utcnow() - timedelta(days=60),
            },
            {
                "event_type": "enforcement_action",
                "title": "CBN Penalizes Banks for KYC Non-Compliance",
                "issuing_body": "CBN",
                "announced_at": datetime.utcnow() - timedelta(days=30),
            },
            # Repeat sequence to establish pattern
            {
                "event_type": "regulatory_consultation",
                "title": "CBN Public Consultation on Cash Reserve Ratio",
                "issuing_body": "CBN",
                "announced_at": datetime.utcnow() - timedelta(days=150),
            },
            {
                "event_type": "policy_change",
                "title": "CBN Revises CRR Requirements",
                "issuing_body": "CBN",
                "announced_at": datetime.utcnow() - timedelta(days=120),
            },
            {
                "event_type": "enforcement_action",
                "title": "CBN Sanctions Banks for CRR Violations",
                "issuing_body": "CBN",
                "announced_at": datetime.utcnow() - timedelta(days=90),
            },
        ]
        
        for event_data in test_events:
            event = RegulatoryEvent(
                id=uuid4(),
                event_type=event_data["event_type"],
                title=event_data["title"],
                description=f"Test event: {event_data['title']}",
                issuing_body=event_data["issuing_body"],
                announced_at=event_data["announced_at"],
                severity_score=0.7,
                confidence_score=0.9,
                verified_by_expert=True,
                affected_sectors=["financial_services"],
            )
            db.add(event)
        
        await db.flush()
        
        # Learn patterns
        print("   Running ML pattern learning...")
        patterns = await service.learn_patterns_from_history(
            lookback_months=12,
            min_occurrences=2,
        )
        
        await db.commit()
        
        print(f"✅ Pattern learning completed:")
        print(f"   Total patterns discovered: {len(patterns)}")
        
        for pattern in patterns[:5]:  # Show first 5
            print(f"\n   Pattern: {pattern.pattern_type}")
            print(f"   Signature: {pattern.pattern_signature}")
            print(f"   Description: {pattern.description}")
            print(f"   Confidence: {pattern.confidence_score:.2f}")
            print(f"   Occurrences: {pattern.occurrence_count}")
        
        return len(patterns) > 0


async def test_predictions():
    """Test regulatory action predictions."""
    print("\n🔮 Test 4: Predict next regulatory actions")
    print("=" * 60)
    
    async with async_session_maker() as db:
        service = RegulatoryIntelligenceService(db)
        
        # Get most recent verified event
        query = (
            select(RegulatoryEvent)
            .where(RegulatoryEvent.verified_by_expert == True)
            .order_by(RegulatoryEvent.announced_at.desc())
            .limit(1)
        )
        result = await db.execute(query)
        recent_event = result.scalar_one_or_none()
        
        if not recent_event:
            print("⚠️  No verified events found")
            return False
        
        print(f"   Base event: {recent_event.title}")
        print(f"   Event type: {recent_event.event_type}")
        print(f"   Regulator: {recent_event.issuing_body}")
        
        # Generate predictions
        predictions = await service.predict_next_regulatory_action(recent_event)
        
        if predictions:
            print(f"\n✅ Generated {len(predictions)} predictions:")
            
            for i, pred in enumerate(predictions[:3], 1):
                print(f"\n   Prediction {i}:")
                print(f"   Type: {pred['prediction_type']}")
                print(f"   Predicted event: {pred['predicted_event_type']}")
                print(f"   Regulator: {pred['predicted_regulator']}")
                print(f"   Confidence: {pred['confidence']:.2%}")
                print(f"   Rationale: {pred['rationale']}")
                
                if "expected_date" in pred:
                    print(f"   Expected: {pred['expected_date']} ({pred['days_until_expected']} days)")
        else:
            print("ℹ️  No predictions generated (may need more patterns)")
        
        return True


async def test_knowledge_stats():
    """Test knowledge base statistics."""
    print("\n📊 Test 5: Knowledge base statistics")
    print("=" * 60)
    
    async with async_session_maker() as db:
        from sqlalchemy import func
        
        # Count events
        event_count = await db.execute(select(func.count(RegulatoryEvent.id)))
        events = event_count.scalar_one()
        
        # Count patterns
        pattern_count = await db.execute(select(func.count(RegulatoryPattern.id)))
        patterns = pattern_count.scalar_one()
        
        # Count verified events
        verified_count = await db.execute(
            select(func.count(RegulatoryEvent.id))
            .where(RegulatoryEvent.verified_by_expert == True)
        )
        verified = verified_count.scalar_one()
        
        # Count rules
        rule_count = await db.execute(
            select(func.count(RegulatoryRule.id))
            .where(RegulatoryRule.is_active == True)
        )
        rules = rule_count.scalar_one()
        
        print(f"✅ Knowledge base summary:")
        print(f"   Total regulatory events: {events}")
        print(f"   Verified by experts: {verified}")
        print(f"   Learned patterns: {patterns}")
        print(f"   Active rules: {rules}")
        print(f"   Verification rate: {(verified/events*100) if events > 0 else 0:.1f}%")
        
        return True


async def main():
    """Run all smoke tests."""
    print("\n" + "=" * 60)
    print("🚀 REGULATORY INTELLIGENCE SMOKE TESTS")
    print("=" * 60)
    
    tests = [
        ("Event Extraction", test_event_extraction),
        ("Signal Enrichment", test_signal_enrichment),
        ("Pattern Learning", test_pattern_learning),
        ("Predictions", test_predictions),
        ("Knowledge Stats", test_knowledge_stats),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ {test_name} failed with error:")
            print(f"   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Regulatory intelligence system is operational.")
    else:
        print("\n⚠️  Some tests failed. Check logs above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
