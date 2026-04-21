'use client'

import { Check, Circle, ArrowRight } from 'lucide-react'
import type { ContractStep } from '@/lib/hooks/useContractStudio'

// ── Step definitions ──────────────────────────────────────────────────────────

interface Step {
  id: ContractStep
  label: string
  description: string
}

const STEPS: Step[] = [
  { id: 'draft',      label: 'Define',     description: 'Natural language + schema' },
  { id: 'validation', label: 'Validate',   description: 'Requirements & evidence check' },
  { id: 'simulation', label: 'Review',     description: 'Preview rows & launch plan' },
  { id: 'active',     label: 'Activate',   description: 'Contract is live' },
]

const STEP_ORDER: ContractStep[] = ['draft', 'validation', 'simulation', 'active']

type StepStatus = 'completed' | 'active' | 'pending'

function getStatus(step: ContractStep, current: ContractStep): StepStatus {
  const stepIdx    = STEP_ORDER.indexOf(step)
  const currentIdx = STEP_ORDER.indexOf(current)
  if (stepIdx < currentIdx) return 'completed'
  if (stepIdx === currentIdx) return 'active'
  return 'pending'
}

// ── Sub-component: StepNode ───────────────────────────────────────────────────

function StepNode({
  step,
  status,
  isLast,
}: {
  step: Step
  status: StepStatus
  isLast: boolean
}) {
  return (
    <div className="flex flex-1 items-center">
      <div className="flex flex-col items-center">
        {/* Circle indicator */}
        <div
          className={`relative flex h-8 w-8 items-center justify-center rounded-full border-2 transition-all duration-300 ${
            status === 'completed'
              ? 'border-primary bg-primary text-white'
              : status === 'active'
              ? 'border-primary bg-white text-primary shadow-[0_0_0_4px_rgba(79,70,229,0.12)]'
              : 'border-border bg-surface text-subtle'
          }`}
        >
          {status === 'completed' ? (
            <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
          ) : status === 'active' ? (
            <Circle className="h-2.5 w-2.5 fill-current" />
          ) : (
            <span className="text-[10px] font-medium">
              {STEP_ORDER.indexOf(step.id) + 1}
            </span>
          )}

          {/* Pulse ring on active step */}
          {status === 'active' && (
            <span className="absolute inset-0 animate-ping rounded-full bg-primary/20" />
          )}
        </div>

        {/* Label + description */}
        <div className="mt-2 text-center">
          <p
            className={`text-[11px] font-semibold transition-colors ${
              status === 'active'   ? 'text-primary'
              : status === 'completed' ? 'text-heading'
              : 'text-subtle'
            }`}
          >
            {step.label}
          </p>
          <p className="text-[9px] text-subtle">{step.description}</p>
        </div>
      </div>

      {/* Connector line */}
      {!isLast && (
        <div className="relative mx-3 flex-1 pb-6">
          <div className={`h-px w-full transition-colors duration-500 ${
            status === 'completed' ? 'bg-primary' : 'bg-border'
          }`} />
          <ArrowRight
            className={`absolute -right-1 -top-2 h-4 w-4 transition-colors ${
              status === 'completed' ? 'text-primary' : 'text-border'
            }`}
          />
        </div>
      )}
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

interface LifecycleTrackerProps {
  currentStep: ContractStep
  isProcessing?: boolean
}

export function LifecycleTracker({ currentStep, isProcessing }: LifecycleTrackerProps) {
  return (
    <div className="flex items-start border-b border-border bg-surface px-8 py-4">
      {STEPS.map((step, i) => (
        <StepNode
          key={step.id}
          step={step}
          status={getStatus(step.id, currentStep)}
          isLast={i === STEPS.length - 1}
        />
      ))}

      {/* Processing pill */}
      {isProcessing && (
        <div className="ml-auto flex flex-shrink-0 items-center gap-1.5 self-start rounded-pill border border-primary/20 bg-primary/5 px-3 py-1 text-xs text-primary">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary" />
          </span>
          Processing…
        </div>
      )}
    </div>
  )
}
