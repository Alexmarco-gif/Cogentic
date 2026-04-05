'use client'

import { Plus, Trash2, ChevronDown, Play, RotateCcw, Sparkles } from 'lucide-react'
import type {
  DeliveryFormat,
  SchemaField,
  FieldType,
  ContractParameters,
  ContractStep,
  StudioSourceType,
} from '@/lib/hooks/useContractStudio'
import type { IndustryItem } from '@/lib/api/discovered_sources'
import {
  getProviderOptions,
  getSourcePlaceholder,
  getSourcePresetDescription,
} from '@/lib/contracts/providerPresets'

// ── Field type options ────────────────────────────────────────────────────────

const FIELD_TYPES: { value: FieldType; label: string }[] = [
  { value: 'string',  label: 'String'  },
  { value: 'number',  label: 'Number'  },
  { value: 'date',    label: 'Date'    },
  { value: 'boolean', label: 'Boolean' },
  { value: 'enum',    label: 'Enum'    },
]

// ── Parameter options ─────────────────────────────────────────────────────────

const FREQUENCY_OPTIONS: ContractParameters['dataFrequency'][] = ['real-time', 'hourly', '6-hourly', 'daily']
const FORMAT_OPTIONS: DeliveryFormat[] = ['json', 'csv', 'parquet']
const WINDOW_OPTIONS:    ContractParameters['historicalWindow'][] = ['7d', '30d', '90d', '1y', '5y']
const REGION_OPTIONS:    ContractParameters['region'][] = ['Nigeria', 'West Africa', 'Pan-Africa', 'Global']
const SOURCE_TYPE_OPTIONS: StudioSourceType[] = ['api', 'rss', 'scraper', 'social', 'webhook']

// ── Select widget ─────────────────────────────────────────────────────────────

function SelectField<T extends string>({
  value,
  options,
  onChange,
  small,
}: {
  value: T
  options: T[]
  onChange: (v: T) => void
  small?: boolean
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={e => onChange(e.target.value as T)}
        className={`w-full appearance-none rounded-lg border border-border bg-muted pr-7 text-body focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/20 ${small ? 'py-1 pl-2 text-[11px]' : 'py-1.5 pl-2.5 text-xs'}`}
      >
        {options.map(o => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-subtle" />
    </div>
  )
}

// ── Schema row ────────────────────────────────────────────────────────────────

function SchemaRow({
  field,
  onUpdate,
  onRemove,
  isLocked,
}: {
  field: SchemaField
  onUpdate: (id: string, patch: Partial<SchemaField>) => void
  onRemove: (id: string) => void
  isLocked: boolean
}) {
  return (
    <div className="grid grid-cols-[1fr_80px_28px_28px] items-center gap-1.5">
      <input
        value={field.name}
        onChange={e => onUpdate(field.id, { name: e.target.value })}
        placeholder="field_name"
        disabled={isLocked}
        className="rounded-lg border border-border bg-muted px-2 py-1 font-mono text-[11px] placeholder:text-subtle focus:border-primary/50 focus:outline-none disabled:opacity-40"
      />
      <SelectField
        value={field.type}
        options={FIELD_TYPES.map(t => t.value) as FieldType[]}
        onChange={v => onUpdate(field.id, { type: v })}
        small
      />
      {/* Required toggle */}
      <button
        onClick={() => onUpdate(field.id, { required: !field.required })}
        disabled={isLocked}
        title={field.required ? 'Required' : 'Optional'}
        className={`flex h-6 w-6 items-center justify-center rounded border text-[9px] font-semibold transition-colors ${
          field.required
            ? 'border-primary/30 bg-primary/10 text-primary'
            : 'border-border bg-surface text-subtle'
        } disabled:opacity-40`}
      >
        {field.required ? 'R' : 'O'}
      </button>
      <button
        onClick={() => onRemove(field.id)}
        disabled={isLocked}
        className="flex h-6 w-6 items-center justify-center rounded text-subtle transition-colors hover:bg-rose-50 hover:text-rose-500 disabled:opacity-40"
      >
        <Trash2 className="h-3 w-3" />
      </button>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

interface DefinitionPaneProps {
  nlQuery: string
  onNlQueryChange: (v: string) => void
  schemaFields: SchemaField[]
  parameters: ContractParameters
  industries: IndustryItem[]
  industriesLoading: boolean
  industriesError?: string | null
  selectedIndustryId: string
  onIndustryChange: (id: string) => void
  step: ContractStep
  isProcessing: boolean
  onRunValidation: () => void
  onReset: () => void
  onAddField: () => void
  onUpdateField: (id: string, patch: Partial<SchemaField>) => void
  onRemoveField: (id: string) => void
  onUpdateParameter: <K extends keyof ContractParameters>(k: K, v: ContractParameters[K]) => void
}

export function DefinitionPane({
  nlQuery,
  onNlQueryChange,
  schemaFields,
  parameters,
  industries,
  industriesLoading,
  industriesError,
  selectedIndustryId,
  onIndustryChange,
  step,
  isProcessing,
  onRunValidation,
  onReset,
  onAddField,
  onUpdateField,
  onRemoveField,
  onUpdateParameter,
}: DefinitionPaneProps) {
  const isLocked = step !== 'draft' || isProcessing
  const canRun = (
    nlQuery.trim().length > 10
    && !!selectedIndustryId
    && parameters.sourceUrl.trim().length > 0
    && !isProcessing
    && step === 'draft'
  )
  const sourceUrlLabel = parameters.sourceType === 'webhook' ? 'Webhook Endpoint URL' : 'Source URL'
  const sourceUrlPlaceholder = getSourcePlaceholder(parameters.sourceType, parameters.sourcePreset)
  const providerOptions = getProviderOptions(parameters.sourceType)

  return (
    <div className="flex h-full flex-col overflow-hidden border-r border-border">
      {/* ── Pane header ──────────────────────────────────────────────────── */}
      <div className="flex flex-shrink-0 items-center justify-between border-b border-border px-5 py-3">
        <div>
          <h2 className="text-sm font-medium text-heading">Contract Definition</h2>
          <p className="text-[10px] text-subtle">Natural language → structured data contract</p>
        </div>
        {step !== 'draft' && (
          <button
            onClick={onReset}
            className="flex items-center gap-1 text-[10px] text-subtle hover:text-rose-500"
          >
            <RotateCcw className="h-3 w-3" />
            Reset
          </button>
        )}
      </div>

      {/* ── Scrollable body ──────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col gap-5 overflow-y-auto px-5 py-5">

        {/* Industry */} 
        <div>
          <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-subtle">
            Industry
          </label>
          <div className="relative">
            <select
              value={selectedIndustryId}
              onChange={(e) => onIndustryChange(e.target.value)}
              disabled={isLocked || industriesLoading || industries.length === 0}
              className="w-full appearance-none rounded-xl border border-border bg-muted px-3 py-2.5 text-xs text-body focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/20 disabled:opacity-50"
            >
              <option value="">
                {industriesLoading ? 'Loading industries...' : 'Select an industry'}
              </option>
              {industries.map((industry) => (
                <option key={industry.id} value={industry.id}>
                  {industry.name}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-3 w-3 -translate-y-1/2 text-subtle" />
          </div>
          {industriesError && (
            <p className="mt-1 text-[10px] text-rose-500">{industriesError}</p>
          )}
        </div>

        {/* NL Query textarea */}
        <div>
          <label className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-subtle">
            <Sparkles className="h-3 w-3 text-primary" />
            Define in plain language
          </label>
          <textarea
            value={nlQuery}
            onChange={e => onNlQueryChange(e.target.value)}
            disabled={isLocked}
            rows={5}
            placeholder={`Describe what data you need…\n\nExample: "Daily agricultural commodity prices for maize, sorghum, and rice across a target region with 90-day historical window, delivered as JSON."`}
            className="w-full resize-none rounded-xl border border-border bg-muted p-3 text-xs leading-relaxed text-body placeholder:text-subtle/70 focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/20 disabled:opacity-50"
          />
          <p className="mt-1 text-right text-[9px] text-subtle">{nlQuery.length} chars</p>
        </div>

        {/* Schema builder */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className="text-[10px] font-semibold uppercase tracking-wider text-subtle">
              Schema Fields
              <span className="ml-1.5 rounded-pill bg-muted px-1.5 py-0.5 text-[9px] font-medium text-data">
                {schemaFields.length}
              </span>
            </label>
            <button
              onClick={onAddField}
              disabled={isLocked}
              className="flex items-center gap-1 text-[10px] font-medium text-primary hover:underline disabled:opacity-40"
            >
              <Plus className="h-3 w-3" />
              Add field
            </button>
          </div>

          {/* Column headers */}
          <div className="mb-1.5 grid grid-cols-[1fr_80px_28px_28px] gap-1.5 text-[9px] font-semibold uppercase tracking-wider text-subtle">
            <span>Name</span>
            <span>Type</span>
            <span className="text-center">Req</span>
            <span />
          </div>

          <div className="flex flex-col gap-1.5">
            {schemaFields.map(f => (
              <SchemaRow
                key={f.id}
                field={f}
                onUpdate={onUpdateField}
                onRemove={onRemoveField}
                isLocked={isLocked}
              />
            ))}
            {schemaFields.length === 0 && (
              <p className="py-3 text-center text-xs text-subtle">No fields — add one above</p>
            )}
          </div>
        </div>

        {/* Parameters */}
        <div>
          <label className="mb-2 block text-[10px] font-semibold uppercase tracking-wider text-subtle">
            Delivery Parameters
          </label>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {[
              { label: 'Frequency',  key: 'dataFrequency',  options: FREQUENCY_OPTIONS  },
              { label: 'Format',     key: 'deliveryFormat', options: FORMAT_OPTIONS     },
              { label: 'History',    key: 'historicalWindow',options: WINDOW_OPTIONS    },
              { label: 'Region',     key: 'region',         options: REGION_OPTIONS     },
            ].map(p => (
              <div key={p.key}>
                <p className="mb-1 text-[9px] text-subtle">{p.label}</p>
                <SelectField
                  value={parameters[p.key as keyof ContractParameters]}
                  options={p.options as string[]}
                  onChange={v => onUpdateParameter(p.key as keyof ContractParameters, v as never)}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Source configuration */}
        <div>
          <label className="mb-2 block text-[10px] font-semibold uppercase tracking-wider text-subtle">
            Source Configuration
          </label>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div>
              <p className="mb-1 text-[9px] text-subtle">Source type</p>
              <SelectField
                value={parameters.sourceType}
                options={SOURCE_TYPE_OPTIONS}
                onChange={(value) => onUpdateParameter('sourceType', value)}
              />
            </div>
            <div>
              <p className="mb-1 text-[9px] text-subtle">Provider preset</p>
              <SelectField
                value={parameters.sourcePreset}
                options={providerOptions.map((option) => option.value)}
                onChange={(value) => onUpdateParameter('sourcePreset', value)}
              />
            </div>
            <div className="sm:col-span-1">
              <p className="mb-1 text-[9px] text-subtle">{sourceUrlLabel}</p>
              <input
                type="url"
                value={parameters.sourceUrl}
                onChange={(e) => onUpdateParameter('sourceUrl', e.target.value)}
                disabled={isLocked}
                placeholder={sourceUrlPlaceholder}
                className="w-full rounded-lg border border-border bg-muted px-2.5 py-1.5 text-xs placeholder:text-subtle/70 focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/20 disabled:opacity-40"
              />
            </div>
          </div>
          <p className="mt-1 text-[9px] text-subtle">
            {parameters.sourceType === 'webhook'
              ? 'Webhook contracts deliver new signals to your endpoint after ingestion.'
              : getSourcePresetDescription(parameters.sourceType, parameters.sourcePreset)}
          </p>
        </div>
      </div>

      {/* ── Footer CTA ───────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 border-t border-border bg-surface px-5 py-4">
        <button
          onClick={onRunValidation}
          disabled={!canRun}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-2.5 text-sm font-medium text-white transition-all hover:bg-primary-hover active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Play className="h-4 w-4" />
          {isProcessing ? 'Processing…' : 'Run Validation'}
        </button>
      </div>
    </div>
  )
}
