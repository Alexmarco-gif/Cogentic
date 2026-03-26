/**
 * Dynamic domain color system — derives colors from domain name string.
 *
 * Instead of hardcoding 5 Nigeria-specific domains, this module generates
 * consistent, deterministic color assignments for ANY domain string.
 * When a new domain appears, it automatically gets a color.
 */

import type { TrendColor } from '@/components/ui/TrendLine'

// ── Color palette — a finite set of curated Tailwind-compatible colors ──────
// The system cycles through these for unknown domains.

const COLOR_PALETTE = [
  { key: 'violet',  pill: 'bg-violet-500/15 text-violet-300',  pillLight: 'bg-violet-50 text-violet-700 border-violet-100',  avatar: 'bg-violet-500/20 text-violet-300 ring-violet-500/20', badge: 'ai',      fill: '#8B5CF6', dot: 'bg-violet-500', accent: 'text-violet-500', trend: 'indigo' as TrendColor },
  { key: 'emerald', pill: 'bg-emerald-500/15 text-emerald-300', pillLight: 'bg-emerald-50 text-emerald-700 border-emerald-100', avatar: 'bg-emerald-500/20 text-emerald-300 ring-emerald-500/20', badge: 'success', fill: '#10B981', dot: 'bg-emerald-500', accent: 'text-emerald-500', trend: 'emerald' as TrendColor },
  { key: 'pink',    pill: 'bg-pink-500/15 text-pink-300',      pillLight: 'bg-pink-50 text-pink-700 border-pink-100',          avatar: 'bg-pink-500/20 text-pink-300 ring-pink-500/20',       badge: 'neutral', fill: '#EC4899', dot: 'bg-pink-500',    accent: 'text-pink-500',    trend: 'rose' as TrendColor },
  { key: 'blue',    pill: 'bg-blue-500/15 text-blue-300',      pillLight: 'bg-blue-50 text-blue-700 border-blue-100',          avatar: 'bg-blue-500/20 text-blue-300 ring-blue-500/20',       badge: 'ai',      fill: '#3B82F6', dot: 'bg-blue-500',    accent: 'text-blue-500',    trend: 'indigo' as TrendColor },
  { key: 'amber',   pill: 'bg-amber-500/15 text-amber-300',    pillLight: 'bg-amber-50 text-amber-700 border-amber-100',       avatar: 'bg-amber-500/20 text-amber-300 ring-amber-500/20',    badge: 'warning', fill: '#D97706', dot: 'bg-amber-500',   accent: 'text-amber-500',   trend: 'amber' as TrendColor },
  { key: 'cyan',    pill: 'bg-cyan-500/15 text-cyan-300',      pillLight: 'bg-cyan-50 text-cyan-700 border-cyan-100',          avatar: 'bg-cyan-500/20 text-cyan-300 ring-cyan-500/20',       badge: 'ai',      fill: '#06B6D4', dot: 'bg-cyan-500',    accent: 'text-cyan-500',    trend: 'indigo' as TrendColor },
  { key: 'rose',    pill: 'bg-rose-500/15 text-rose-300',      pillLight: 'bg-rose-50 text-rose-700 border-rose-100',          avatar: 'bg-rose-500/20 text-rose-300 ring-rose-500/20',       badge: 'neutral', fill: '#F43F5E', dot: 'bg-rose-500',    accent: 'text-rose-500',    trend: 'rose' as TrendColor },
  { key: 'indigo',  pill: 'bg-indigo-500/15 text-indigo-300',  pillLight: 'bg-indigo-50 text-indigo-700 border-indigo-100',    avatar: 'bg-indigo-500/20 text-indigo-300 ring-indigo-500/20',  badge: 'ai',      fill: '#6366F1', dot: 'bg-indigo-500',  accent: 'text-indigo-500',  trend: 'indigo' as TrendColor },
]

const DEFAULT_COLOR = COLOR_PALETTE[0]

// ── Deterministic hash → color index ────────────────────────────────────────

function hashString(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash |= 0 // Convert to 32bit integer
  }
  return Math.abs(hash)
}

function getColorEntry(domain: string) {
  if (!domain) return DEFAULT_COLOR
  const idx = hashString(domain.toLowerCase()) % COLOR_PALETTE.length
  return COLOR_PALETTE[idx]
}

// ── Public API ──────────────────────────────────────────────────────────────

/** Dark-mode pill (bg-{color}-500/15 text-{color}-300) */
export function getDomainPill(domain: string): string {
  return getColorEntry(domain).pill
}

/** Light-mode pill (bg-{color}-50 text-{color}-700 border-{color}-100) */
export function getDomainPillLight(domain: string): string {
  return getColorEntry(domain).pillLight
}

/** Avatar ring (bg-{color}-500/20 text-{color}-300 ring-{color}-500/20) */
export function getDomainAvatar(domain: string): string {
  return getColorEntry(domain).avatar
}

/** Badge variant string for Badge component */
export function getDomainBadge(domain: string): string {
  return getColorEntry(domain).badge
}

/** Hex fill color for map markers / chart colors */
export function getDomainFill(domain: string): string {
  return getColorEntry(domain).fill
}

/** Tailwind dot class (bg-{color}-500) */
export function getDomainDot(domain: string): string {
  return getColorEntry(domain).dot
}

/** Tailwind accent text class (text-{color}-500) */
export function getDomainAccent(domain: string): string {
  return getColorEntry(domain).accent
}

/** TrendLine color token */
export function getDomainTrend(domain: string): TrendColor {
  return getColorEntry(domain).trend
}

/** Get a hex color for any string key (for charts/reports) */
export function getStringColor(key: string): string {
  return getColorEntry(key).fill
}
