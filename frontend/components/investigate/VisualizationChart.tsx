'use client'

import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import type { ChartDefinition } from '@/lib/hooks/useInvestigate'

interface VisualizationChartProps {
  charts: ChartDefinition[]
}

function SingleChart({ chart }: { chart: ChartDefinition }) {
  const hasRightAxis = chart.series.some(s => s.yAxisId === 'right')

  return (
    <div className="space-y-2">
      {/* Chart header */}
      <div>
        <h4 className="text-[13px] font-medium text-heading">{chart.title}</h4>
        <p className="text-[11px] text-subtle">{chart.subtitle}</p>
      </div>

      {/* Chart body */}
      <div className="h-[200px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chart.data} margin={{ top: 4, right: hasRightAxis ? 8 : 4, bottom: 0, left: -16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: '#94A3B8' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              yAxisId="left"
              tick={{ fontSize: 10, fill: '#94A3B8' }}
              axisLine={false}
              tickLine={false}
              domain={['auto', 'auto']}
              label={{
                value: chart.leftLabel,
                angle: -90,
                position: 'insideLeft',
                offset: 14,
                style: { fontSize: 9, fill: '#94A3B8' },
              }}
            />
            {hasRightAxis && (
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 10, fill: '#94A3B8' }}
                axisLine={false}
                tickLine={false}
                domain={['auto', 'auto']}
                label={{
                  value: chart.rightLabel ?? '',
                  angle: 90,
                  position: 'insideRight',
                  offset: 14,
                  style: { fontSize: 9, fill: '#94A3B8' },
                }}
              />
            )}
            <Tooltip
              contentStyle={{
                background: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderRadius: 8,
                fontSize: 12,
                boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
              }}
              cursor={{ stroke: '#E2E8F0', strokeWidth: 1 }}
            />
            <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8, color: '#64748B' }} />

            {chart.series.map(s => {
              const commonProps = {
                key:      s.key,
                dataKey:  s.key,
                name:     s.label,
                yAxisId:  s.yAxisId ?? 'left',
              }
              if (s.type === 'bar') {
                return (
                  <Bar
                    {...commonProps}
                    fill={s.color}
                    radius={[3, 3, 0, 0]}
                    maxBarSize={28}
                  />
                )
              }
              if (s.type === 'area') {
                return (
                  <Area
                    {...commonProps}
                    type="monotone"
                    fill={`${s.color}18`}
                    stroke={s.color}
                    strokeWidth={2}
                    strokeDasharray={s.dashed ? '4 3' : undefined}
                    dot={{ r: 3, fill: s.color, strokeWidth: 0 }}
                    activeDot={{ r: 5 }}
                  />
                )
              }
              // line
              return (
                <Line
                  {...commonProps}
                  type="monotone"
                  stroke={s.color}
                  strokeWidth={s.dashed ? 1.5 : 2}
                  strokeDasharray={s.dashed ? '4 3' : undefined}
                  dot={{ r: 2.5, fill: s.color, strokeWidth: 0 }}
                  activeDot={{ r: 4 }}
                />
              )
            })}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Insight callout */}
      <div className="bg-primary/5 border border-primary/10 rounded-lg px-3 py-2 text-[11.5px] text-body leading-relaxed">
        <span className="font-medium text-primary">Pattern: </span>
        {chart.insight}
      </div>
    </div>
  )
}

export function VisualizationChart({ charts }: VisualizationChartProps) {
  if (!charts.length) return null

  return (
    <div className="space-y-6">
      {charts.map((chart, i) => (
        <div key={chart.id}>
          {i > 0 && <div className="border-t border-border mb-6" />}
          <SingleChart chart={chart} />
        </div>
      ))}
    </div>
  )
}
