'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'

import { getCurrentUser as apiGetCurrentUser } from '@/lib/api/auth'
import {
  activateContract as apiActivateExistingContract,
  createContract as apiCreateContract,
  deactivateContract as apiDeactivateExistingContract,
  deleteContract as apiDeleteContract,
  listContracts as apiListContracts,
  triggerContractFetch as apiTriggerContractFetch,
  updateContract as apiUpdateContract,
} from '@/lib/api/contracts'
import { type IndustryItem, getIndustries } from '@/lib/api/discovered_sources'
import { friendlyErrorMessage, isApiError } from '@/lib/api/errors'
import { executeSearch } from '@/lib/api/search'
import type {
  SearchResponse,
  SignalContractResponse,
} from '@/lib/api/types'
import {
  buildProviderExtractionConfig,
  getDefaultSourcePreset,
  getDefaultSourceUrlForPreset,
  getProviderLabel,
  type ContractSourcePreset,
  type StudioSourceType,
} from '@/lib/contracts/providerPresets'
import { useFeatureGate } from '@/lib/hooks/useFeatureGate'

export type ContractStep = 'draft' | 'validation' | 'simulation' | 'active'

export type FieldType = 'string' | 'number' | 'boolean' | 'date' | 'enum'
export type DeliveryFormat = 'json' | 'csv' | 'parquet'
export type { ContractSourcePreset, StudioSourceType } from '@/lib/contracts/providerPresets'

export interface SchemaField {
  id: string
  name: string
  type: FieldType
  required: boolean
  description: string
}

export interface ContractParameters {
  dataFrequency: 'real-time' | 'hourly' | '6-hourly' | 'daily'
  deliveryFormat: DeliveryFormat
  historicalWindow: '7d' | '30d' | '90d' | '1y' | '5y'
  region: 'Nigeria' | 'West Africa' | 'Pan-Africa' | 'Global'
  sourceType: StudioSourceType
  sourcePreset: ContractSourcePreset
  sourceUrl: string
}

export interface ValidationError {
  field: string
  message: string
  severity: 'error' | 'warning'
}

export interface FeasibilityPoint {
  period: string
  availability: number
  quality: number
  coverage: number
}

export interface SyntheticRow {
  id: string
  [key: string]: string | number | boolean
}

export interface SourceDocument {
  id: string
  title: string
  source: string
  snippet: string
  relevance: number
  status: 'reading' | 'indexed' | 'cited'
}

export interface StudioAccessState {
  loading: boolean
  featureResolved: boolean
  hasFeatureAccess: boolean
  canManageContracts: boolean
  currentTier: string
  userRole: string | null
}

const DEFAULT_PARAMS: ContractParameters = {
  dataFrequency: 'daily',
  deliveryFormat: 'json',
  historicalWindow: '90d',
  region: 'Nigeria',
  sourceType: 'rss',
  sourcePreset: getDefaultSourcePreset('rss'),
  sourceUrl: '',
}

const DEFAULT_FIELDS: SchemaField[] = [
  {
    id: 'f1',
    name: 'entity_name',
    type: 'string',
    required: true,
    description: 'Name of the tracked entity',
  },
  {
    id: 'f2',
    name: 'signal_date',
    type: 'date',
    required: true,
    description: 'Date of signal occurrence',
  },
  {
    id: 'f3',
    name: 'domain',
    type: 'enum',
    required: true,
    description: 'Sector domain classification',
  },
  {
    id: 'f4',
    name: 'confidence',
    type: 'number',
    required: false,
    description: 'Signal confidence score 0-100',
  },
  {
    id: 'f5',
    name: 'headline',
    type: 'string',
    required: true,
    description: 'One-line signal description',
  },
]

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value))
}

function generateFeasibility(
  query: string,
  sourceCount: number,
  sourceType: StudioSourceType,
): FeasibilityPoint[] {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const seed = query.length % 13
  const sourceLift = Math.min(sourceCount * 2, 16)
  const typeLift = sourceType === 'api' ? 10 : sourceType === 'rss' ? 6 : sourceType === 'webhook' ? 12 : 4

  return months.map((period, index) => ({
    period,
    availability: clamp(48 + seed * 2 + sourceLift + typeLift + index * 1.4, 20, 98),
    quality: clamp(54 + seed * 1.7 + sourceLift + index * 1.2, 20, 98),
    coverage: clamp(42 + seed * 2.1 + sourceLift + index * 1.6, 20, 95),
  }))
}

function generateSyntheticPreview(
  fields: SchemaField[],
  docs: SourceDocument[],
  params: ContractParameters,
): SyntheticRow[] {
  const sourceRows = docs.length > 0 ? docs.slice(0, 5) : [buildConfiguredSourceDoc(params)]

  return sourceRows.map((doc, index) => {
    const row: SyntheticRow = { id: `row-${index + 1}` }
    const words = `${doc.title} ${doc.snippet}`.trim().split(/\s+/).filter(Boolean)

    fields.slice(0, 6).forEach((field, fieldIndex) => {
      switch (field.type) {
        case 'string':
          row[field.name] = fieldIndex === 0
            ? doc.title
            : words.slice(fieldIndex, fieldIndex + 6).join(' ') || doc.source
          break
        case 'number':
          row[field.name] = Math.max(1, Math.round(doc.relevance - fieldIndex * 3))
          break
        case 'boolean':
          row[field.name] = doc.status === 'cited'
          break
        case 'date':
          row[field.name] = new Date().toISOString().slice(0, 10)
          break
        case 'enum':
          row[field.name] = doc.source
          break
      }
    })

    return row
  })
}

function estimateCredits(fields: SchemaField[], params: ContractParameters): number {
  const baseCredits: Record<ContractParameters['dataFrequency'], number> = {
    'real-time': 2400,
    hourly: 480,
    '6-hourly': 180,
    daily: 120,
  }
  const windowMultiplier: Record<ContractParameters['historicalWindow'], number> = {
    '7d': 0.5,
    '30d': 1,
    '90d': 2.2,
    '1y': 6,
    '5y': 22,
  }
  const sourceMultiplier: Record<StudioSourceType, number> = {
    api: 1.15,
    rss: 1,
    scraper: 1.25,
    social: 1.2,
    webhook: 0.8,
  }

  return Math.round(
    baseCredits[params.dataFrequency]
      * windowMultiplier[params.historicalWindow]
      * sourceMultiplier[params.sourceType]
      * (1 + fields.length * 0.08),
  )
}

function buildValidationErrors(
  fields: SchemaField[],
  params: ContractParameters,
  industryId: string,
): ValidationError[] {
  const errors: ValidationError[] = []
  const trimmedSourceUrl = params.sourceUrl.trim()

  if (!industryId) {
    errors.push({
      field: 'industry',
      message: 'Select an industry before validating this contract.',
      severity: 'error',
    })
  }

  if (fields.length === 0) {
    errors.push({
      field: 'schema',
      message: 'At least one schema field is required.',
      severity: 'error',
    })
  }

  if (fields.some((field) => !field.name.trim())) {
    errors.push({
      field: 'field_name',
      message: 'Every schema field needs a name.',
      severity: 'error',
    })
  }

  if (fields.some((field) => field.name.includes(' '))) {
    errors.push({
      field: 'field_name',
      message: 'Field names cannot contain spaces. Use snake_case instead.',
      severity: 'error',
    })
  }

  if (fields.length > 12) {
    errors.push({
      field: 'schema',
      message: 'Schemas with more than 12 fields may impact delivery performance.',
      severity: 'warning',
    })
  }

  if (!trimmedSourceUrl) {
    errors.push({
      field: 'source_url',
      message: 'A source URL is required for live contract activation.',
      severity: 'error',
    })
  } else {
    try {
      const parsed = new URL(trimmedSourceUrl)
      if (!['http:', 'https:'].includes(parsed.protocol)) {
        errors.push({
          field: 'source_url',
          message: 'Source URL must use http or https.',
          severity: 'error',
        })
      }
      if (params.sourceType === 'webhook' && ['localhost', '127.0.0.1'].includes(parsed.hostname)) {
        errors.push({
          field: 'source_url',
          message: 'Webhook targets cannot point at localhost or loopback addresses.',
          severity: 'error',
        })
      }
    } catch {
      errors.push({
        field: 'source_url',
        message: 'Source URL must be a valid absolute URL.',
        severity: 'error',
      })
    }
  }

  return errors
}

function buildSearchQuery(
  nlQuery: string,
  industry: IndustryItem | undefined,
  params: ContractParameters,
) {
  return [
    nlQuery.trim(),
    industry?.name ?? '',
    params.region,
    params.sourceType === 'webhook' ? 'webhook delivery endpoint' : `${params.sourceType} source`,
  ]
    .filter(Boolean)
    .join(' ')
}

function buildConfiguredSourceDoc(params: ContractParameters): SourceDocument {
  return {
    id: 'configured-source',
    title: params.sourceType === 'webhook'
      ? 'Configured webhook destination'
      : `Configured ${getProviderLabel(params.sourcePreset)} endpoint`,
    source: `${params.sourceType.toUpperCase()} · ${getProviderLabel(params.sourcePreset)}`,
    snippet: params.sourceUrl,
    relevance: 100,
    status: 'cited',
  }
}

function mapSearchResultsToDocs(search: SearchResponse): SourceDocument[] {
  const signalDocs = search.results.slice(0, 4).map((item, index) => ({
    id: item.signal_id ?? `signal-doc-${index}`,
    title: item.title ?? 'Untitled intelligence source',
    source: item.source ?? item.signal_type ?? 'Internal signal',
    snippet: item.summary ?? item.source_url ?? 'Signal-backed intelligence result',
    relevance: clamp(Math.round(item.composite_score * 100), 35, 98),
    status: index === 0 ? 'cited' as const : 'indexed' as const,
  }))

  const webDocs = search.web_results.slice(0, Math.max(0, 5 - signalDocs.length)).map((item, index) => ({
    id: `web-doc-${index}`,
    title: item.title ?? 'Web result',
    source: item.source ?? 'Web',
    snippet: item.snippet ?? item.url ?? 'Live web result',
    relevance: clamp(Math.round((item.relevance_score ?? item.confidence ?? 0.6) * 100), 30, 92),
    status: 'indexed' as const,
  }))

  return [...signalDocs, ...webDocs]
}

function mapFrequencyToScheduleTier(
  frequency: ContractParameters['dataFrequency'],
): 'realtime' | 'standard' | 'slow' | 'daily' {
  switch (frequency) {
    case 'real-time':
      return 'realtime'
    case 'hourly':
      return 'standard'
    case '6-hourly':
      return 'slow'
    case 'daily':
    default:
      return 'daily'
  }
}

function mapFrequencyToCron(frequency: ContractParameters['dataFrequency']) {
  switch (frequency) {
    case 'real-time':
      return '*/15 * * * *'
    case 'hourly':
      return '0 * * * *'
    case '6-hourly':
      return '0 */6 * * *'
    case 'daily':
    default:
      return '0 0 * * *'
  }
}

function buildContractName(nlQuery: string, industry: IndustryItem | undefined) {
  const trimmed = nlQuery.trim()
  if (!trimmed) return industry ? `${industry.name} contract` : 'Studio contract'
  const prefix = trimmed.length > 90 ? `${trimmed.slice(0, 87).trim()}...` : trimmed
  return industry ? `${industry.name}: ${prefix}` : prefix
}

export function useContractStudio() {
  const { hasAccess: hasFeatureAccess, loading: featureLoading, currentTier, resolved: featureResolved } =
    useFeatureGate('custom_contracts')

  const [nlQuery, setNlQuery] = useState('')
  const [schemaFields, setSchemaFields] = useState<SchemaField[]>(DEFAULT_FIELDS)
  const [parameters, setParameters] = useState<ContractParameters>(DEFAULT_PARAMS)
  const [step, setStep] = useState<ContractStep>('draft')
  const [isProcessing, setIsProcessing] = useState(false)
  const [isSourceTrayOpen, setIsSourceTrayOpen] = useState(true)
  const [activationError, setActivationError] = useState<string | null>(null)
  const [currentRole, setCurrentRole] = useState<string | null>(null)
  const [accessLoading, setAccessLoading] = useState(true)

  const [contracts, setContracts] = useState<SignalContractResponse[]>([])
  const [contractsLoading, setContractsLoading] = useState(false)
  const [contractActionId, setContractActionId] = useState<string | null>(null)

  const [industries, setIndustries] = useState<IndustryItem[]>([])
  const [industriesLoading, setIndustriesLoading] = useState(true)
  const [industriesError, setIndustriesError] = useState<string | null>(null)
  const [selectedIndustryId, setSelectedIndustryId] = useState('')

  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([])
  const [feasibilityData, setFeasibilityData] = useState<FeasibilityPoint[]>([])
  const [syntheticPreview, setSyntheticPreview] = useState<SyntheticRow[]>([])
  const [sourceDocs, setSourceDocs] = useState<SourceDocument[]>([])
  const [creditEstimate, setCreditEstimate] = useState(0)
  const [lastCreatedContractId, setLastCreatedContractId] = useState<string | null>(null)

  const selectedIndustry = useMemo(
    () => industries.find((industry) => industry.id === selectedIndustryId),
    [industries, selectedIndustryId],
  )

  const canManageContracts = (featureResolved ? hasFeatureAccess : true) && ['admin', 'owner'].includes(currentRole ?? '')

  useEffect(() => {
    let cancelled = false

    async function loadAccess() {
      setAccessLoading(true)
      try {
        const auth = await apiGetCurrentUser()
        if (!cancelled) {
          setCurrentRole(auth.organization.role)
        }
      } catch {
        if (!cancelled) {
          setCurrentRole(null)
        }
      } finally {
        if (!cancelled) {
          setAccessLoading(false)
        }
      }
    }

    loadAccess()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    async function loadIndustries() {
      setIndustriesLoading(true)
      setIndustriesError(null)
      try {
        const data = await getIndustries()
        if (!cancelled) {
          setIndustries(data)
          setSelectedIndustryId((current) => current || data[0]?.id || '')
        }
      } catch (error) {
        if (!cancelled) {
          setIndustries([])
          setIndustriesError(friendlyErrorMessage(error))
        }
      } finally {
        if (!cancelled) {
          setIndustriesLoading(false)
        }
      }
    }

    loadIndustries()
    return () => {
      cancelled = true
    }
  }, [])

  const loadContracts = useCallback(async () => {
    setContractsLoading(true)
    try {
      const data = await apiListContracts({ limit: 50, active_only: false })
      setContracts(data.items)
    } catch {
      setContracts([])
    } finally {
      setContractsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadContracts()
  }, [loadContracts])

  const runValidation = useCallback(async () => {
    if (!nlQuery.trim()) return

    setActivationError(null)
    setStep('validation')
    setIsProcessing(true)
    setFeasibilityData([])
    setSyntheticPreview([])

    const errors = buildValidationErrors(schemaFields, parameters, selectedIndustryId)
    setValidationErrors(errors)
    setCreditEstimate(estimateCredits(schemaFields, parameters))

    if (errors.some((error) => error.severity === 'error')) {
      setSourceDocs([])
      setIsProcessing(false)
      return
    }

    try {
      if (!hasFeatureAccess) {
        setSourceDocs([buildConfiguredSourceDoc(parameters)])
        return
      }

      const search = await executeSearch({
        query: buildSearchQuery(nlQuery, selectedIndustry, parameters),
        max_results: 6,
        include_synthesis: false,
      })
      const docs = mapSearchResultsToDocs(search)
      setSourceDocs(docs.length > 0 ? docs : [buildConfiguredSourceDoc(parameters)])
    } catch {
      setSourceDocs([buildConfiguredSourceDoc(parameters)])
    } finally {
      setIsProcessing(false)
    }
  }, [hasFeatureAccess, nlQuery, parameters, schemaFields, selectedIndustry, selectedIndustryId])

  const runSimulation = useCallback(() => {
    if (validationErrors.some((error) => error.severity === 'error')) return

    setIsProcessing(true)
    setStep('simulation')

    const docsCount = sourceDocs.length > 0 ? sourceDocs.length : 1
    setFeasibilityData(generateFeasibility(nlQuery, docsCount, parameters.sourceType))
    setSyntheticPreview(generateSyntheticPreview(schemaFields, sourceDocs, parameters))
    setCreditEstimate(estimateCredits(schemaFields, parameters))
    setIsProcessing(false)
  }, [nlQuery, parameters, schemaFields, sourceDocs, validationErrors])

  const activateContract = useCallback(async () => {
    if (!canManageContracts) {
      setActivationError('Only admin or owner accounts with custom contracts access can activate this workflow.')
      return
    }

    const errors = buildValidationErrors(schemaFields, parameters, selectedIndustryId)
    if (errors.some((error) => error.severity === 'error')) {
      setValidationErrors(errors)
      setActivationError('Resolve validation issues before activation.')
      setStep('validation')
      return
    }

    try {
      setIsProcessing(true)
      setActivationError(null)

      const created = await apiCreateContract({
        name: buildContractName(nlQuery, selectedIndustry),
        description: `Created in Studio for ${selectedIndustry?.name ?? 'selected industry'}`,
        industry_id: selectedIndustryId,
        source_url: parameters.sourceUrl.trim(),
        source_type: parameters.sourceType,
        refresh_cron: mapFrequencyToCron(parameters.dataFrequency),
        schedule_tier: mapFrequencyToScheduleTier(parameters.dataFrequency),
        extraction_config: {
          ...buildProviderExtractionConfig({
            sourceType: parameters.sourceType,
            preset: parameters.sourcePreset,
            query: nlQuery,
            industryName: selectedIndustry?.name,
            region: parameters.region,
          }),
          nl_query: nlQuery,
          schema_fields: schemaFields,
          studio_parameters: {
            delivery_format: parameters.deliveryFormat,
            historical_window: parameters.historicalWindow,
            region: parameters.region,
            source_preset: parameters.sourcePreset,
          },
          source_documents: sourceDocs.map((doc) => ({
            title: doc.title,
            source: doc.source,
            snippet: doc.snippet,
            relevance: doc.relevance,
          })),
        },
      })

      setContracts((previous) => [created, ...previous.filter((contract) => contract.id !== created.id)])
      setLastCreatedContractId(created.id)
      setStep('active')
    } catch (error) {
      if (isApiError(error) && typeof error.detail === 'object' && error.detail && 'message' in error.detail) {
        setActivationError(String((error.detail as { message?: unknown }).message ?? friendlyErrorMessage(error)))
      } else {
        setActivationError(friendlyErrorMessage(error))
      }
    } finally {
      setIsProcessing(false)
    }
  }, [
    canManageContracts,
    nlQuery,
    parameters,
    schemaFields,
    selectedIndustry,
    selectedIndustryId,
    sourceDocs,
  ])

  const resetContract = useCallback(() => {
    setNlQuery('')
    setSchemaFields(DEFAULT_FIELDS)
    setParameters(DEFAULT_PARAMS)
    setStep('draft')
    setIsProcessing(false)
    setActivationError(null)
    setValidationErrors([])
    setFeasibilityData([])
    setSyntheticPreview([])
    setSourceDocs([])
    setCreditEstimate(0)
    setLastCreatedContractId(null)
  }, [])

  const deleteContractById = useCallback(async (contractId: string) => {
    try {
      setContractActionId(contractId)
      setActivationError(null)
      await apiDeleteContract(contractId)
      setContracts((previous) => previous.filter((contract) => contract.id !== contractId))
      if (lastCreatedContractId === contractId) {
        setLastCreatedContractId(null)
      }
    } catch (error) {
      setActivationError(friendlyErrorMessage(error))
      throw error
    } finally {
      setContractActionId(null)
    }
  }, [lastCreatedContractId])

  const updateContractById = useCallback(async (
    contractId: string,
    patch: {
      name?: string
      description?: string
      source_url?: string
      source_type?: string
      schedule_tier?: string
      extraction_config?: Record<string, unknown>
      is_active?: boolean
    },
  ) => {
    try {
      const updated = await apiUpdateContract(contractId, patch)
      setContracts((previous) => previous.map((contract) => (
        contract.id === contractId ? updated : contract
      )))
      return updated
    } catch (error) {
      throw new Error(friendlyErrorMessage(error))
    }
  }, [])

  const toggleContractActiveById = useCallback(async (contractId: string, isActive: boolean) => {
    try {
      setContractActionId(contractId)
      setActivationError(null)
      const updated = isActive
        ? await apiDeactivateExistingContract(contractId)
        : await apiActivateExistingContract(contractId)
      setContracts((previous) => previous.map((contract) => (
        contract.id === contractId ? updated : contract
      )))
    } catch (error) {
      setActivationError(friendlyErrorMessage(error))
      throw error
    } finally {
      setContractActionId(null)
    }
  }, [])

  const triggerFetchById = useCallback(async (contractId: string) => {
    try {
      setContractActionId(contractId)
      setActivationError(null)
      await apiTriggerContractFetch(contractId)
    } catch (error) {
      setActivationError(friendlyErrorMessage(error))
      throw error
    } finally {
      setContractActionId(null)
    }
  }, [])

  const addField = useCallback(() => {
    const id = `f${Date.now()}`
    setSchemaFields((previous) => [
      ...previous,
      { id, name: '', type: 'string', required: false, description: '' },
    ])
  }, [])

  const updateField = useCallback((id: string, patch: Partial<SchemaField>) => {
    setSchemaFields((previous) => previous.map((field) => (
      field.id === id ? { ...field, ...patch } : field
    )))
  }, [])

  const removeField = useCallback((id: string) => {
    setSchemaFields((previous) => previous.filter((field) => field.id !== id))
  }, [])

  const updateParameter = useCallback(<K extends keyof ContractParameters>(
    key: K,
    value: ContractParameters[K],
  ) => {
    setParameters((previous) => {
      if (key === 'sourceType') {
        const nextSourceType = value as StudioSourceType
        const previousDefaultUrl = getDefaultSourceUrlForPreset(previous.sourcePreset)
        const nextPreset = getDefaultSourcePreset(nextSourceType)
        const nextDefaultUrl = getDefaultSourceUrlForPreset(nextPreset)
        const shouldReplaceUrl = !previous.sourceUrl.trim() || previous.sourceUrl === previousDefaultUrl

        return {
          ...previous,
          sourceType: nextSourceType,
          sourcePreset: nextPreset,
          sourceUrl: shouldReplaceUrl ? nextDefaultUrl : previous.sourceUrl,
        }
      }

      if (key === 'sourcePreset') {
        const nextPreset = value as ContractSourcePreset
        const previousDefaultUrl = getDefaultSourceUrlForPreset(previous.sourcePreset)
        const nextDefaultUrl = getDefaultSourceUrlForPreset(nextPreset)
        const shouldReplaceUrl = !previous.sourceUrl.trim() || previous.sourceUrl === previousDefaultUrl

        return {
          ...previous,
          sourcePreset: nextPreset,
          sourceUrl: shouldReplaceUrl ? nextDefaultUrl : previous.sourceUrl,
        }
      }

      return { ...previous, [key]: value }
    })
  }, [])

  const access: StudioAccessState = {
    loading: featureLoading || accessLoading,
    featureResolved,
    hasFeatureAccess,
    canManageContracts,
    currentTier: currentTier ?? 'explorer',
    userRole: currentRole,
  }

  return {
    nlQuery,
    setNlQuery,
    schemaFields,
    parameters,
    step,
    isProcessing,
    isSourceTrayOpen,
    setIsSourceTrayOpen,
    activationError,
    contracts,
    contractsLoading,
    contractActionId,
    industries,
    industriesLoading,
    industriesError,
    selectedIndustryId,
    setSelectedIndustryId,
    selectedIndustry,
    access,
    validationErrors,
    feasibilityData,
    syntheticPreview,
    sourceDocs,
    creditEstimate,
    lastCreatedContractId,
    runValidation,
    runSimulation,
    activateContract,
    resetContract,
    deleteContractById,
    updateContractById,
    toggleContractActiveById,
    triggerFetchById,
    addField,
    updateField,
    removeField,
    updateParameter,
    reloadContracts: loadContracts,
  }
}
