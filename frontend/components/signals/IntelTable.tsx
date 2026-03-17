'use client'

import { ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Signal } from '@/lib/hooks/useSignals'

const SEVERITY_DOT: Record<string, string> = {
  critical: 'bg-red-500',
  high:     'bg-orange-400',
  medium:   'bg-amber-400',
  low:      'bg-slate-300',
}

import { getDomainPillLight } from '@/lib/domain-colors'

interface IntelTableProps {
  signals: Signal[]
  onRowClick: (signal: Signal) => void
  loading?: boolean
}

export function IntelTable({ signals, onRowClick, loading }: IntelTableProps) {
  const rows = signals.slice(0, 8)

  return (
    <div className="bg-surface border border-border rounded-card shadow-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border">
        <div>
          <h2 className="text-[14px] font-medium text-heading">Intelligence Feed</h2>
          <p className="text-[11px] text-subtle mt-0.5">All active signals across domains</p>
        </div>
        <button className="text-[12px] text-primary font-medium hover:underline flex items-center gap-1">
          View all <ExternalLink size={11} />
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              <th className="text-left px-5 py-2.5 text-[11px] font-medium text-subtle tracking-wide">Entity</th>
              <th className="text-left px-4 py-2.5 text-[11px] font-medium text-subtle tracking-wide">Domain</th>
              <th className="text-left px-4 py-2.5 text-[11px] font-medium text-subtle tracking-wide">Headline</th>
              <th className="text-left px-4 py-2.5 text-[11px] font-medium text-subtle tracking-wide">Severity</th>
              <th className="text-right px-5 py-2.5 text-[11px] font-medium text-subtle tracking-wide">Conf.</th>
              <th className="text-right px-5 py-2.5 text-[11px] font-medium text-subtle tracking-wide">Time</th>
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td className="px-5 py-3" colSpan={6}>
                      <div className="h-3 bg-muted rounded animate-pulse w-full" />
                    </td>
                  </tr>
                ))
              : rows.map(signal => (
                  <tr
                    key={signal.id}
                    onClick={() => onRowClick(signal)}
                    className={cn(
                      'border-b border-border/50 cursor-pointer transition-colors hover:bg-muted/60',
                      signal.isUnread && 'bg-primary/[0.02]',
                    )}
                  >
                    {/* Entity */}
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2.5">
                        {signal.isUnread && (
                          <span className="w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
                        )}
                        <div
                          className="w-6 h-6 rounded-full bg-muted border border-border shrink-0
                                     flex items-center justify-center text-[9px] font-medium text-subtle"
                        >
                          {signal.entityInitial}
                        </div>
                        <span className="font-medium text-heading truncate max-w-[140px]">
                          {signal.entityName}
                        </span>
                      </div>
                    </td>

                    {/* Domain */}
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          'text-[10px] font-medium px-2 py-0.5 rounded-pill whitespace-nowrap',
                          getDomainPillLight(signal.domain),
                        )}
                      >
                        {signal.domain}
                      </span>
                    </td>

                    {/* Headline */}
                    <td className="px-4 py-3 max-w-[300px]">
                      <p className="text-body truncate text-[12px]">{signal.headline}</p>
                    </td>

                    {/* Severity */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <span className={cn('w-1.5 h-1.5 rounded-full', SEVERITY_DOT[signal.severity])} />
                        <span className="capitalize text-[12px] text-body">{signal.severity}</span>
                      </div>
                    </td>

                    {/* Confidence */}
                    <td className="px-5 py-3 text-right">
                      <span className="text-[12px] font-medium tabular-nums text-heading">
                        {signal.confidence}%
                      </span>
                    </td>

                    {/* Time */}
                    <td className="px-5 py-3 text-right whitespace-nowrap">
                      <span className="text-[11px] text-subtle">{signal.relativeTime}</span>
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
