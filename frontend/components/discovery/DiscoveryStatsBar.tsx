'use client'

import { Radar, Globe2, Zap, XCircle, Layers } from 'lucide-react'
import { StatCard } from '@/components/signals/StatCard'
import type { DiscoveredSourceStatsResponse } from '@/lib/api/types'

interface DiscoveryStatsBarProps {
  stats: DiscoveredSourceStatsResponse | null
  loading?: boolean
}

export function DiscoveryStatsBar({ stats, loading }: DiscoveryStatsBarProps) {
  if (loading || !stats) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="bg-surface border border-border rounded-card shadow-card p-5 h-[110px] animate-pulse"
          />
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      <StatCard
        icon={<Layers size={18} className="text-primary" />}
        label="Total Sources"
        value={String(stats.total)}
        accent="bg-primary/10"
      />
      <StatCard
        icon={<Radar size={18} className="text-sky-600" />}
        label="Discovered"
        value={String(stats.discovered)}
        sub="Awaiting threshold"
        accent="bg-sky-50"
      />
      <StatCard
        icon={<Globe2 size={18} className="text-amber-600" />}
        label="Recommended"
        value={String(stats.recommended)}
        sub="Ready for review"
        accent="bg-amber-50"
      />
      <StatCard
        icon={<Zap size={18} className="text-emerald-600" />}
        label="Activated"
        value={String(stats.activated)}
        sub="Feeding contracts"
        accent="bg-emerald-50"
      />
      <StatCard
        icon={<XCircle size={18} className="text-neutral-500" />}
        label="Dismissed"
        value={String(stats.dismissed)}
        accent="bg-neutral-100"
      />
    </div>
  )
}
