'use client'

import { cn } from '@/lib/utils'
import { Check, Loader2 } from 'lucide-react'
import type { ProcessStep } from '@/lib/hooks/useInvestigate'

interface ProcessTrackerProps {
  steps: ProcessStep[]
}

export function ProcessTracker({ steps }: ProcessTrackerProps) {
  return (
    <div className="flex flex-col gap-1 py-2">
      {steps.map((step, i) => (
        <ProcessStepRow key={step.id} step={step} index={i} />
      ))}
    </div>
  )
}

function ProcessStepRow({ step, index }: { step: ProcessStep; index: number }) {
  const isPending  = step.status === 'pending'
  const isActive   = step.status === 'active'
  const isComplete = step.status === 'complete'

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-300',
        isActive   && 'bg-primary/5 border border-primary/10',
        isComplete && 'opacity-60',
        isPending  && 'opacity-30',
      )}
    >
      {/* Step icon */}
      <div
        className={cn(
          'w-5 h-5 rounded-full flex items-center justify-center shrink-0 transition-all duration-300',
          isComplete && 'bg-emerald-100 text-emerald-600',
          isActive   && 'bg-primary/10 text-primary',
          isPending  && 'bg-muted text-subtle',
        )}
      >
        {isComplete && <Check size={11} strokeWidth={2.5} />}
        {isActive   && <Loader2 size={11} className="animate-spin" />}
        {isPending  && (
          <span className="text-[9px] font-medium">{index + 1}</span>
        )}
      </div>

      {/* Label */}
      <span
        className={cn(
          'text-[13px] transition-colors duration-200',
          isActive   && 'text-heading font-medium',
          isComplete && 'text-subtle line-through decoration-1',
          isPending  && 'text-subtle',
        )}
      >
        {step.label}
      </span>

      {/* Active pulse */}
      {isActive && (
        <span className="ml-auto flex gap-1 items-center">
          {[0, 1, 2].map(d => (
            <span
              key={d}
              className="w-1 h-1 rounded-full bg-primary animate-bounce"
              style={{ animationDelay: `${d * 150}ms` }}
            />
          ))}
        </span>
      )}
    </div>
  )
}
