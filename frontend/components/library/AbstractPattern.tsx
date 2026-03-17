/**
 * AbstractPattern.tsx
 *
 * Generates deterministic, SSR-safe SVG visualisation art for LibraryBrief
 * card headers. All randomness is seeded from the brief `id` string — no
 * Math.random() calls, so output is identical on server and client.
 *
 * Pattern variety: bar-chart, trend-line, area-fill, scatter, ring-donut.
 * Colour palette is domain-keyed.
 */

import type { LibraryBriefDomain, LibraryBriefType } from '@/lib/hooks/useLibrary'

// ── Deterministic hash ────────────────────────────────────────────────────────

function hashCode(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}

/** Returns a pseudo-random float 0–1 given a seed string + index */
function seededFloat(seed: string, index: number): number {
  const h = hashCode(seed + String(index))
  return (h % 10000) / 10000
}

/** Returns integer in [min, max] */
function seededInt(seed: string, index: number, min: number, max: number): number {
  return min + Math.floor(seededFloat(seed, index) * (max - min + 1))
}

// ── Domain colour palettes ────────────────────────────────────────────────────

const DOMAIN_PALETTES: Record<string, { primary: string; secondary: string; accent: string; bg: string; light: string }> = {
  Agriculture:  { primary: '#059669', secondary: '#34D399', accent: '#6EE7B7', bg: '#ECFDF5', light: '#D1FAE5' },
  Finance:      { primary: '#4F46E5', secondary: '#818CF8', accent: '#A5B4FC', bg: '#EEF2FF', light: '#E0E7FF' },
  Energy:       { primary: '#D97706', secondary: '#F59E0B', accent: '#FCD34D', bg: '#FFFBEB', light: '#FEF3C7' },
  Technology:   { primary: '#7C3AED', secondary: '#A78BFA', accent: '#C4B5FD', bg: '#F5F3FF', light: '#EDE9FE' },
  Consumer:     { primary: '#DB2777', secondary: '#F472B6', accent: '#FBCFE8', bg: '#FDF2F8', light: '#FCE7F3' },
  Healthcare:   { primary: '#0891B2', secondary: '#22D3EE', accent: '#67E8F9', bg: '#ECFEFF', light: '#CFFAFE' },
  'Cross-Sector': { primary: '#4F46E5', secondary: '#6366F1', accent: '#A5B4FC', bg: '#EEF2FF', light: '#E0E7FF' },
  Macro:        { primary: '#0F172A', secondary: '#475569', accent: '#94A3B8', bg: '#F8FAFC', light: '#F1F5F9' },
}

const FALLBACK_PALETTE = DOMAIN_PALETTES['Cross-Sector']

// ── Pattern generators ────────────────────────────────────────────────────────

type PatternType = 'bars' | 'area' | 'scatter' | 'donut' | 'rings'

interface PatternProps {
  id: string
  domain: LibraryBriefDomain
  type: LibraryBriefType
  width?: number
  height?: number
  className?: string
}

/** Vertical bar chart with 8–10 bars */
function BarPattern({
  seed,
  palette,
  w,
  h,
}: {
  seed: string
  palette: typeof FALLBACK_PALETTE
  w: number
  h: number
}) {
  const barCount = 9
  const barW = Math.floor((w - 48) / barCount) - 4
  const maxH = h - 32

  const bars = Array.from({ length: barCount }, (_, i) => ({
    height: seededInt(seed, i + 10, Math.floor(maxH * 0.2), maxH),
    secondary: seededFloat(seed, i + 50) > 0.6,
  }))

  return (
    <>
      {/* Background grid lines */}
      {[0.25, 0.5, 0.75, 1].map((frac, i) => (
        <line
          key={i}
          x1={24}
          y1={h - 16 - frac * maxH}
          x2={w - 24}
          y2={h - 16 - frac * maxH}
          stroke={palette.light}
          strokeWidth={1}
        />
      ))}
      {/* Bars */}
      {bars.map((bar, i) => {
        const x = 24 + i * (barW + 4)
        const y = h - 16 - bar.height
        return (
          <g key={i}>
            <rect
              x={x}
              y={y}
              width={barW}
              height={bar.height}
              rx={2}
              fill={bar.secondary ? palette.secondary : palette.primary}
              opacity={bar.secondary ? 0.65 : 0.9}
            />
          </g>
        )
      })}
      {/* Trend line overlay */}
      <polyline
        points={bars
          .map((bar, i) => {
            const x = 24 + i * (barW + 4) + barW / 2
            const y = h - 16 - bar.height
            return `${x},${y}`
          })
          .join(' ')}
        fill="none"
        stroke={palette.accent}
        strokeWidth={2}
        strokeLinejoin="round"
        opacity={0.7}
      />
    </>
  )
}

/** Filled area / sparkline chart */
function AreaPattern({
  seed,
  palette,
  w,
  h,
}: {
  seed: string
  palette: typeof FALLBACK_PALETTE
  w: number
  h: number
}) {
  const pointCount = 12
  const maxH = h - 28

  const points = Array.from({ length: pointCount }, (_, i) => ({
    x: 16 + (i / (pointCount - 1)) * (w - 32),
    y: h - 14 - seededInt(seed, i + 20, Math.floor(maxH * 0.15), maxH),
  }))

  const smoothPath = points
    .map((p, i) => {
      if (i === 0) return `M ${p.x},${p.y}`
      const prev = points[i - 1]
      const cpX = (prev.x + p.x) / 2
      return `C ${cpX},${prev.y} ${cpX},${p.y} ${p.x},${p.y}`
    })
    .join(' ')

  const fillPath = `${smoothPath} L ${points[points.length - 1].x},${h - 14} L ${points[0].x},${h - 14} Z`

  // Secondary lighter line
  const secondaryPoints = Array.from({ length: pointCount }, (_, i) => ({
    x: 16 + (i / (pointCount - 1)) * (w - 32),
    y: h - 14 - seededInt(seed, i + 70, Math.floor(maxH * 0.1), Math.floor(maxH * 0.6)),
  }))
  const secondaryPath = secondaryPoints
    .map((p, i) => {
      if (i === 0) return `M ${p.x},${p.y}`
      const prev = secondaryPoints[i - 1]
      const cpX = (prev.x + p.x) / 2
      return `C ${cpX},${prev.y} ${cpX},${p.y} ${p.x},${p.y}`
    })
    .join(' ')

  const gradId = `grad-${seed.replace(/[^a-z0-9]/gi, '')}`

  return (
    <>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={palette.primary} stopOpacity="0.35" />
          <stop offset="100%" stopColor={palette.primary} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {/* Grid */}
      {[0.33, 0.66, 1].map((f, i) => (
        <line
          key={i}
          x1={16}
          y1={h - 14 - f * maxH}
          x2={w - 16}
          y2={h - 14 - f * maxH}
          stroke={palette.light}
          strokeWidth={1}
        />
      ))}
      {/* Main area fill */}
      <path d={fillPath} fill={`url(#${gradId})`} />
      {/* Main line */}
      <path d={smoothPath} fill="none" stroke={palette.primary} strokeWidth={2.5} strokeLinejoin="round" />
      {/* Secondary line */}
      <path d={secondaryPath} fill="none" stroke={palette.secondary} strokeWidth={1.5} strokeDasharray="4 3" opacity={0.6} />
      {/* Highlight dot at peak */}
      {(() => {
        const peak = points.reduce((a, b) => (a.y < b.y ? a : b))
        return (
          <circle cx={peak.x} cy={peak.y} r={4} fill={palette.primary} stroke="white" strokeWidth={1.5} />
        )
      })()}
    </>
  )
}

/** Scatter plot with 18–28 dots */
function ScatterPattern({
  seed,
  palette,
  w,
  h,
}: {
  seed: string
  palette: typeof FALLBACK_PALETTE
  w: number
  h: number
}) {
  const count = seededInt(seed, 0, 18, 26)
  const dots = Array.from({ length: count }, (_, i) => ({
    x: 20 + seededFloat(seed, i + 100) * (w - 40),
    y: 16 + seededFloat(seed, i + 200) * (h - 32),
    r: 2 + seededFloat(seed, i + 300) * 5,
    c: seededFloat(seed, i + 400) > 0.5 ? palette.primary : palette.secondary,
    o: 0.4 + seededFloat(seed, i + 500) * 0.6,
  }))

  // Trend line
  const trendY1 = h - 14 - seededInt(seed, 1, 20, 60)
  const trendY2 = seededInt(seed, 2, 20, trendY1 - 10)

  return (
    <>
      {/* Quadrant guides */}
      <line x1={w / 2} y1={8} x2={w / 2} y2={h - 8} stroke={palette.light} strokeWidth={1} />
      <line x1={8} y1={h / 2} x2={w - 8} y2={h / 2} stroke={palette.light} strokeWidth={1} />
      {/* Trend line */}
      <line x1={20} y1={trendY1} x2={w - 20} y2={trendY2} stroke={palette.accent} strokeWidth={1.5} strokeDasharray="5 3" opacity={0.7} />
      {/* Dots */}
      {dots.map((d, i) => (
        <circle key={i} cx={d.x} cy={d.y} r={d.r} fill={d.c} opacity={d.o} />
      ))}
    </>
  )
}

/** Donut / pie chart */
function DonutPattern({
  seed,
  palette,
  w,
  h,
}: {
  seed: string
  palette: typeof FALLBACK_PALETTE
  w: number
  h: number
}) {
  const cx = w * 0.45
  const cy = h / 2
  const outer = Math.min(w, h) * 0.36
  const inner = outer * 0.55

  const rawSlices = [
    seededInt(seed, 10, 15, 40),
    seededInt(seed, 11, 10, 30),
    seededInt(seed, 12, 5, 25),
    seededInt(seed, 13, 10, 30),
  ]
  const total = rawSlices.reduce((a, b) => a + b, 0)
  const slices = rawSlices.map(s => s / total)
  const colors = [palette.primary, palette.secondary, palette.accent, palette.light]

  let cumAngle = -Math.PI / 2
  const paths = slices.map((frac, i) => {
    const angle = frac * 2 * Math.PI
    const x1 = cx + outer * Math.cos(cumAngle)
    const y1 = cy + outer * Math.sin(cumAngle)
    cumAngle += angle
    const x2 = cx + outer * Math.cos(cumAngle)
    const y2 = cy + outer * Math.sin(cumAngle)
    const ix1 = cx + inner * Math.cos(cumAngle)
    const iy1 = cy + inner * Math.sin(cumAngle)
    const ix2 = cx + inner * Math.cos(cumAngle - angle)
    const iy2 = cy + inner * Math.sin(cumAngle - angle)
    const large = angle > Math.PI ? 1 : 0
    return { path: `M ${x1} ${y1} A ${outer} ${outer} 0 ${large} 1 ${x2} ${y2} L ${ix1} ${iy1} A ${inner} ${inner} 0 ${large} 0 ${ix2} ${iy2} Z`, color: colors[i] }
  })

  // Legend bars on right
  const legendX = cx + outer + 16
  const legendItems = [
    { label: `${Math.round(slices[0] * 100)}%`, color: palette.primary },
    { label: `${Math.round(slices[1] * 100)}%`, color: palette.secondary },
    { label: `${Math.round(slices[2] * 100)}%`, color: palette.accent },
  ]

  return (
    <>
      {paths.map((p, i) => (
        <path key={i} d={p.path} fill={p.color} opacity={i === 0 ? 1 : 0.75 - i * 0.12} />
      ))}
      {/* Center label */}
      <text x={cx} y={cy + 1} textAnchor="middle" dominantBaseline="middle" fontSize={11} fontWeight="600" fill={palette.primary}>
        {Math.round(slices[0] * 100)}%
      </text>
      {/* Legend */}
      {legendItems.map((item, i) => (
        <g key={i} transform={`translate(${legendX}, ${cy - 18 + i * 16})`}>
          <rect x={0} y={-5} width={8} height={8} rx={2} fill={item.color} />
          <text x={12} y={0} dominantBaseline="middle" fontSize={9} fill={palette.primary} opacity={0.8}>
            {item.label}
          </text>
        </g>
      ))}
    </>
  )
}

/** Concentric ring / progress rings */
function RingsPattern({
  seed,
  palette,
  w,
  h,
}: {
  seed: string
  palette: typeof FALLBACK_PALETTE
  w: number
  h: number
}) {
  const cx = w / 2
  const cy = h / 2
  const rings = [
    { r: Math.min(w, h) * 0.38, fill: seededFloat(seed, 10), color: palette.primary, sw: 6 },
    { r: Math.min(w, h) * 0.28, fill: seededFloat(seed, 11), color: palette.secondary, sw: 5 },
    { r: Math.min(w, h) * 0.18, fill: seededFloat(seed, 12), color: palette.accent, sw: 4 },
  ]

  return (
    <>
      {rings.map((ring, i) => {
        const circumference = 2 * Math.PI * ring.r
        const dashArray = ring.fill * circumference
        return (
          <g key={i}>
            {/* Track */}
            <circle cx={cx} cy={cy} r={ring.r} fill="none" stroke={palette.light} strokeWidth={ring.sw} />
            {/* Fill */}
            <circle
              cx={cx}
              cy={cy}
              r={ring.r}
              fill="none"
              stroke={ring.color}
              strokeWidth={ring.sw}
              strokeDasharray={`${dashArray} ${circumference}`}
              strokeLinecap="round"
              transform={`rotate(-90 ${cx} ${cy})`}
              opacity={0.9 - i * 0.15}
            />
          </g>
        )
      })}
      {/* Center dot */}
      <circle cx={cx} cy={cy} r={4} fill={palette.primary} />
    </>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

const TYPE_TO_PATTERN: Record<LibraryBriefType, PatternType> = {
  'ai-brief':       'area',
  'weekly-report':  'bars',
  'deep-analysis':  'scatter',
  'sector-review':  'donut',
}

export function AbstractPattern({
  id,
  domain,
  type,
  width = 400,
  height = 180,
  className,
}: PatternProps) {
  const palette = DOMAIN_PALETTES[domain] ?? FALLBACK_PALETTE

  // Use hash to occasionally override the type-default pattern for variety
  const override = seededInt(id, 999, 0, 4)
  const patternOptions: PatternType[] = ['bars', 'area', 'scatter', 'donut', 'rings']
  const patternType: PatternType =
    override === 0 ? TYPE_TO_PATTERN[type] : patternOptions[seededInt(id, 888, 0, 4)]

  const w = width
  const h = height

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      width="100%"
      height="100%"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
      style={{ background: palette.bg, display: 'block' }}
    >
      {/* Subtle grid background */}
      <rect width={w} height={h} fill={palette.bg} />
      {/* Decorative circle blob */}
      <circle
        cx={w * (0.6 + seededFloat(id, 1) * 0.3)}
        cy={h * (0.2 + seededFloat(id, 2) * 0.6)}
        r={w * (0.15 + seededFloat(id, 3) * 0.12)}
        fill={palette.light}
        opacity={0.6}
      />

      {patternType === 'bars'    && <BarPattern    seed={id} palette={palette} w={w} h={h} />}
      {patternType === 'area'    && <AreaPattern   seed={id} palette={palette} w={w} h={h} />}
      {patternType === 'scatter' && <ScatterPattern seed={id} palette={palette} w={w} h={h} />}
      {patternType === 'donut'   && <DonutPattern  seed={id} palette={palette} w={w} h={h} />}
      {patternType === 'rings'   && <RingsPattern  seed={id} palette={palette} w={w} h={h} />}
    </svg>
  )
}
