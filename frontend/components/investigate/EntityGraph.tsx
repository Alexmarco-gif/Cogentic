'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import type { GraphNode, GraphEdge } from '@/lib/hooks/useInvestigate'

// ── Node colours by type ─────────────────────────────────────────────────────
const NODE_CONFIG: Record<GraphNode['type'], {
  bg: string; border: string; label: string; labelBg: string
}> = {
  company:   { bg: 'bg-primary/10',  border: 'border-primary/30',  label: 'Company',   labelBg: 'bg-primary/10  text-primary'  },
  regulator: { bg: 'bg-amber-50',    border: 'border-amber-200',   label: 'Regulator', labelBg: 'bg-amber-50    text-amber-700' },
  market:    { bg: 'bg-emerald-50',  border: 'border-emerald-200', label: 'Market',    labelBg: 'bg-emerald-50  text-emerald-700' },
  event:     { bg: 'bg-red-50',      border: 'border-red-200',     label: 'Event',     labelBg: 'bg-red-50      text-red-700'   },
}

const NODE_W = 104
const NODE_H = 52

interface EntityGraphProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export function EntityGraph({ nodes, edges }: EntityGraphProps) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [hoveredEdge, setHoveredEdge] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<string | null>(null)

  // Compute SVG dimensions from node positions
  const maxX = Math.max(...nodes.map(n => n.x)) + NODE_W + 20
  const maxY = Math.max(...nodes.map(n => n.y)) + NODE_H + 32

  // Node centre helpers
  const cx = (n: GraphNode) => n.x + NODE_W / 2
  const cy = (n: GraphNode) => n.y + NODE_H / 2

  return (
    <div className="relative w-full overflow-auto rounded-xl border border-border bg-gradient-to-br from-slate-50 to-white">
      {/* Legend */}
      <div className="absolute top-3 right-3 flex flex-col gap-1 z-10">
        {(Object.entries(NODE_CONFIG) as [GraphNode['type'], typeof NODE_CONFIG[GraphNode['type']]][]).map(([type, cfg]) => (
          <div key={type} className="flex items-center gap-1.5">
            <span className={cn('w-2.5 h-2.5 rounded border', cfg.bg, cfg.border)} />
            <span className="text-[10px] text-subtle capitalize">{cfg.label}</span>
          </div>
        ))}
      </div>

      <svg
        width="100%"
        viewBox={`0 0 ${maxX} ${maxY}`}
        className="overflow-visible"
        style={{ minHeight: maxY }}
      >
        {/* ── Edges ─────────────────────────────────── */}
        {edges.map(edge => {
          const src  = nodes.find(n => n.id === edge.source)
          const tgt  = nodes.find(n => n.id === edge.target)
          if (!src || !tgt) return null

          const x1 = cx(src), y1 = cy(src)
          const x2 = cx(tgt), y2 = cy(tgt)

          // Mid-point for label
          const mx = (x1 + x2) / 2
          const my = (y1 + y2) / 2

          const isHovered = hoveredEdge === edge.id ||
            selectedNode === edge.source ||
            selectedNode === edge.target ||
            hoveredNode === edge.source ||
            hoveredNode === edge.target

          return (
            <g key={edge.id}>
              <line
                x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={isHovered ? '#4F46E5' : '#CBD5E1'}
                strokeWidth={isHovered ? 1.5 : 1}
                strokeDasharray={isHovered ? undefined : '4 3'}
                className="transition-all duration-200"
                onMouseEnter={() => setHoveredEdge(edge.id)}
                onMouseLeave={() => setHoveredEdge(null)}
              />
              {/* Edge arrowhead */}
              <marker id={`arrow-${edge.id}`} markerWidth="8" markerHeight="8" refX="6" refY="3">
                <path d="M 0 0 L 6 3 L 0 6 z" fill={isHovered ? '#4F46E5' : '#94A3B8'} />
              </marker>
              {/* Edge label */}
              {isHovered && (
                <text
                  x={mx} y={my - 6}
                  textAnchor="middle"
                  fontSize={10}
                  fill="#64748B"
                  className="pointer-events-none select-none"
                >
                  {edge.label}
                </text>
              )}
            </g>
          )
        })}

        {/* ── Nodes (foreign objects so we can use Tailwind) ─ */}
        {nodes.map(node => {
          const cfg = NODE_CONFIG[node.type]
          const isHovered = hoveredNode === node.id || selectedNode === node.id
          return (
            <foreignObject
              key={node.id}
              x={node.x}
              y={node.y}
              width={NODE_W}
              height={NODE_H}
              overflow="visible"
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              onClick={() => setSelectedNode(current => current === node.id ? null : node.id)}
              className="cursor-pointer"
            >
              <div
                className={cn(
                  'w-full h-full rounded-xl border-2 flex flex-col items-center justify-center px-2 transition-all duration-150',
                  cfg.bg,
                  cfg.border,
                  isHovered && 'scale-105 shadow-md',
                )}
              >
                <span className="text-[11px] font-semibold text-heading text-center leading-tight">{node.label}</span>
                {node.sublabel && (
                  <span className="text-[9px] text-subtle mt-0.5">{node.sublabel}</span>
                )}
              </div>
            </foreignObject>
          )
        })}
      </svg>

      {/* Tip */}
      <p className="text-[10px] text-subtle text-center py-2">
        Tap or hover nodes to explore relationships
      </p>
    </div>
  )
}
