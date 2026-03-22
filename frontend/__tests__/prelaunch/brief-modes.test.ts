import { describe, expect, it } from 'vitest'
import type { Signal } from '@/lib/hooks/useSignals'
import { buildAnalystSections, buildExecutiveSections } from '@/components/signals/SignalDrawer'

const sampleSignal: Signal = {
  id: 'signal-1',
  entityName: 'CBN',
  entityInitial: 'C',
  domain: 'Macro',
  severity: 'high',
  confidence: 84,
  headline: 'Inflation is cooling, but policy stays tight',
  summary: 'Inflation is easing, but not enough to justify a fast policy pivot.',
  publishedAt: '2026-03-22T09:00:00Z',
  relativeTime: 'just now',
  sources: [
    {
      id: 'src-1',
      name: 'National Bureau of Statistics',
      url: 'https://example.com/cpi',
      publishedAt: '2026-03-22T08:00:00Z',
    },
  ],
  sparklineData: [72, 78, 84],
  isUnread: false,
  isSaved: false,
  brief: {
    metadata: {
      category: 'Market',
      confidence_level: 'High',
      priority_level: 'High',
    },
    executive_summary: {
      bottom_line: 'Inflation is easing, but not enough to justify a fast pivot.',
      why_it_matters: 'Funding assumptions still need to stay conservative.',
      recommended_action: 'Keep near-term liquidity plans conservative.',
      watchpoint: 'The next CPI release below 30%.',
      insights: [
        {
          text: 'Headline inflation is slowing.',
          signal_refs: ['SIG-1'],
          source_refs: ['SRC-1'],
          evidence_note: 'CPI eased to 31.2% in the latest release.',
        },
      ],
      situation_status: 'Emerging',
      decision_required: true,
      decision_description: 'Decide whether to revise treasury assumptions.',
    },
    key_intelligence_questions: {
      what_is_happening: 'Inflation is slowing.',
      why_is_it_happening: 'Base effects are helping.',
      what_will_happen_next: 'Gradual easing is more likely than a fast pivot.',
      impact_on_organization: 'Funding costs may stay elevated in the near term.',
    },
    situation_overview: {
      topic: 'Nigeria inflation outlook',
      region_market: 'Nigeria',
      timeframe: 'Short-term',
      overview: 'Disinflation is emerging, but food inflation remains sticky.',
    },
    signals_and_indicators: {
      leading_indicators: ['Monthly CPI'],
      triggers: ['CPI below 30%'],
      signal_evidence: [
        {
          signal_ref: 'SIG-1',
          signal_title: 'Inflation slowed in the latest monthly print',
          confidence: 0.84,
          contribution: 'CPI eased to 31.2% in the latest release.',
          source_refs: ['SRC-1'],
        },
      ],
    },
    analysis: {
      drivers: {
        technology: [],
        market: ['Base effects'],
        regulatory: [],
      },
      patterns_detected: ['Disinflation is emerging, but food inflation remains sticky.'],
      risk_assessment: {
        operational: null,
        strategic: 'A delayed easing cycle could constrain investment timing.',
        technical: null,
        market: 'FX liquidity volatility could reverse the progress.',
      },
    },
    impact_assessment: {
      short_term: {
        operations: 'Financing conditions remain restrictive.',
        infrastructure: null,
        product_roadmap: null,
      },
      long_term: {
        market_position: 'A slower easing cycle could delay demand recovery.',
        innovation_strategy: null,
        competitive_landscape: null,
      },
    },
    recommended_actions: {
      immediate: ['Maintain conservative liquidity assumptions.'],
      strategic: ['Revisit investment triggers after the next CPI print.'],
    },
    key_signals: ['Headline inflation is slowing.'],
    limitations: ['The evidence base is still relatively narrow.'],
    outlook: 'Expect gradual easing, not a fast pivot.',
    decision_lens: 'Avoid premature balance-sheet commitments.',
    confidence_note: 'High confidence based on corroborating recent signals.',
    domain: 'Macro',
    tags: ['#Macro', '#Inflation'],
    read_time: 5,
    author: 'AI Generated',
  },
}

describe('brief mode section builders', () => {
  it('builds an executive brief from the canonical brief with explicit refs', () => {
    const sections = buildExecutiveSections(sampleSignal)

    expect(sections.map((section) => section.heading)).toEqual([
      'Bottom Line',
      'Key Claims',
      'Actions',
      'Confidence',
    ])
    expect(sections[1]?.content).toContain('SIG-1')
    expect(sections[1]?.content).toContain('SRC-1')
  })

  it('builds an analyst brief from the same canonical brief with evidence refs', () => {
    const sections = buildAnalystSections(sampleSignal)

    expect(sections.map((section) => section.heading)).toContain('Signal Evidence')
    expect(sections.map((section) => section.heading)).toContain('Recommended Actions')
    expect(sections.find((section) => section.heading === 'Signal Evidence')?.content).toContain('SRC-1')
    expect(sections.find((section) => section.heading === 'Executive Summary')?.content).toContain('SIG-1')
  })
})
