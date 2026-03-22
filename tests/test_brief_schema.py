from backend.briefs.generator import BriefGenerator
from backend.briefs.schema import normalize_brief_body


def test_normalize_brief_body_maps_legacy_shape() -> None:
    payload = {
        "bluf": "Policy tightening is slowing, but inflation risk remains elevated.",
        "findings": [
            {
                "finding": "The inflation trend is easing.",
                "evidence": ["CPI slowed to 31.2% in the latest print."],
                "rebuttal": "Food inflation is still sticky.",
            }
        ],
        "indicators": [
            {
                "watch": "Next CPI release",
                "confirms_if": "Below 30%",
                "disconfirms_if": "Above 33%",
            }
        ],
        "decision_lens": "Prepare for a slower but still restrictive policy path.",
        "domain": "macro",
        "confidence": 82,
    }

    brief = normalize_brief_body(payload, topic="Nigeria inflation outlook")

    assert brief["metadata"]["confidence_level"] == "High"
    assert brief["executive_summary"]["bottom_line"] == payload["bluf"]
    assert brief["executive_summary"]["insights"][0]["signal_refs"] == ["SIG-1"]
    assert brief["signals_and_indicators"]["signal_evidence"][0]["signal_ref"] == "SIG-1"
    assert brief["recommended_actions"]["immediate"]


def test_normalize_brief_body_keeps_canonical_shape() -> None:
    payload = {
        "metadata": {
            "category": "Strategic",
            "confidence_level": "Verified",
            "priority_level": "Critical",
        },
        "executive_summary": {
            "bottom_line": "Demand is reaccelerating in the target market.",
            "why_it_matters": "This shifts the investment case.",
            "recommended_action": "Increase coverage now.",
            "watchpoint": "A sudden reversal in weekly orders.",
            "insights": [
                {
                    "text": "Weekly demand is climbing.",
                    "signal_refs": ["SIG-2"],
                    "source_refs": [],
                    "evidence_note": "Orders rose 18% week on week.",
                }
            ],
            "situation_status": "Escalating",
            "decision_required": True,
            "decision_description": "Decide whether to expand inventory.",
        },
        "key_intelligence_questions": {
            "what_is_happening": "Demand is rising.",
            "why_is_it_happening": "Competitor stock-outs are redirecting orders.",
            "what_will_happen_next": "Further short-term acceleration is likely.",
            "impact_on_organization": "Missed revenue if stock stays constrained.",
        },
        "domain": "market",
        "tags": ["#Demand"],
    }

    brief = normalize_brief_body(payload, topic="Demand surge")

    assert brief["metadata"]["priority_level"] == "Critical"
    assert brief["executive_summary"]["insights"][0]["signal_refs"] == ["SIG-2"]
    assert brief["domain"] == "market"
    assert brief["tags"] == ["#Demand"]


def test_brief_generator_maps_to_canonical_body() -> None:
    generator = BriefGenerator(db=None)  # type: ignore[arg-type]

    mapped = generator._map_synthesis_result(
        "Nigeria inflation outlook",
        {
            "title": "Inflation is cooling, but policy remains tight",
            "bluf": "Inflation is easing, but not enough to justify a quick policy pivot.",
            "findings": [
                {
                    "finding": "Inflation is easing.",
                    "evidence": ["CPI slowed again."],
                }
            ],
            "indicators": [],
            "outlook": "Expect a slower path to rate cuts.",
            "decision_lens": "Protect near-term liquidity plans.",
            "domain": "macro",
            "confidence": 84,
        },
    )

    body_json = mapped["body_json"]
    assert mapped["bluf"] == body_json["executive_summary"]["bottom_line"]
    assert body_json["signals_and_indicators"]["signal_evidence"][0]["signal_ref"] == "SIG-1"
    assert mapped["decision_lens"] == body_json["decision_lens"]
