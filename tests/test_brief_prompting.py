from backend.briefs.prompting import (
    build_brief_user_prompt,
    build_signal_catalog,
    coerce_canonical_brief_result,
)


SAMPLE_SIGNALS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "title": "Inflation slowed in the latest monthly print",
        "summary": "Headline CPI eased to 31.2% while food inflation stayed elevated.",
        "confidence": 0.84,
        "source_url": "https://example.com/cpi",
        "published_at": "2026-03-21T08:00:00Z",
        "similarity": 0.92,
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "title": "FX liquidity remains uneven",
        "summary": "Importers are still seeing settlement delays in some windows.",
        "confidence": 0.78,
        "source_url": "https://example.com/fx",
        "published_at": "2026-03-20T10:00:00Z",
        "similarity": 0.88,
    },
]


def test_build_brief_user_prompt_requests_canonical_schema() -> None:
    prompt = build_brief_user_prompt("Nigeria inflation outlook", SAMPLE_SIGNALS, 81)

    assert '"executive_summary"' in prompt
    assert '"signals_and_indicators"' in prompt
    assert 'SIG-1' in prompt
    assert 'SRC-1' in prompt


def test_coerce_canonical_brief_result_backfills_refs_and_signal_ids() -> None:
    raw = {
        "title": "Inflation is cooling, but risks remain",
        "metadata": {
            "category": "Market",
            "confidence_level": "High",
            "priority_level": "High",
        },
        "executive_summary": {
            "bottom_line": "Inflation is easing, but not enough to justify a fast pivot.",
            "why_it_matters": "Liquidity planning still needs caution.",
            "recommended_action": "Keep near-term liquidity plans conservative.",
            "watchpoint": "The next CPI print.",
            "insights": [
                {
                    "text": "Headline inflation is slowing.",
                    "signal_refs": [],
                    "source_refs": [],
                    "evidence_note": None,
                }
            ],
            "situation_status": "Emerging",
            "decision_required": True,
            "decision_description": "Decide whether to revise treasury assumptions.",
        },
        "key_intelligence_questions": {
            "what_is_happening": "Inflation is slowing.",
            "why_is_it_happening": "Base effects are starting to help.",
            "what_will_happen_next": "Further easing is possible over the next quarter.",
            "impact_on_organization": "Funding costs may stay tight in the near term.",
        },
        "situation_overview": {
            "topic": "Nigeria inflation outlook",
            "region_market": "Nigeria",
            "timeframe": "Short-term",
            "overview": "Disinflation is emerging, but risks remain uneven.",
        },
        "signals_and_indicators": {
            "leading_indicators": ["Monthly CPI"],
            "triggers": ["CPI below 30%"],
            "signal_evidence": [
                {
                    "signal_ref": "SIG-1",
                    "signal_title": "Inflation slowed in the latest monthly print",
                    "confidence": 0.84,
                    "contribution": "CPI eased to 31.2% in the latest release.",
                    "source_refs": [],
                }
            ],
        },
        "analysis": {
            "drivers": {"technology": [], "market": ["Base effects"], "regulatory": []},
            "patterns_detected": ["Disinflation is emerging, but food inflation remains sticky."],
            "risk_assessment": {
                "operational": None,
                "strategic": "A delayed easing cycle could constrain investment timing.",
                "technical": None,
                "market": "Volatility in FX liquidity could reverse the progress.",
            },
        },
        "impact_assessment": {
            "short_term": {
                "operations": "Financing conditions remain restrictive.",
                "infrastructure": None,
                "product_roadmap": None,
            },
            "long_term": {
                "market_position": "A slower easing cycle could delay demand recovery.",
                "innovation_strategy": None,
                "competitive_landscape": None,
            },
        },
        "recommended_actions": {
            "immediate": ["Maintain conservative liquidity assumptions."],
            "strategic": ["Revisit investment triggers after the next CPI print."],
        },
        "key_signals": [],
        "limitations": ["The evidence base is still relatively narrow."],
        "outlook": "Expect gradual easing, not a fast pivot.",
        "decision_lens": "Avoid premature balance-sheet commitments.",
        "confidence_note": "High confidence based on corroborating recent signals.",
        "domain": "macro",
        "tags": ["#Macro", "#Inflation"],
        "read_time": 5,
        "author": "AI Generated",
    }

    brief = coerce_canonical_brief_result(
        "Nigeria inflation outlook",
        raw,
        SAMPLE_SIGNALS,
        81,
    )

    assert brief["executive_summary"]["insights"][0]["signal_refs"] == ["SIG-1"]
    assert brief["executive_summary"]["insights"][0]["source_refs"] == ["SRC-1"]
    assert brief["signals_and_indicators"]["signal_evidence"][0]["source_refs"] == ["SRC-1"]
    assert brief["signal_ids"] == [signal["id"] for signal in SAMPLE_SIGNALS]
    assert build_signal_catalog(SAMPLE_SIGNALS)[0]["source_ref"] == "SRC-1"
