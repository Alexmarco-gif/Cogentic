"""Canonical intelligence brief schema helpers.

The signal drawer UI is the source of truth for brief structure. This module
normalizes AI outputs and legacy brief bodies into that canonical schema so the
backend can persist one shape while older records remain readable.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_BRIEF_BODY: dict[str, Any] = {
    "metadata": {
        "category": "Strategic",
        "confidence_level": "Low",
        "priority_level": "Low",
    },
    "executive_summary": {
        "bottom_line": None,
        "why_it_matters": None,
        "recommended_action": None,
        "watchpoint": None,
        "insights": [],
        "situation_status": "Emerging",
        "decision_required": False,
        "decision_description": None,
    },
    "key_intelligence_questions": {
        "what_is_happening": None,
        "why_is_it_happening": None,
        "what_will_happen_next": None,
        "impact_on_organization": None,
    },
    "situation_overview": {
        "topic": None,
        "region_market": None,
        "timeframe": "Short-term",
        "overview": None,
    },
    "signals_and_indicators": {
        "leading_indicators": [],
        "triggers": [],
        "signal_evidence": [],
    },
    "analysis": {
        "drivers": {
            "technology": [],
            "market": [],
            "regulatory": [],
        },
        "patterns_detected": [],
        "risk_assessment": {
            "operational": None,
            "strategic": None,
            "technical": None,
            "market": None,
        },
    },
    "impact_assessment": {
        "short_term": {
            "operations": None,
            "infrastructure": None,
            "product_roadmap": None,
        },
        "long_term": {
            "market_position": None,
            "innovation_strategy": None,
            "competitive_landscape": None,
        },
    },
    "recommended_actions": {
        "immediate": [],
        "strategic": [],
    },
    "key_signals": [],
    "limitations": [],
    "outlook": None,
    "decision_lens": None,
    "confidence_note": None,
    "domain": None,
    "tags": [],
    "read_time": 5,
    "author": "AI Generated",
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_str(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return None


def _as_bool(value: Any) -> bool:
    return bool(value)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_str_list(value: Any) -> list[str]:
    return [item.strip() for item in _as_list(value) if isinstance(item, str) and item.strip()]


def _as_confidence(value: Any, fallback: float = 0.75) -> float:
    if not isinstance(value, (int, float)):
        return fallback
    if value > 1:
        value = value / 100
    return max(0.0, min(float(value), 1.0))


def _first_sentence(value: str | None) -> str | None:
    if not value:
        return None
    for token in [". ", "! ", "? "]:
        if token in value:
            return value.split(token, 1)[0].strip() + token.strip()
    return value.strip()


def _sentences(value: str | None) -> list[str]:
    if not value:
        return []
    text = value.replace("!", ".").replace("?", ".")
    return [part.strip() for part in text.split(".") if part.strip()]


def _confidence_level(score: float) -> str:
    if score >= 0.92:
        return "Verified"
    if score >= 0.80:
        return "High"
    if score >= 0.65:
        return "Medium"
    return "Low"


def _priority_level(score: float) -> str:
    if score >= 0.90:
        return "Critical"
    if score >= 0.80:
        return "High"
    if score >= 0.65:
        return "Medium"
    return "Low"


def _category_from_domain(domain: str | None) -> str:
    normalized = (domain or "").lower()
    if any(token in normalized for token in ("market", "finance", "macro")):
        return "Market"
    if any(token in normalized for token in ("regulatory", "policy", "threat")):
        return "Threat"
    if any(token in normalized for token in ("technology", "tech")):
        return "Technical"
    if any(token in normalized for token in ("operations", "supply")):
        return "Operational"
    if "competitive" in normalized:
        return "Competitive"
    return "Strategic"


def build_confidence_note(score: float, evidence_count: int = 0) -> str:
    level = _confidence_level(score)
    if level == "Verified":
        if evidence_count >= 3:
            return "Verified confidence from corroborating evidence across multiple recent signals."
        return "Verified confidence, though the evidence base is still relatively narrow."
    if level == "High":
        if evidence_count >= 3:
            return "High confidence based on corroborating recent signals."
        return "High confidence, but this view still leans on a concentrated evidence set."
    if level == "Medium":
        return "Medium confidence: the pattern is credible, but there are still open variables to watch."
    return "Low confidence: treat this as an early signal until more evidence arrives."


def _looks_canonical(payload: dict[str, Any]) -> bool:
    return (
        isinstance(payload.get("metadata"), dict)
        and isinstance(payload.get("executive_summary"), dict)
        and isinstance(payload.get("key_intelligence_questions"), dict)
    )


def _normalize_claim(item: Any, index: int) -> dict[str, Any] | None:
    if isinstance(item, str):
        text = _as_str(item)
        if not text:
            return None
        return {
            "text": text,
            "signal_refs": [f"SIG-{index + 1}"],
            "source_refs": [],
            "evidence_note": None,
        }

    if not isinstance(item, dict):
        return None

    text = _as_str(item.get("text")) or _as_str(item.get("claim")) or _as_str(
        item.get("statement")
    )
    if not text:
        return None

    return {
        "text": text,
        "signal_refs": _as_str_list(item.get("signal_refs")) or [f"SIG-{index + 1}"],
        "source_refs": _as_str_list(item.get("source_refs")),
        "evidence_note": _as_str(item.get("evidence_note")),
    }


def _normalize_signal_evidence(
    item: Any,
    index: int,
    fallback_confidence: float,
) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    signal_ref = _as_str(item.get("signal_ref")) or f"SIG-{index + 1}"
    signal_title = (
        _as_str(item.get("signal_title"))
        or _as_str(item.get("title"))
        or signal_ref
    )
    contribution = (
        _as_str(item.get("contribution"))
        or _as_str(item.get("summary"))
        or _first_sentence(_as_str(item.get("evidence_note")))
        or "Contributes supporting context to the brief."
    )

    return {
        "signal_ref": signal_ref,
        "signal_title": signal_title,
        "confidence": _as_confidence(item.get("confidence"), fallback_confidence),
        "contribution": contribution,
        "source_refs": _as_str_list(item.get("source_refs")),
    }


def _legacy_to_canonical(
    payload: dict[str, Any],
    *,
    topic: str,
    summary: str | None = None,
    domain: str | None = None,
    confidence: float | None = None,
    outlook: str | None = None,
    decision_lens: str | None = None,
) -> dict[str, Any]:
    score = _as_confidence(payload.get("confidence"), confidence or 0.75)
    findings = [item for item in _as_list(payload.get("findings")) if isinstance(item, dict)]
    indicators = [
        item for item in _as_list(payload.get("indicators")) if isinstance(item, dict)
    ]
    bluf = _as_str(payload.get("bluf")) or summary
    outlook_value = _as_str(payload.get("outlook")) or outlook
    decision_value = _as_str(payload.get("decision_lens")) or decision_lens
    domain_value = _as_str(payload.get("domain")) or domain
    decision_sentences = _sentences(decision_value)

    claims: list[dict[str, Any]] = []
    signal_evidence: list[dict[str, Any]] = []

    for index, finding in enumerate(findings):
        evidence_points = _as_str_list(finding.get("evidence"))
        signal_ref = _as_str_list(finding.get("signal_refs"))[:1] or [f"SIG-{index + 1}"]
        claims.append(
            {
                "text": _as_str(finding.get("finding")) or f"Finding {index + 1}",
                "signal_refs": _as_str_list(finding.get("signal_refs")) or signal_ref,
                "source_refs": _as_str_list(finding.get("source_refs")),
                "evidence_note": evidence_points[0] if evidence_points else None,
            }
        )
        signal_evidence.append(
            {
                "signal_ref": signal_ref[0],
                "signal_title": _first_sentence(_as_str(finding.get("finding")))
                or f"Finding {index + 1}",
                "confidence": score,
                "contribution": " ".join(
                    part
                    for part in [evidence_points[0] if evidence_points else None, _as_str(finding.get("rebuttal"))]
                    if part
                )
                or "Contributes supporting context to the brief.",
                "source_refs": _as_str_list(finding.get("source_refs")),
            }
        )

    return {
        "metadata": {
            "category": _category_from_domain(domain_value),
            "confidence_level": _confidence_level(score),
            "priority_level": _priority_level(score),
        },
        "executive_summary": {
            "bottom_line": bluf,
            "why_it_matters": _first_sentence(decision_value) or _first_sentence(bluf),
            "recommended_action": decision_sentences[0] if decision_sentences else None,
            "watchpoint": _as_str(indicators[0].get("watch")) if indicators else None,
            "insights": claims,
            "situation_status": "Emerging",
            "decision_required": bool(decision_value),
            "decision_description": decision_value,
        },
        "key_intelligence_questions": {
            "what_is_happening": bluf or (claims[0]["text"] if claims else None),
            "why_is_it_happening": claims[0]["evidence_note"] if claims else None,
            "what_will_happen_next": outlook_value,
            "impact_on_organization": decision_value,
        },
        "situation_overview": {
            "topic": topic,
            "region_market": None,
            "timeframe": "Short-term",
            "overview": bluf,
        },
        "signals_and_indicators": {
            "leading_indicators": [_as_str(item.get("watch")) for item in indicators if _as_str(item.get("watch"))],
            "triggers": [_as_str(item.get("confirms_if")) for item in indicators if _as_str(item.get("confirms_if"))],
            "signal_evidence": signal_evidence,
        },
        "analysis": {
            "drivers": {
                "technology": [],
                "market": [],
                "regulatory": [],
            },
            "patterns_detected": [_as_str(item.get("rebuttal")) for item in findings if _as_str(item.get("rebuttal"))],
            "risk_assessment": {
                "operational": None,
                "strategic": None,
                "technical": None,
                "market": None,
            },
        },
        "impact_assessment": {
            "short_term": {
                "operations": _first_sentence(decision_value),
                "infrastructure": None,
                "product_roadmap": None,
            },
            "long_term": {
                "market_position": _first_sentence(outlook_value),
                "innovation_strategy": None,
                "competitive_landscape": None,
            },
        },
        "recommended_actions": {
            "immediate": decision_sentences[:2],
            "strategic": decision_sentences[2:4],
        },
        "key_signals": [claim["text"] for claim in claims[:3]],
        "limitations": _as_str_list(payload.get("limitations")),
        "outlook": outlook_value,
        "decision_lens": decision_value,
        "confidence_note": build_confidence_note(score, len(signal_evidence)),
        "domain": domain_value,
        "tags": _as_str_list(payload.get("tags")),
        "read_time": payload.get("read_time")
        if isinstance(payload.get("read_time"), int)
        else max(4, len(claims) + 3),
        "author": _as_str(payload.get("author")) or "AI Generated",
    }


def normalize_brief_body(
    payload: dict[str, Any] | None,
    *,
    topic: str,
    summary: str | None = None,
    domain: str | None = None,
    confidence: float | None = None,
    outlook: str | None = None,
    decision_lens: str | None = None,
) -> dict[str, Any]:
    """Normalize a brief payload to the canonical UI schema."""

    raw = payload or {}
    canonical = raw if _looks_canonical(raw) else _legacy_to_canonical(
        raw,
        topic=topic,
        summary=summary,
        domain=domain,
        confidence=confidence,
        outlook=outlook,
        decision_lens=decision_lens,
    )

    brief = deepcopy(DEFAULT_BRIEF_BODY)
    brief["metadata"].update(_as_dict(canonical.get("metadata")))
    brief["executive_summary"].update(_as_dict(canonical.get("executive_summary")))
    brief["key_intelligence_questions"].update(
        _as_dict(canonical.get("key_intelligence_questions"))
    )
    brief["situation_overview"].update(_as_dict(canonical.get("situation_overview")))
    brief["signals_and_indicators"].update(
        _as_dict(canonical.get("signals_and_indicators"))
    )
    brief["analysis"].update(_as_dict(canonical.get("analysis")))
    brief["analysis"]["drivers"].update(
        _as_dict(_as_dict(canonical.get("analysis")).get("drivers"))
    )
    brief["analysis"]["risk_assessment"].update(
        _as_dict(_as_dict(canonical.get("analysis")).get("risk_assessment"))
    )
    brief["impact_assessment"].update(_as_dict(canonical.get("impact_assessment")))
    brief["impact_assessment"]["short_term"].update(
        _as_dict(_as_dict(canonical.get("impact_assessment")).get("short_term"))
    )
    brief["impact_assessment"]["long_term"].update(
        _as_dict(_as_dict(canonical.get("impact_assessment")).get("long_term"))
    )
    brief["recommended_actions"].update(_as_dict(canonical.get("recommended_actions")))

    brief["executive_summary"]["insights"] = [
        claim
        for index, item in enumerate(_as_list(brief["executive_summary"]["insights"]))
        if (claim := _normalize_claim(item, index)) is not None
    ]
    brief["signals_and_indicators"]["leading_indicators"] = _as_str_list(
        brief["signals_and_indicators"]["leading_indicators"]
    )
    brief["signals_and_indicators"]["triggers"] = _as_str_list(
        brief["signals_and_indicators"]["triggers"]
    )
    brief["signals_and_indicators"]["signal_evidence"] = [
        item
        for index, raw_item in enumerate(
            _as_list(brief["signals_and_indicators"]["signal_evidence"])
        )
        if (
            item := _normalize_signal_evidence(
                raw_item,
                index,
                _as_confidence(canonical.get("confidence"), confidence or 0.75),
            )
        )
        is not None
    ]
    brief["analysis"]["drivers"]["technology"] = _as_str_list(
        brief["analysis"]["drivers"]["technology"]
    )
    brief["analysis"]["drivers"]["market"] = _as_str_list(
        brief["analysis"]["drivers"]["market"]
    )
    brief["analysis"]["drivers"]["regulatory"] = _as_str_list(
        brief["analysis"]["drivers"]["regulatory"]
    )
    brief["analysis"]["patterns_detected"] = _as_str_list(
        brief["analysis"]["patterns_detected"]
    )
    brief["recommended_actions"]["immediate"] = _as_str_list(
        brief["recommended_actions"]["immediate"]
    )
    brief["recommended_actions"]["strategic"] = _as_str_list(
        brief["recommended_actions"]["strategic"]
    )
    brief["key_signals"] = _as_str_list(canonical.get("key_signals"))
    brief["limitations"] = _as_str_list(canonical.get("limitations"))
    brief["tags"] = _as_str_list(canonical.get("tags"))
    brief["outlook"] = _as_str(canonical.get("outlook")) or outlook
    brief["decision_lens"] = _as_str(canonical.get("decision_lens")) or decision_lens
    brief["domain"] = _as_str(canonical.get("domain")) or domain
    brief["read_time"] = (
        canonical.get("read_time")
        if isinstance(canonical.get("read_time"), int)
        else brief["read_time"]
    )
    brief["author"] = _as_str(canonical.get("author")) or "AI Generated"

    score = _as_confidence(
        canonical.get("confidence")
        or confidence
        or {"Low": 0.58, "Medium": 0.72, "High": 0.85, "Verified": 0.95}.get(
            brief["metadata"]["confidence_level"],
            0.75,
        )
    )
    brief["confidence_note"] = _as_str(canonical.get("confidence_note")) or build_confidence_note(
        score, len(brief["signals_and_indicators"]["signal_evidence"])
    )

    return brief
