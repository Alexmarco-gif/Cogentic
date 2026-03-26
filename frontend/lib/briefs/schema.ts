export type BriefCategory =
  | 'Strategic'
  | 'Operational'
  | 'Market'
  | 'Threat'
  | 'Technical'
  | 'Competitive'

export type BriefConfidenceLevel = 'Low' | 'Medium' | 'High' | 'Verified'
export type BriefPriorityLevel = 'Low' | 'Medium' | 'High' | 'Critical'
export type SituationStatus = 'Emerging' | 'Stable' | 'Escalating' | 'Declining' | 'Improving'
export type BriefTimeframe = 'Immediate' | 'Short-term' | 'Long-term'

export interface BriefMetadata {
  category: BriefCategory
  confidence_level: BriefConfidenceLevel
  priority_level: BriefPriorityLevel
}

export interface BriefClaim {
  text: string
  signal_refs: string[]
  source_refs: string[]
  evidence_note: string | null
}

export interface ExecutiveSummary {
  bottom_line: string | null
  why_it_matters: string | null
  recommended_action: string | null
  watchpoint: string | null
  insights: BriefClaim[]
  situation_status: SituationStatus
  decision_required: boolean
  decision_description: string | null
}

export interface KeyIntelligenceQuestions {
  what_is_happening: string | null
  why_is_it_happening: string | null
  what_will_happen_next: string | null
  impact_on_organization: string | null
}

export interface SituationOverview {
  topic: string | null
  region_market: string | null
  timeframe: BriefTimeframe
  overview: string | null
}

export interface SignalEvidence {
  signal_ref: string
  signal_title: string
  confidence: number
  contribution: string
  source_refs: string[]
}

export interface SignalsAndIndicators {
  leading_indicators: string[]
  triggers: string[]
  signal_evidence: SignalEvidence[]
}

export interface AnalysisDrivers {
  technology: string[]
  market: string[]
  regulatory: string[]
}

export interface RiskAssessment {
  operational: string | null
  strategic: string | null
  technical: string | null
  market: string | null
}

export interface Analysis {
  drivers: AnalysisDrivers
  patterns_detected: string[]
  risk_assessment: RiskAssessment
}

export interface ShortTermImpact {
  operations: string | null
  infrastructure: string | null
  product_roadmap: string | null
}

export interface LongTermImpact {
  market_position: string | null
  innovation_strategy: string | null
  competitive_landscape: string | null
}

export interface ImpactAssessment {
  short_term: ShortTermImpact
  long_term: LongTermImpact
}

export interface RecommendedActions {
  immediate: string[]
  strategic: string[]
}

export interface IntelligenceBrief {
  metadata: BriefMetadata
  executive_summary: ExecutiveSummary
  key_intelligence_questions: KeyIntelligenceQuestions
  situation_overview: SituationOverview
  signals_and_indicators: SignalsAndIndicators
  analysis: Analysis
  impact_assessment: ImpactAssessment
  recommended_actions: RecommendedActions
  key_signals: string[]
  limitations: string[]
  outlook: string | null
  decision_lens: string | null
  confidence_note: string | null
  domain: string | null
  tags: string[]
  read_time: number
  author: string | null
}

export interface BriefNormalizationContext {
  headline?: string | null
  summary?: string | null
  domain?: string | null
  confidence?: number | null
  outlook?: string | null
  decisionLens?: string | null
  readTime?: number | null
  author?: string | null
  tags?: string[]
}

const VALID_CATEGORIES: BriefCategory[] = [
  'Strategic',
  'Operational',
  'Market',
  'Threat',
  'Technical',
  'Competitive',
]

const VALID_CONFIDENCE_LEVELS: BriefConfidenceLevel[] = ['Low', 'Medium', 'High', 'Verified']
const VALID_PRIORITY_LEVELS: BriefPriorityLevel[] = ['Low', 'Medium', 'High', 'Critical']
const VALID_STATUSES: SituationStatus[] = ['Emerging', 'Stable', 'Escalating', 'Declining', 'Improving']
const VALID_TIMEFRAMES: BriefTimeframe[] = ['Immediate', 'Short-term', 'Long-term']

export const EMPTY_BRIEF: IntelligenceBrief = {
  metadata: { category: 'Strategic', confidence_level: 'Low', priority_level: 'Low' },
  executive_summary: {
    bottom_line: null,
    why_it_matters: null,
    recommended_action: null,
    watchpoint: null,
    insights: [],
    situation_status: 'Emerging',
    decision_required: false,
    decision_description: null,
  },
  key_intelligence_questions: {
    what_is_happening: null,
    why_is_it_happening: null,
    what_will_happen_next: null,
    impact_on_organization: null,
  },
  situation_overview: {
    topic: null,
    region_market: null,
    timeframe: 'Short-term',
    overview: null,
  },
  signals_and_indicators: {
    leading_indicators: [],
    triggers: [],
    signal_evidence: [],
  },
  analysis: {
    drivers: { technology: [], market: [], regulatory: [] },
    patterns_detected: [],
    risk_assessment: {
      operational: null,
      strategic: null,
      technical: null,
      market: null,
    },
  },
  impact_assessment: {
    short_term: {
      operations: null,
      infrastructure: null,
      product_roadmap: null,
    },
    long_term: {
      market_position: null,
      innovation_strategy: null,
      competitive_landscape: null,
    },
  },
  recommended_actions: { immediate: [], strategic: [] },
  key_signals: [],
  limitations: [],
  outlook: null,
  decision_lens: null,
  confidence_note: null,
  domain: null,
  tags: [],
  read_time: 5,
  author: null,
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim() : null
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
    : []
}

function asConfidence(value: unknown, fallback = 0.75): number {
  if (typeof value !== 'number' || Number.isNaN(value)) return fallback
  if (value > 1) return Math.max(0, Math.min(value / 100, 1))
  return Math.max(0, Math.min(value, 1))
}

function toConfidenceLevel(score: number): BriefConfidenceLevel {
  if (score >= 0.92) return 'Verified'
  if (score >= 0.8) return 'High'
  if (score >= 0.65) return 'Medium'
  return 'Low'
}

function toPriorityLevel(score: number): BriefPriorityLevel {
  if (score >= 0.9) return 'Critical'
  if (score >= 0.8) return 'High'
  if (score >= 0.65) return 'Medium'
  return 'Low'
}

function mapDomainToCategory(domain: string | null): BriefCategory {
  const normalized = domain?.toLowerCase() ?? ''
  if (normalized.includes('market') || normalized.includes('finance') || normalized.includes('macro')) {
    return 'Market'
  }
  if (normalized.includes('regulatory') || normalized.includes('policy')) {
    return 'Threat'
  }
  if (normalized.includes('technology') || normalized.includes('tech')) {
    return 'Technical'
  }
  if (normalized.includes('operations') || normalized.includes('supply')) {
    return 'Operational'
  }
  if (normalized.includes('competitive')) {
    return 'Competitive'
  }
  return 'Strategic'
}

function splitSentences(value: string | null): string[] {
  if (!value) return []
  return value
    .split(/(?<=[.!?])\s+/)
    .map((sentence) => sentence.trim())
    .filter(Boolean)
}

function takeFirstSentence(value: string | null): string | null {
  return splitSentences(value)[0] ?? null
}

function buildConfidenceNote(score: number, evidenceCount: number): string {
  const level = toConfidenceLevel(score)
  if (level === 'Verified') {
    return evidenceCount >= 3
      ? 'Verified confidence from corroborating evidence across multiple recent signals.'
      : 'Verified confidence, though the evidence base is still relatively narrow.'
  }
  if (level === 'High') {
    return evidenceCount >= 3
      ? 'High confidence based on corroborating recent signals.'
      : 'High confidence, but this view still leans on a concentrated evidence set.'
  }
  if (level === 'Medium') {
    return 'Medium confidence: the pattern is credible, but there are still open variables to watch.'
  }
  return 'Low confidence: treat this as an early signal until more evidence arrives.'
}

function normalizeClaim(value: unknown, index: number): BriefClaim | null {
  if (typeof value === 'string') {
    const text = asString(value)
    if (!text) return null
    return {
      text,
      signal_refs: [`SIG-${index + 1}`],
      source_refs: [],
      evidence_note: null,
    }
  }

  if (!isRecord(value)) return null

  const text = asString(value.text) ?? asString(value.statement) ?? asString(value.claim)
  if (!text) return null

  return {
    text,
    signal_refs: asStringArray(value.signal_refs).length > 0 ? asStringArray(value.signal_refs) : [`SIG-${index + 1}`],
    source_refs: asStringArray(value.source_refs),
    evidence_note: asString(value.evidence_note),
  }
}

function normalizeSignalEvidence(value: unknown, index: number, fallbackConfidence: number): SignalEvidence | null {
  if (!isRecord(value)) return null

  const signal_ref = asString(value.signal_ref) ?? `SIG-${index + 1}`
  const signal_title = asString(value.signal_title) ?? asString(value.title) ?? signal_ref
  const contribution =
    asString(value.contribution)
    ?? asString(value.summary)
    ?? takeFirstSentence(asString(value.evidence_note))
    ?? 'Contributes supporting context to the brief.'

  return {
    signal_ref,
    signal_title,
    confidence: asConfidence(value.confidence, fallbackConfidence),
    contribution,
    source_refs: asStringArray(value.source_refs),
  }
}

function looksLikeCanonicalBrief(value: unknown): value is Record<string, unknown> {
  return isRecord(value)
    && isRecord(value.metadata)
    && isRecord(value.executive_summary)
    && isRecord(value.key_intelligence_questions)
}

function legacyToCanonicalBrief(raw: Record<string, unknown>, context: BriefNormalizationContext): IntelligenceBrief {
  const score = asConfidence(raw.confidence ?? context.confidence, 0.75)
  const findings = Array.isArray(raw.findings) ? raw.findings : []
  const indicators = Array.isArray(raw.indicators) ? raw.indicators : []
  const bluf = asString(raw.bluf) ?? asString(context.summary)
  const outlook = asString(raw.outlook) ?? asString(context.outlook)
  const decisionLens = asString(raw.decision_lens) ?? asString(context.decisionLens)
  const domain = asString(raw.domain) ?? asString(context.domain)
  const tags = asStringArray(raw.tags).length > 0 ? asStringArray(raw.tags) : (context.tags ?? [])
  const claims = findings
    .map((finding, index) => {
      if (!isRecord(finding)) return null
      const evidence = asStringArray(finding.evidence)
      const claim: BriefClaim = {
        text: asString(finding.finding) ?? `Finding ${index + 1}`,
        signal_refs: asStringArray(finding.signal_refs).length > 0 ? asStringArray(finding.signal_refs) : [`SIG-${index + 1}`],
        source_refs: asStringArray(finding.source_refs),
        evidence_note: evidence[0] ?? null,
      }
      return claim
    })
    .filter((claim): claim is BriefClaim => claim !== null)

  const evidence = findings
    .map((finding, index) => {
      if (!isRecord(finding)) return null
      const contributionLines = [
        asStringArray(finding.evidence)[0] ?? null,
        asString(finding.rebuttal),
      ].filter(Boolean) as string[]

      return {
        signal_ref: asStringArray(finding.signal_refs)[0] ?? `SIG-${index + 1}`,
        signal_title: takeFirstSentence(asString(finding.finding)) ?? `Finding ${index + 1}`,
        confidence: score,
        contribution: contributionLines.join(' '),
        source_refs: asStringArray(finding.source_refs),
      } satisfies SignalEvidence
    })
    .filter((item): item is SignalEvidence => item !== null)

  const recommendedSentences = splitSentences(decisionLens)

  return {
    ...EMPTY_BRIEF,
    metadata: {
      category: mapDomainToCategory(domain),
      confidence_level: toConfidenceLevel(score),
      priority_level: toPriorityLevel(score),
    },
    executive_summary: {
      bottom_line: bluf,
      why_it_matters: takeFirstSentence(decisionLens) ?? takeFirstSentence(bluf),
      recommended_action: recommendedSentences[0] ?? null,
      watchpoint: indicators.find(isRecord) ? asString((indicators.find(isRecord) as Record<string, unknown>).watch) : null,
      insights: claims,
      situation_status: 'Emerging',
      decision_required: Boolean(decisionLens),
      decision_description: decisionLens,
    },
    key_intelligence_questions: {
      what_is_happening: bluf ?? claims[0]?.text ?? null,
      why_is_it_happening: claims[0]?.evidence_note ?? null,
      what_will_happen_next: outlook,
      impact_on_organization: decisionLens,
    },
    situation_overview: {
      topic: asString(context.headline),
      region_market: null,
      timeframe: 'Short-term',
      overview: bluf,
    },
    signals_and_indicators: {
      leading_indicators: indicators
        .filter(isRecord)
        .map((indicator) => asString(indicator.watch))
        .filter((item): item is string => Boolean(item)),
      triggers: indicators
        .filter(isRecord)
        .map((indicator) => asString(indicator.confirms_if))
        .filter((item): item is string => Boolean(item)),
      signal_evidence: evidence,
    },
    analysis: {
      drivers: { technology: [], market: [], regulatory: [] },
      patterns_detected: findings
        .filter(isRecord)
        .map((finding) => asString(finding.rebuttal))
        .filter((item): item is string => Boolean(item)),
      risk_assessment: {
        operational: null,
        strategic: null,
        technical: null,
        market: null,
      },
    },
    impact_assessment: {
      short_term: {
        operations: takeFirstSentence(decisionLens),
        infrastructure: null,
        product_roadmap: null,
      },
      long_term: {
        market_position: takeFirstSentence(outlook),
        innovation_strategy: null,
        competitive_landscape: null,
      },
    },
    recommended_actions: {
      immediate: recommendedSentences.slice(0, 2),
      strategic: recommendedSentences.slice(2, 4),
    },
    key_signals: claims.map((claim) => claim.text).slice(0, 3),
    limitations: asStringArray(raw.limitations),
    outlook,
    decision_lens: decisionLens,
    confidence_note: buildConfidenceNote(score, evidence.length),
    domain,
    tags,
    read_time: typeof raw.read_time === 'number' ? raw.read_time : (context.readTime ?? Math.max(4, claims.length + 3)),
    author: asString(raw.author) ?? asString(context.author),
  }
}

export function normalizeIntelligenceBrief(raw: unknown, context: BriefNormalizationContext = {}): IntelligenceBrief {
  const source = isRecord(raw) ? raw : {}
  const canonical = looksLikeCanonicalBrief(source) ? source : legacyToCanonicalBrief(source, context)
  const metadata = isRecord(canonical.metadata) ? canonical.metadata : {}
  const score = asConfidence(
    typeof metadata.confidence_level === 'string'
      ? context.confidence
      : source.confidence ?? context.confidence,
    0.75,
  )

  const executiveSummary = isRecord(canonical.executive_summary) ? canonical.executive_summary : {}
  const keyQuestions = isRecord(canonical.key_intelligence_questions) ? canonical.key_intelligence_questions : {}
  const situationOverview = isRecord(canonical.situation_overview) ? canonical.situation_overview : {}
  const signalsAndIndicators = isRecord(canonical.signals_and_indicators) ? canonical.signals_and_indicators : {}
  const analysis = isRecord(canonical.analysis) ? canonical.analysis : {}
  const drivers = isRecord(analysis.drivers) ? analysis.drivers : {}
  const riskAssessment = isRecord(analysis.risk_assessment) ? analysis.risk_assessment : {}
  const impactAssessment = isRecord(canonical.impact_assessment) ? canonical.impact_assessment : {}
  const shortTerm = isRecord(impactAssessment.short_term) ? impactAssessment.short_term : {}
  const longTerm = isRecord(impactAssessment.long_term) ? impactAssessment.long_term : {}
  const recommendedActions = isRecord(canonical.recommended_actions) ? canonical.recommended_actions : {}

  const normalizedInsights = Array.isArray(executiveSummary.insights)
    ? executiveSummary.insights
      .map(normalizeClaim)
      .filter((claim): claim is BriefClaim => claim !== null)
    : []

  const normalizedEvidence = Array.isArray(signalsAndIndicators.signal_evidence)
    ? signalsAndIndicators.signal_evidence
      .map((item, index) => normalizeSignalEvidence(item, index, score))
      .filter((item): item is SignalEvidence => item !== null)
    : []

  return {
    metadata: {
      category: VALID_CATEGORIES.includes(metadata.category as BriefCategory)
        ? metadata.category as BriefCategory
        : mapDomainToCategory(asString(canonical.domain) ?? asString(context.domain)),
      confidence_level: VALID_CONFIDENCE_LEVELS.includes(metadata.confidence_level as BriefConfidenceLevel)
        ? metadata.confidence_level as BriefConfidenceLevel
        : toConfidenceLevel(score),
      priority_level: VALID_PRIORITY_LEVELS.includes(metadata.priority_level as BriefPriorityLevel)
        ? metadata.priority_level as BriefPriorityLevel
        : toPriorityLevel(score),
    },
    executive_summary: {
      bottom_line: asString(executiveSummary.bottom_line) ?? asString(context.summary),
      why_it_matters: asString(executiveSummary.why_it_matters),
      recommended_action: asString(executiveSummary.recommended_action),
      watchpoint: asString(executiveSummary.watchpoint),
      insights: normalizedInsights,
      situation_status: VALID_STATUSES.includes(executiveSummary.situation_status as SituationStatus)
        ? executiveSummary.situation_status as SituationStatus
        : 'Emerging',
      decision_required: Boolean(executiveSummary.decision_required),
      decision_description: asString(executiveSummary.decision_description),
    },
    key_intelligence_questions: {
      what_is_happening: asString(keyQuestions.what_is_happening),
      why_is_it_happening: asString(keyQuestions.why_is_it_happening),
      what_will_happen_next: asString(keyQuestions.what_will_happen_next),
      impact_on_organization: asString(keyQuestions.impact_on_organization),
    },
    situation_overview: {
      topic: asString(situationOverview.topic) ?? asString(context.headline),
      region_market: asString(situationOverview.region_market),
      timeframe: VALID_TIMEFRAMES.includes(situationOverview.timeframe as BriefTimeframe)
        ? situationOverview.timeframe as BriefTimeframe
        : 'Short-term',
      overview: asString(situationOverview.overview) ?? asString(context.summary),
    },
    signals_and_indicators: {
      leading_indicators: asStringArray(signalsAndIndicators.leading_indicators),
      triggers: asStringArray(signalsAndIndicators.triggers),
      signal_evidence: normalizedEvidence,
    },
    analysis: {
      drivers: {
        technology: asStringArray(drivers.technology),
        market: asStringArray(drivers.market),
        regulatory: asStringArray(drivers.regulatory),
      },
      patterns_detected: asStringArray(analysis.patterns_detected),
      risk_assessment: {
        operational: asString(riskAssessment.operational),
        strategic: asString(riskAssessment.strategic),
        technical: asString(riskAssessment.technical),
        market: asString(riskAssessment.market),
      },
    },
    impact_assessment: {
      short_term: {
        operations: asString(shortTerm.operations),
        infrastructure: asString(shortTerm.infrastructure),
        product_roadmap: asString(shortTerm.product_roadmap),
      },
      long_term: {
        market_position: asString(longTerm.market_position),
        innovation_strategy: asString(longTerm.innovation_strategy),
        competitive_landscape: asString(longTerm.competitive_landscape),
      },
    },
    recommended_actions: {
      immediate: asStringArray(recommendedActions.immediate),
      strategic: asStringArray(recommendedActions.strategic),
    },
    key_signals: asStringArray(canonical.key_signals),
    limitations: asStringArray(canonical.limitations),
    outlook: asString(canonical.outlook) ?? asString(context.outlook),
    decision_lens: asString(canonical.decision_lens) ?? asString(context.decisionLens),
    confidence_note: asString(canonical.confidence_note) ?? buildConfidenceNote(score, normalizedEvidence.length),
    domain: asString(canonical.domain) ?? asString(context.domain),
    tags: asStringArray(canonical.tags).length > 0 ? asStringArray(canonical.tags) : (context.tags ?? []),
    read_time: typeof canonical.read_time === 'number'
      ? canonical.read_time
      : (context.readTime ?? Math.max(4, normalizedInsights.length + 3)),
    author: asString(canonical.author) ?? asString(context.author),
  }
}
