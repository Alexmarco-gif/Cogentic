'use client'

import React from 'react'
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Coins,
  Loader2,
  PauseCircle,
  PlayCircle,
  RefreshCw,
  ShieldAlert,
  Table2,
  Trash2,
  Sparkles,
} from 'lucide-react'

import type { SignalContractResponse } from '@/lib/api/types'
import { FeasibilityPanel } from './FeasibilityPanel'
import type {
  ContractStep,
  FeasibilityPoint,
  SchemaField,
  StudioAccessState,
  SyntheticRow,
  ValidationError,
} from '@/lib/hooks/useContractStudio'

function AccessNotice({ access }: { access: StudioAccessState }) {
  if (access.loading) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-border bg-surface p-4">
        <Loader2 className="h-4 w-4 animate-spin text-primary" />
        <div>
          <p className="text-sm font-medium text-heading">Checking Studio access</p>
          <p className="text-xs text-subtle">Loading your role and plan entitlements...</p>
        </div>
      </div>
    )
  }

  if (!access.hasFeatureAccess) {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <ShieldAlert className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
        <div>
          <p className="text-sm font-medium text-amber-700">Studio requires custom contracts access</p>
          <p className="mt-1 text-xs text-amber-600">
            Your current plan is <span className="font-semibold">{access.currentTier}</span>. Upgrade to a tier that includes
            custom contracts before activating Studio-created workflows.
          </p>
        </div>
      </div>
    )
  }

  if (!access.canManageContracts) {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <ShieldAlert className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
        <div>
          <p className="text-sm font-medium text-amber-700">Admin or owner role required</p>
          <p className="mt-1 text-xs text-amber-600">
            Your current role is <span className="font-semibold">{access.userRole ?? 'unknown'}</span>. You can review the Studio flow,
            but only admin or owner accounts can activate, pause, fetch, or delete contracts.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
      <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-emerald-600" />
      <div>
        <p className="text-sm font-medium text-emerald-700">Studio ready for contract activation</p>
        <p className="text-xs text-emerald-600">Your role and plan allow full contract lifecycle actions.</p>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 px-8 py-10 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl border-2 border-dashed border-border bg-muted">
        <Sparkles className="h-7 w-7 text-subtle" />
      </div>
      <div>
        <p className="text-sm font-medium text-heading">Define your contract</p>
        <p className="mt-1 text-xs leading-relaxed text-subtle">
          Choose an industry, set the live source, describe the data you need, then validate and simulate before activation.
        </p>
      </div>
    </div>
  )
}

function ValidationView({
  errors,
  isProcessing,
  canSimulate,
  onRunSimulation,
}: {
  errors: ValidationError[]
  isProcessing: boolean
  canSimulate: boolean
  onRunSimulation: () => void
}) {
  if (isProcessing) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 py-12">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/8">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-heading">Running validation</p>
          <p className="mt-0.5 text-xs text-subtle">Checking source shape, schema inputs, and activation prerequisites...</p>
        </div>
      </div>
    )
  }

  const errorItems = errors.filter((error) => error.severity === 'error')
  const warningItems = errors.filter((error) => error.severity === 'warning')
  const isClean = errors.length === 0

  return (
    <div className="flex flex-col gap-5 p-5">
      {isClean ? (
        <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-emerald-600" />
          <div>
            <p className="text-sm font-medium text-emerald-700">Validation passed</p>
            <p className="text-xs text-emerald-600">Schema, source, and contract prerequisites look ready for simulation.</p>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
          <p className="text-sm font-medium text-rose-700">
            {errorItems.length} error{errorItems.length !== 1 ? 's' : ''}
            {warningItems.length > 0 && `, ${warningItems.length} warning${warningItems.length !== 1 ? 's' : ''}`}
          </p>
          <p className="mt-0.5 text-xs text-rose-500">Fix the issues below before moving to simulation.</p>
        </div>
      )}

      {errorItems.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-subtle">Errors</p>
          {errorItems.map((error, index) => (
            <div key={`${error.field}-${index}`} className="flex items-start gap-2 rounded-lg border border-rose-100 bg-rose-50/60 px-3 py-2">
              <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-rose-500" />
              <div>
                {error.field && <p className="font-mono text-[10px] font-medium text-rose-700">{error.field}</p>}
                <p className="text-xs text-rose-600">{error.message}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {warningItems.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-subtle">Warnings</p>
          {warningItems.map((warning, index) => (
            <div key={`${warning.field}-${index}`} className="flex items-start gap-2 rounded-lg border border-amber-100 bg-amber-50/60 px-3 py-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-500" />
              <div>
                {warning.field && <p className="font-mono text-[10px] font-medium text-amber-700">{warning.field}</p>}
                <p className="text-xs text-amber-600">{warning.message}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      <button
        onClick={onRunSimulation}
        disabled={!canSimulate}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-2.5 text-sm font-medium text-white transition-all hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-40"
      >
        Run Simulation
      </button>
    </div>
  )
}

function CreditCard({ estimate }: { estimate: number }) {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-border bg-surface p-4 shadow-card">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50">
        <Coins className="h-5 w-5 text-amber-500" />
      </div>
      <div className="flex-1">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-subtle">Estimated monthly cost</p>
        <p className="mt-0.5 text-2xl font-semibold tabular-nums text-heading">
          {estimate.toLocaleString()}<span className="ml-1 text-sm font-medium text-subtle">credits</span>
        </p>
      </div>
      <div className="text-right">
        <p className="text-[10px] text-subtle">Data quality</p>
        <p className="text-sm font-medium text-primary">High</p>
      </div>
    </div>
  )
}

function PreviewTable({
  fields,
  rows,
}: {
  fields: SchemaField[]
  rows: SyntheticRow[]
}) {
  if (fields.length === 0 || rows.length === 0) return null

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <Table2 className="h-4 w-4 text-subtle" />
        <p className="text-xs font-medium text-heading">Synthetic preview</p>
        <span className="ml-auto text-[10px] text-subtle">{rows.length} sample rows</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border bg-muted">
              {fields.map((field) => (
                <th key={field.id} className="whitespace-nowrap px-3 py-2 text-left font-medium text-subtle">
                  {field.name}
                  {field.required && <span className="ml-0.5 text-rose-400">*</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={row.id} className={rowIndex % 2 === 0 ? 'bg-surface' : 'bg-muted/40'}>
                {fields.map((field) => (
                  <td key={field.id} className="whitespace-nowrap px-3 py-2 text-body">
                    {String(row[field.name] ?? '-')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ActiveView({
  fields,
  rows,
  creditEstimate,
}: {
  fields: SchemaField[]
  rows: SyntheticRow[]
  creditEstimate: number
}) {
  return (
    <div className="flex flex-col gap-5 p-5">
      <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-emerald-600" />
        <div>
          <p className="text-sm font-medium text-emerald-700">Contract active</p>
          <p className="text-xs text-emerald-600">The contract is live and ready for its next scheduled fetch cycle.</p>
        </div>
        <span className="ml-auto flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-100 px-2 py-0.5 text-[9px] font-semibold text-emerald-700">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-600" />
          </span>
          Live
        </span>
      </div>

      <CreditCard estimate={creditEstimate} />
      <PreviewTable fields={fields} rows={rows} />
    </div>
  )
}

function ContractList({
  contracts,
  contractsLoading,
  contractActionId,
  lastCreatedContractId,
  canManageContracts,
  onDeleteContract,
  onToggleContractActive,
  onTriggerContractFetch,
}: {
  contracts: SignalContractResponse[]
  contractsLoading: boolean
  contractActionId: string | null
  lastCreatedContractId: string | null
  canManageContracts: boolean
  onDeleteContract: (id: string) => Promise<void>
  onToggleContractActive: (id: string, isActive: boolean) => Promise<void>
  onTriggerContractFetch: (id: string) => Promise<void>
}) {
  return (
    <div className="border-t border-border p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium text-heading">Live contracts</h3>
          <p className="text-[10px] text-subtle">Existing contracts available for fetch, pause, resume, or deletion.</p>
        </div>
        {contractsLoading && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
      </div>

      {contracts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-surface p-4 text-xs text-subtle">
          No contracts created yet. Activate your first Studio contract to see it here.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
          {contracts.slice(0, 8).map((contract) => {
            const isBusy = contractActionId === contract.id
            const isNew = lastCreatedContractId === contract.id
            return (
              <div key={contract.id} className="rounded-xl border border-border bg-surface p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-medium text-heading">{contract.name}</p>
                      {isNew && (
                        <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[9px] font-semibold text-emerald-700">
                          New
                        </span>
                      )}
                    </div>
                    <p className="mt-1 line-clamp-2 text-[11px] text-subtle">
                      {contract.description ?? contract.source_url}
                    </p>
                  </div>
                  <span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${
                    contract.is_active
                      ? 'bg-emerald-50 text-emerald-700'
                      : 'bg-slate-100 text-slate-700'
                  }`}>
                    {contract.is_active ? 'Active' : 'Paused'}
                  </span>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px] text-subtle">
                  <span className="rounded-full bg-muted px-2 py-0.5">{contract.source_type}</span>
                  <span className="rounded-full bg-muted px-2 py-0.5">{contract.schedule_tier}</span>
                  <span className="rounded-full bg-muted px-2 py-0.5">Failures: {contract.failure_count}</span>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    onClick={() => void onTriggerContractFetch(contract.id)}
                    disabled={!canManageContracts || !contract.is_active || isBusy}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-[11px] font-medium text-body transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <RefreshCw className={`h-3 w-3 ${isBusy ? 'animate-spin' : ''}`} />
                    Fetch now
                  </button>
                  <button
                    onClick={() => void onToggleContractActive(contract.id, contract.is_active)}
                    disabled={!canManageContracts || isBusy}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-[11px] font-medium text-body transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {contract.is_active ? (
                      <>
                        <PauseCircle className="h-3 w-3" />
                        Pause
                      </>
                    ) : (
                      <>
                        <PlayCircle className="h-3 w-3" />
                        Resume
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => void onDeleteContract(contract.id)}
                    disabled={!canManageContracts || isBusy}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-[11px] font-medium text-rose-600 transition-colors hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <Trash2 className="h-3 w-3" />
                    Delete
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

interface IntelligencePaneProps {
  step: ContractStep
  isProcessing: boolean
  access: StudioAccessState
  validationErrors: ValidationError[]
  feasibilityData: FeasibilityPoint[]
  syntheticPreview: SyntheticRow[]
  schemaFields: SchemaField[]
  creditEstimate: number
  contracts: SignalContractResponse[]
  contractsLoading: boolean
  contractActionId: string | null
  lastCreatedContractId: string | null
  onRunSimulation: () => void
  onActivate: () => Promise<void>
  onDeleteContract: (id: string) => Promise<void>
  onToggleContractActive: (id: string, isActive: boolean) => Promise<void>
  onTriggerContractFetch: (id: string) => Promise<void>
  activationError?: string | null
}

export function IntelligencePane({
  step,
  isProcessing,
  access,
  validationErrors,
  feasibilityData,
  syntheticPreview,
  schemaFields,
  creditEstimate,
  contracts,
  contractsLoading,
  contractActionId,
  lastCreatedContractId,
  onRunSimulation,
  onActivate,
  onDeleteContract,
  onToggleContractActive,
  onTriggerContractFetch,
  activationError,
}: IntelligencePaneProps) {
  const [activating, setActivating] = React.useState(false)
  const canSimulate = validationErrors.every((error) => error.severity !== 'error')

  const handleActivate = async () => {
    setActivating(true)
    try {
      await onActivate()
    } finally {
      setActivating(false)
    }
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-canvas">
      <div className="flex-shrink-0 border-b border-border px-5 py-3">
        <h2 className="text-sm font-medium text-heading">Intelligence Preview</h2>
        <p className="text-[10px] text-subtle">Validation, simulation, activation, and live contract controls</p>
      </div>

      <div className="flex flex-1 flex-col">
        <div className="flex flex-col gap-5 p-5">
          <AccessNotice access={access} />

          {step === 'draft' && <EmptyState />}

          {step === 'validation' && (
            <ValidationView
              errors={validationErrors}
              isProcessing={isProcessing}
              canSimulate={canSimulate}
              onRunSimulation={onRunSimulation}
            />
          )}

          {step === 'simulation' && (
            <div className="flex flex-col gap-5">
              {isProcessing ? (
                <div className="flex flex-col items-center justify-center gap-3 py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <p className="text-sm font-medium text-heading">Running simulation...</p>
                  <p className="text-xs text-subtle">Generating feasibility scores and synthetic data preview.</p>
                </div>
              ) : (
                <>
                  {feasibilityData.length > 0 && <FeasibilityPanel data={feasibilityData} />}
                  <CreditCard estimate={creditEstimate} />
                  <PreviewTable fields={schemaFields} rows={syntheticPreview} />
                  <button
                    onClick={() => void handleActivate()}
                    disabled={!access.canManageContracts || activating}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-2.5 text-sm font-medium text-white transition-all hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {activating ? 'Activating...' : 'Activate Contract'}
                  </button>
                  {activationError && (
                    <p className="text-center text-xs text-rose-500">{activationError}</p>
                  )}
                </>
              )}
            </div>
          )}

          {step === 'active' && (
            <ActiveView
              fields={schemaFields}
              rows={syntheticPreview}
              creditEstimate={creditEstimate}
            />
          )}
        </div>

        <ContractList
          contracts={contracts}
          contractsLoading={contractsLoading}
          contractActionId={contractActionId}
          lastCreatedContractId={lastCreatedContractId}
          canManageContracts={access.canManageContracts}
          onDeleteContract={onDeleteContract}
          onToggleContractActive={onToggleContractActive}
          onTriggerContractFetch={onTriggerContractFetch}
        />
      </div>
    </div>
  )
}
