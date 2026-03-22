import { describe, expect, it } from 'vitest'
import { normalizeIntelligenceBrief } from '@/lib/briefs/schema'

describe('normalizeIntelligenceBrief', () => {
  it('maps legacy findings into the canonical signal drawer schema', () => {
    const brief = normalizeIntelligenceBrief({
      bluf: 'Inflation is easing, but risks remain.',
      findings: [
        {
          finding: 'Inflation is easing.',
          evidence: ['CPI slowed to 31.2%.'],
          rebuttal: 'Food inflation remains high.',
        },
      ],
      indicators: [
        {
          watch: 'Next CPI release',
          confirms_if: 'Below 30%',
          disconfirms_if: 'Above 33%',
        },
      ],
      decision_lens: 'Keep liquidity plans conservative.',
      confidence: 84,
      domain: 'macro',
    }, {
      headline: 'Inflation outlook',
      summary: 'Inflation is easing, but risks remain.',
      confidence: 84,
      domain: 'macro',
    })

    expect(brief.executive_summary.bottom_line).toBe('Inflation is easing, but risks remain.')
    expect(brief.executive_summary.insights[0]?.signal_refs).toEqual(['SIG-1'])
    expect(brief.signals_and_indicators.signal_evidence[0]?.signal_ref).toBe('SIG-1')
    expect(brief.metadata.confidence_level).toBe('High')
  })

  it('preserves canonical claim references and top-level guidance fields', () => {
    const brief = normalizeIntelligenceBrief({
      metadata: {
        category: 'Strategic',
        confidence_level: 'Verified',
        priority_level: 'Critical',
      },
      executive_summary: {
        bottom_line: 'Demand is reaccelerating.',
        why_it_matters: 'This changes the market posture.',
        recommended_action: 'Increase coverage now.',
        watchpoint: 'A sudden reversal in weekly orders.',
        insights: [
          {
            text: 'Weekly demand is climbing.',
            signal_refs: ['SIG-2'],
            source_refs: ['SRC-1'],
            evidence_note: 'Orders rose 18% week on week.',
          },
        ],
        situation_status: 'Escalating',
        decision_required: true,
        decision_description: 'Decide whether to expand inventory.',
      },
      key_intelligence_questions: {
        what_is_happening: 'Demand is rising.',
        why_is_it_happening: 'Competitor stock-outs are redirecting orders.',
        what_will_happen_next: 'Further short-term acceleration is likely.',
        impact_on_organization: 'Missed revenue if stock stays constrained.',
      },
      confidence_note: 'Verified confidence from corroborating evidence.',
      domain: 'market',
      tags: ['#Demand'],
      read_time: 6,
      author: 'AI Generated',
    })

    expect(brief.executive_summary.insights[0]?.signal_refs).toEqual(['SIG-2'])
    expect(brief.executive_summary.insights[0]?.source_refs).toEqual(['SRC-1'])
    expect(brief.confidence_note).toContain('Verified confidence')
    expect(brief.read_time).toBe(6)
  })
})
