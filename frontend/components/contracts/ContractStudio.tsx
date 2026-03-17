'use client'

import { LifecycleTracker } from './LifecycleTracker'
import { DefinitionPane }   from './DefinitionPane'
import { IntelligencePane } from './IntelligencePane'
import { SourceTray }       from './SourceTray'
import type { IndustryItem } from '@/lib/api/discovered_sources'
import type { SignalContractResponse } from '@/lib/api/types'
import type {
  ContractStep,
  SchemaField,
  ContractParameters,
  ValidationError,
  FeasibilityPoint,
  SyntheticRow,
  SourceDocument,
  StudioAccessState,
} from '@/lib/hooks/useContractStudio'

// ── Props (mirrors useContractStudio return) ──────────────────────────────────

export interface ContractStudioProps {
  // NL query
  nlQuery: string
  onNlQueryChange: (v: string) => void
  // Schema
  schemaFields: SchemaField[]
  onAddField: () => void
  onUpdateField: (id: string, patch: Partial<SchemaField>) => void
  onRemoveField: (id: string) => void
  // Industry
  industries: IndustryItem[]
  industriesLoading: boolean
  industriesError?: string | null
  selectedIndustryId: string
  onIndustryChange: (id: string) => void
  // Parameters
  parameters: ContractParameters
  onUpdateParameter: <K extends keyof ContractParameters>(k: K, v: ContractParameters[K]) => void
  // Lifecycle
  step: ContractStep
  isProcessing: boolean
  access: StudioAccessState
  // Actions
  onRunValidation: () => void
  onRunSimulation: () => void
  onActivate: () => Promise<void>
  onReset: () => void
  onDeleteContract: (id: string) => Promise<void>
  onToggleContractActive: (id: string, isActive: boolean) => Promise<void>
  onTriggerContractFetch: (id: string) => Promise<void>
  // Intelligence
  validationErrors: ValidationError[]
  feasibilityData: FeasibilityPoint[]
  syntheticPreview: SyntheticRow[]
  creditEstimate: number
  activationError?: string | null
  contracts: SignalContractResponse[]
  contractsLoading: boolean
  contractActionId: string | null
  lastCreatedContractId: string | null
  // Sources
  sourceDocs: SourceDocument[]
  isSourceTrayOpen: boolean
  onToggleSourceTray: () => void
}

// ── Root layout ───────────────────────────────────────────────────────────────

export function ContractStudio({
  nlQuery,
  onNlQueryChange,
  schemaFields,
  onAddField,
  onUpdateField,
  onRemoveField,
  industries,
  industriesLoading,
  industriesError,
  selectedIndustryId,
  onIndustryChange,
  parameters,
  onUpdateParameter,
  step,
  isProcessing,
  access,
  onRunValidation,
  onRunSimulation,
  onActivate,
  onReset,
  onDeleteContract,
  onToggleContractActive,
  onTriggerContractFetch,
  validationErrors,
  feasibilityData,
  syntheticPreview,
  creditEstimate,
  activationError,
  contracts,
  contractsLoading,
  contractActionId,
  lastCreatedContractId,
  sourceDocs,
  isSourceTrayOpen,
  onToggleSourceTray,
}: ContractStudioProps) {
  return (
    <div
      className="flex flex-col bg-canvas"
      style={{ minHeight: 'calc(100vh - var(--omnibar-height))' }}
    >
      {/* ── Step tracker ──────────────────────────────────────────────────── */}
      <LifecycleTracker currentStep={step} isProcessing={isProcessing} />

      {/* ── Split pane row ─────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-visible lg:flex-row lg:overflow-hidden">
        {/* Left: DefinitionPane */}
        <div className="w-full overflow-hidden lg:w-[40%]">
          <DefinitionPane
            nlQuery={nlQuery}
            onNlQueryChange={onNlQueryChange}
            schemaFields={schemaFields}
            industries={industries}
            industriesLoading={industriesLoading}
            industriesError={industriesError}
            selectedIndustryId={selectedIndustryId}
            onIndustryChange={onIndustryChange}
            parameters={parameters}
            step={step}
            isProcessing={isProcessing}
            onRunValidation={onRunValidation}
            onReset={onReset}
            onAddField={onAddField}
            onUpdateField={onUpdateField}
            onRemoveField={onRemoveField}
            onUpdateParameter={onUpdateParameter}
          />
        </div>

        {/* Right: IntelligencePane */}
        <div className="flex-1 overflow-hidden">
          <IntelligencePane
            step={step}
            isProcessing={isProcessing}
            access={access}
            validationErrors={validationErrors}
            feasibilityData={feasibilityData}
            syntheticPreview={syntheticPreview}
            schemaFields={schemaFields}
            creditEstimate={creditEstimate}
            contracts={contracts}
            contractsLoading={contractsLoading}
            contractActionId={contractActionId}
            lastCreatedContractId={lastCreatedContractId}
            onRunSimulation={onRunSimulation}
            onActivate={onActivate}
            onDeleteContract={onDeleteContract}
            onToggleContractActive={onToggleContractActive}
            onTriggerContractFetch={onTriggerContractFetch}
            activationError={activationError}
          />
        </div>
      </div>

      {/* ── Source tray ────────────────────────────────────────────────────── */}
      <SourceTray
        docs={sourceDocs}
        isOpen={isSourceTrayOpen}
        onToggle={onToggleSourceTray}
        isProcessing={isProcessing}
      />
    </div>
  )
}
