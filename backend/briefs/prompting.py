"""Prompt-building and canonical coercion helpers for intelligence briefs.

These helpers are intentionally pure-Python so the brief generation contract
can be tested without the database, SQLAlchemy, or the OpenAI client.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from backend.briefs.schema import normalize_brief_body


def _source_name(signal: dict[str, Any], index: int) -> str:
    source_url = signal.get("source_url")
    if isinstance(source_url, str) and source_url.strip():
        host = urlparse(source_url).netloc.replace("www.", "").strip()
        if host:
            return host
    title = signal.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return f"Source {index + 1}"


def build_signal_catalog(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create stable signal/source references for prompting and post-processing."""

    catalog: list[dict[str, Any]] = []
    for index, signal in enumerate(signals):
        confidence = signal.get("confidence")
        if isinstance(confidence, (int, float)):
            confidence_value = float(confidence)
            confidence_pct = round(confidence_value * 100 if confidence_value <= 1 else confidence_value)
        else:
            confidence_pct = 0

        catalog.append(
            {
                "signal_id": str(signal.get("id", "")),
                "signal_ref": f"SIG-{index + 1}",
                "source_ref": f"SRC-{index + 1}",
                "title": signal.get("title") or f"Signal {index + 1}",
                "summary": signal.get("summary") or "",
                "source_name": _source_name(signal, index),
                "source_url": signal.get("source_url") or "",
                "published_at": signal.get("published_at") or "",
                "confidence_pct": confidence_pct,
            }
        )
    return catalog


def build_brief_system_prompt() -> str:
    return (
        "You are a senior intelligence analyst. "
        "Return ONLY valid JSON with the exact schema requested. "
        "Ground every claim in the provided signals only. "
        "Do not invent sources, citations, or metrics not present in the evidence. "
        "Write for both an executive reader and an analyst reader using precise, direct language."
    )


def build_brief_user_prompt(
    topic: str,
    signals: list[dict[str, Any]],
    avg_confidence: int,
) -> str:
    catalog = build_signal_catalog(signals)
    signal_blocks = []
    for item in catalog:
        block = (
            f"[{item['signal_ref']}] {item['title']}\n"
            f"Signal ID: {item['signal_id']}\n"
            f"Source Ref: {item['source_ref']}\n"
            f"Source Name: {item['source_name']}\n"
            f"Source URL: {item['source_url']}\n"
            f"Published: {item['published_at']}\n"
            f"Confidence: {item['confidence_pct']}%\n"
            f"Summary: {item['summary'][:500]}"
        )
        signal_blocks.append(block)

    signal_context = "\n---\n".join(signal_blocks)

    return f"""Produce a structured intelligence brief on the following topic using the signals below.

Topic: {topic}

Signals ({len(catalog)} retrieved):
{signal_context}

Return a JSON object with exactly these keys and nested shapes:

{{
  "title": "Analytical headline, max 15 words",
  "metadata": {{
    "category": "Strategic | Operational | Market | Threat | Technical | Competitive",
    "confidence_level": "Low | Medium | High | Verified",
    "priority_level": "Low | Medium | High | Critical"
  }},
  "executive_summary": {{
    "bottom_line": "2-4 sentence stand-alone summary for decision-makers",
    "why_it_matters": "One sentence on why this matters now",
    "recommended_action": "One clear immediate action",
    "watchpoint": "One signal or threshold that could change the view",
    "insights": [
      {{
        "text": "One evidence-backed claim",
        "signal_refs": ["SIG-1"],
        "source_refs": ["SRC-1"],
        "evidence_note": "Short factual support with metrics where available"
      }}
    ],
    "situation_status": "Emerging | Stable | Escalating | Declining | Improving",
    "decision_required": true,
    "decision_description": "Short statement of the decision required, or null"
  }},
  "key_intelligence_questions": {{
    "what_is_happening": "Direct answer",
    "why_is_it_happening": "Direct answer",
    "what_will_happen_next": "Direct answer with timeline",
    "impact_on_organization": "Direct answer"
  }},
  "situation_overview": {{
    "topic": "{topic}",
    "region_market": "Region, market, or null",
    "timeframe": "Immediate | Short-term | Long-term",
    "overview": "Context paragraph"
  }},
  "signals_and_indicators": {{
    "leading_indicators": ["Specific indicator"],
    "triggers": ["Concrete confirm/disconfirm threshold"],
    "signal_evidence": [
      {{
        "signal_ref": "SIG-1",
        "signal_title": "Signal title",
        "confidence": 0.84,
        "contribution": "How this signal supports the brief",
        "source_refs": ["SRC-1"]
      }}
    ]
  }},
  "analysis": {{
    "drivers": {{
      "technology": ["Driver"],
      "market": ["Driver"],
      "regulatory": ["Driver"]
    }},
    "patterns_detected": ["Pattern"],
    "risk_assessment": {{
      "operational": "Risk or null",
      "strategic": "Risk or null",
      "technical": "Risk or null",
      "market": "Risk or null"
    }}
  }},
  "impact_assessment": {{
    "short_term": {{
      "operations": "Impact or null",
      "infrastructure": "Impact or null",
      "product_roadmap": "Impact or null"
    }},
    "long_term": {{
      "market_position": "Impact or null",
      "innovation_strategy": "Impact or null",
      "competitive_landscape": "Impact or null"
    }}
  }},
  "recommended_actions": {{
    "immediate": ["Action"],
    "strategic": ["Action"]
  }},
  "key_signals": ["Top signal summary"],
  "limitations": ["Evidence gap or constraint"],
  "outlook": "30-90 day view",
  "decision_lens": "What a stakeholder should do with this analysis",
  "confidence_note": "Plain-language explanation of confidence",
  "domain": "Readable domain label",
  "tags": ["#tag"],
  "read_time": 5,
  "author": "AI Generated"
}}

Rules:
- Use only the provided signal refs and source refs. Do not invent new refs.
- Every claim in executive_summary.insights must include at least one signal_ref.
- Every signal_evidence item must include the matching signal_ref and source_refs.
- Executive content must be concise, stand-alone, persuasive, and solution-oriented.
- Analyst content must be precise, comprehensive, readable, and explicit about metrics, risks, and limitations.
- Use straightforward language, not jargon-heavy prose.
- Keep confidence aligned with the evidence quality. The average retrieved-signal confidence is {avg_confidence}%.
"""


def coerce_canonical_brief_result(
    topic: str,
    result: dict[str, Any],
    signals: list[dict[str, Any]],
    avg_confidence: int,
) -> dict[str, Any]:
    """Normalize and backfill model output into the canonical brief contract."""

    catalog = build_signal_catalog(signals)
    normalized = normalize_brief_body(
        result,
        topic=topic,
        summary=result.get("executive_summary", {}).get("bottom_line")
        if isinstance(result.get("executive_summary"), dict)
        else result.get("bluf") or result.get("summary"),
        domain=result.get("domain"),
        confidence=result.get("confidence", avg_confidence),
        outlook=result.get("outlook"),
        decision_lens=result.get("decision_lens"),
    )

    catalog_by_signal_ref = {item["signal_ref"]: item for item in catalog}

    evidence_items = normalized["signals_and_indicators"]["signal_evidence"]
    for index, item in enumerate(evidence_items):
        fallback = catalog[index] if index < len(catalog) else None
        signal_ref = item.get("signal_ref") or (fallback["signal_ref"] if fallback else f"SIG-{index + 1}")
        source_refs = item.get("source_refs") or []
        if not source_refs and fallback:
            source_refs = [fallback["source_ref"]]

        matched = catalog_by_signal_ref.get(signal_ref) or fallback
        item["signal_ref"] = signal_ref
        item["signal_title"] = item.get("signal_title") or (matched["title"] if matched else signal_ref)
        item["source_refs"] = source_refs

        confidence = item.get("confidence")
        if not isinstance(confidence, (int, float)) and matched:
            item["confidence"] = matched["confidence_pct"] / 100 if matched["confidence_pct"] else avg_confidence / 100

    for index, claim in enumerate(normalized["executive_summary"]["insights"]):
        fallback = evidence_items[index] if index < len(evidence_items) else (catalog[index] if index < len(catalog) else None)
        signal_refs = claim.get("signal_refs") or []
        if not signal_refs and fallback:
            signal_ref = fallback["signal_ref"] if isinstance(fallback, dict) else fallback.get("signal_ref")
            signal_refs = [signal_ref] if signal_ref else [f"SIG-{index + 1}"]

        source_refs = claim.get("source_refs") or []
        if not source_refs and fallback:
            if isinstance(fallback, dict) and fallback.get("source_refs"):
                source_refs = list(fallback["source_refs"])
            elif isinstance(fallback, dict) and fallback.get("source_ref"):
                source_refs = [fallback["source_ref"]]

        claim["signal_refs"] = signal_refs
        claim["source_refs"] = source_refs

        if not claim.get("evidence_note") and index < len(evidence_items):
            claim["evidence_note"] = evidence_items[index].get("contribution")

    if not normalized["key_signals"]:
        normalized["key_signals"] = [
            claim["text"] for claim in normalized["executive_summary"]["insights"][:3] if claim.get("text")
        ]

    normalized["title"] = result.get("title") or topic
    normalized["confidence"] = avg_confidence
    normalized["signal_ids"] = [item["signal_id"] for item in catalog if item["signal_id"]]
    return normalized
