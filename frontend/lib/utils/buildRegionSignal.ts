/**
 * Convert a MapRegion into a Signal-shaped object for the shared drawer UI.
 */

import { EMPTY_BRIEF, type BriefClaim } from '@/lib/briefs/schema'
import type { Signal } from '@/lib/hooks/useSignals'
import type { MapRegion } from '@/lib/hooks/useDomainMap'

const RISK_TO_SEVERITY: Record<string, Signal['severity']> = {
  critical: 'critical',
  elevated: 'high',
  moderate: 'medium',
  stable: 'low',
}

export function buildRegionSignal(region: MapRegion): Signal {
  const now = new Date().toISOString()
  const summary = region.summary || `Intelligence overview for ${region.name}, ${region.state}.`
  const topSignal = region.topSignal?.trim()
  const insightClaims: BriefClaim[] = [
    {
      text: `${region.name} is currently rated ${region.riskLevel}.`,
      signal_refs: [`REGION-${region.id}`],
      source_refs: topSignal ? [`region-${region.id}-source`] : [],
      evidence_note: 'Derived from the regional map intelligence layer.',
    },
    {
      text: `${region.signalCount} signals are active across ${region.domains.join(', ') || 'the tracked domains'}.`,
      signal_refs: [`REGION-${region.id}`],
      source_refs: topSignal ? [`region-${region.id}-source`] : [],
      evidence_note: 'Counts reflect the latest synthesized regional rollup.',
    },
    ...(topSignal
      ? [{
          text: topSignal,
          signal_refs: [`REGION-${region.id}`],
          source_refs: [`region-${region.id}-source`],
          evidence_note: 'Top regional development highlighted by the map summary.',
        }]
      : []),
  ]

  return {
    id: `region-${region.id}`,
    entityName: region.name,
    entityInitial: region.name.charAt(0).toUpperCase() || 'R',
    domain: region.domains[0] ?? 'General',
    severity: RISK_TO_SEVERITY[region.riskLevel] ?? region.severity,
    confidence: Math.max(0, Math.min(100, region.opportunityScore)),
    headline: `${region.name} - Regional Intelligence Brief`,
    summary,
    publishedAt: now,
    relativeTime: 'just now',
    sources: topSignal
      ? [
          {
            id: `region-${region.id}-source`,
            name: `Region Intelligence - ${region.state}`,
            url: '#',
            publishedAt: now,
          },
        ]
      : [],
    sparklineData: [Math.max(region.opportunityScore - 8, 0), region.opportunityScore, Math.min(region.opportunityScore + 4, 100)],
    isUnread: false,
    isSaved: false,
    brief: {
      ...EMPTY_BRIEF,
      metadata: {
        category: 'Strategic',
        confidence_level: region.opportunityScore >= 85 ? 'High' : region.opportunityScore >= 65 ? 'Medium' : 'Low',
        priority_level: region.riskLevel === 'critical'
          ? 'Critical'
          : region.riskLevel === 'elevated'
            ? 'High'
            : region.riskLevel === 'moderate'
              ? 'Medium'
              : 'Low',
      },
      executive_summary: {
        bottom_line: summary,
        why_it_matters: `${region.name} needs close attention because regional conditions can shift the operating picture quickly.`,
        recommended_action: topSignal ?? `Review the active domains in ${region.name} and confirm owners for follow-up.`,
        watchpoint: topSignal ?? `Track fresh signals from ${region.name} over the next reporting cycle.`,
        insights: insightClaims,
        situation_status: region.riskLevel === 'critical' ? 'Escalating' : 'Stable',
        decision_required: region.riskLevel === 'critical' || region.riskLevel === 'elevated',
        decision_description: topSignal || null,
      },
      situation_overview: {
        topic: `${region.name} regional outlook`,
        region_market: `${region.name}, ${region.state}`,
        timeframe: 'Short-term',
        overview: summary,
      },
      key_intelligence_questions: {
        what_is_happening: summary,
        why_is_it_happening: topSignal
          ? `Recent activity points to ${topSignal.toLowerCase()}.`
          : `Regional pressure is concentrated across ${region.domains.join(', ') || 'tracked sectors'}.`,
        what_will_happen_next: `Expect follow-up movement in ${region.name} if the current regional pattern persists.`,
        impact_on_organization: `${region.name} can affect sourcing, competitive posture, and market timing decisions.`,
      },
      signals_and_indicators: {
        leading_indicators: topSignal ? [topSignal] : [],
        triggers: [
          `Regional risk level: ${region.riskLevel}`,
          `Active signal count: ${region.signalCount}`,
        ],
        signal_evidence: [
          {
            signal_ref: `REGION-${region.id}`,
            signal_title: `${region.name} regional rollup`,
            confidence: Math.max(0, Math.min(region.opportunityScore / 100, 1)),
            contribution: 'Regional synthesis for map drill-down context.',
            source_refs: topSignal ? [`region-${region.id}-source`] : [],
          },
        ],
      },
      analysis: {
        drivers: {
          technology: [],
          market: region.domains,
          regulatory: [],
        },
        patterns_detected: [
          `${region.signalCount} regional signal${region.signalCount === 1 ? '' : 's'} are active`,
          `Opportunity score is ${region.opportunityScore}`,
        ],
        risk_assessment: {
          operational: `Regional conditions are currently ${region.riskLevel}.`,
          strategic: topSignal ?? `Watch ${region.name} for follow-on shifts.`,
          technical: null,
          market: `Coverage spans ${region.domains.join(', ') || 'tracked sectors'}.`,
        },
      },
      impact_assessment: {
        short_term: {
          operations: `Monitor supplier, customer, and channel updates tied to ${region.name}.`,
          infrastructure: null,
          product_roadmap: null,
        },
        long_term: {
          market_position: `Sustained movement in ${region.name} could reshape local competitive conditions.`,
          innovation_strategy: null,
          competitive_landscape: `Track how peers respond to regional momentum in ${region.name}.`,
        },
      },
      recommended_actions: {
        immediate: topSignal ? [topSignal] : [],
        strategic: [
          `Review active domains: ${region.domains.join(', ') || 'none recorded'}`,
          `Monitor ${region.signalCount} signal${region.signalCount === 1 ? '' : 's'} in this region`,
        ],
      },
      key_signals: topSignal ? [topSignal] : [],
      limitations: ['Regional drill-down uses synthesized map context rather than a dedicated live signal record.'],
      outlook: `Near-term conditions in ${region.name} remain ${region.riskLevel}.`,
      decision_lens: `Use ${region.name} as a regional watchpoint for prioritization and follow-up.`,
      confidence_note: 'Confidence reflects synthesized regional scoring and should be validated against live source reporting for high-stakes decisions.',
      domain: region.domains[0] ?? 'General',
      tags: region.domains,
      read_time: 4,
      author: 'Cogent Map Intelligence',
    },
  }
}
