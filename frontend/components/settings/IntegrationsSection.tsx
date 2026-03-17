'use client'

import { CheckCircle2, XCircle, ExternalLink } from 'lucide-react'
import type { Integration } from '@/lib/hooks/useSettings'

// ── Integration card ──────────────────────────────────────────────────────────

function IntegrationCard({
  integration,
  onToggle,
}: {
  integration: Integration
  onToggle: (id: string) => void
}) {
  const { id, name, description, category, connected, logoInitial, color } = integration

  return (
    <div className="flex items-center gap-4 rounded-2xl border border-border bg-surface p-5 shadow-card transition-all hover:shadow-md">
      {/* Logo */}
      <div
        className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl text-white text-base font-semibold shadow-sm"
        style={{ backgroundColor: color }}
      >
        {logoInitial}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-heading">{name}</p>
          <span className="rounded-pill border border-border bg-muted px-2 py-0.5 text-[10px] text-subtle">
            {category}
          </span>
        </div>
        <p className="mt-0.5 text-xs text-subtle">{description}</p>
      </div>

      {/* Status + action */}
      <div className="flex items-center gap-3 flex-shrink-0">
        {connected ? (
          <span className="flex items-center gap-1 text-[11px] font-medium text-emerald-600">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Connected
          </span>
        ) : (
          <span className="flex items-center gap-1 text-[11px] text-subtle">
            <XCircle className="h-3.5 w-3.5" />
            Not connected
          </span>
        )}
        <button
          onClick={() => onToggle(id)}
          className={`rounded-xl px-4 py-1.5 text-xs font-medium transition-all ${
            connected
              ? 'border border-rose-200 bg-rose-50 text-rose-600 hover:bg-rose-100'
              : 'bg-primary text-white hover:bg-primary-hover'
          }`}
        >
          {connected ? 'Disconnect' : 'Connect'}
        </button>
        <a
          href="#"
          className="text-subtle hover:text-body transition-colors"
          aria-label={`${name} docs`}
        >
          <ExternalLink className="h-4 w-4" strokeWidth={1.5} />
        </a>
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

interface IntegrationsSectionProps {
  integrations: Integration[]
  onToggle: (id: string) => void
}

export function IntegrationsSection({ integrations, onToggle }: IntegrationsSectionProps) {
  const categories = [...new Set(integrations.map(i => i.category))]

  return (
    <div className="flex flex-col gap-8">
      {/* API key info banner */}
      <div className="flex items-center gap-4 rounded-2xl border border-primary/20 bg-primary/5 p-5">
        <div className="flex-1">
          <p className="text-sm font-medium text-heading">Developer API</p>
          <p className="mt-0.5 text-xs text-subtle">
            Access Cogent data programmatically. Manage API keys in the Security tab.
          </p>
        </div>
        <a
          href="#"
          className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-medium text-white hover:bg-primary-hover transition-colors"
        >
          <ExternalLink className="h-3.5 w-3.5" strokeWidth={1.5} />
          View docs
        </a>
      </div>

      {/* Group by category */}
      {categories.map(cat => (
        <div key={cat}>
          <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-subtle">{cat}</h3>
          <div className="flex flex-col gap-3">
            {integrations.filter(i => i.category === cat).map(integration => (
              <IntegrationCard
                key={integration.id}
                integration={integration}
                onToggle={onToggle}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
