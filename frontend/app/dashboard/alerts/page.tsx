'use client';

import { useState } from 'react';
import { Bell, CheckCircle, AlertTriangle, AlertCircle, Info, TrendingUp } from 'lucide-react';
import { useAlerts, useAlertSummary } from '@/lib/hooks/useAlerts';
import type { AlertResponse } from '@/lib/api/types';

const SEVERITY_CONFIG = {
  critical: { label: 'Critical', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', icon: AlertCircle },
  high:     { label: 'High',     color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200', icon: AlertTriangle },
  medium:   { label: 'Medium',   color: 'text-yellow-600', bg: 'bg-yellow-50', border: 'border-yellow-200', icon: AlertTriangle },
  low:      { label: 'Low',      color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', icon: Info },
} as const;

type Severity = keyof typeof SEVERITY_CONFIG;

function SeverityBadge({ severity }: { severity: string }) {
  const cfg = SEVERITY_CONFIG[severity as Severity] ?? SEVERITY_CONFIG.low;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color} ${cfg.bg} border ${cfg.border}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  );
}

function AlertRow({
  alert,
  onAcknowledge,
}: {
  alert: AlertResponse;
  onAcknowledge: (id: string) => void;
}) {
  const cfg = SEVERITY_CONFIG[alert.severity as Severity] ?? SEVERITY_CONFIG.low;

  return (
    <div className={`rounded-lg border p-4 ${alert.acknowledged ? 'opacity-50' : ''} ${cfg.border} ${cfg.bg}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <SeverityBadge severity={alert.severity} />
            {alert.metric && (
              <span className="text-xs font-mono bg-surface border border-border rounded px-1.5 py-0.5 text-body">
                {alert.metric}
              </span>
            )}
            {alert.country_code && (
              <span className="text-xs text-subtle">{alert.country_code}</span>
            )}
          </div>
          <p className={`mt-1 font-medium text-sm ${cfg.color}`}>{alert.title}</p>
          {alert.description && (
            <p className="mt-1 text-xs text-body leading-relaxed">{alert.description}</p>
          )}
          {alert.current_value !== null && alert.baseline_value !== null && (
            <div className="mt-2 flex gap-4 text-xs text-subtle">
              <span>Current: <strong>{alert.current_value?.toFixed(4)}</strong></span>
              <span>Baseline: <strong>{alert.baseline_value?.toFixed(4)}</strong></span>
              {alert.deviation_pct !== null && (
                <span className={alert.deviation_pct > 0 ? 'text-red-600' : 'text-green-600'}>
                  {alert.deviation_pct > 0 ? '+' : ''}{alert.deviation_pct.toFixed(1)}%
                </span>
              )}
            </div>
          )}
          <p className="mt-1 text-xs text-subtle">
            {new Date(alert.created_at).toLocaleString()}
          </p>
        </div>
        {!alert.acknowledged && (
          <button
            onClick={() => onAcknowledge(alert.id)}
            className="shrink-0 flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-body hover:text-success hover:bg-success-bg rounded-lg border border-border transition-colors"
          >
            <CheckCircle className="w-3.5 h-3.5" />
            Acknowledge
          </button>
        )}
        {alert.acknowledged && (
          <span className="shrink-0 flex items-center gap-1 text-xs text-subtle">
            <CheckCircle className="w-3.5 h-3.5" />
            Acknowledged
          </span>
        )}
      </div>
    </div>
  );
}

export default function AlertsPage() {
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [showAcknowledged, setShowAcknowledged] = useState(false);

  const { summary } = useAlertSummary();
  const { data, loading, error, acknowledge } = useAlerts({
    severity: (severityFilter as Severity) || undefined,
    acknowledged: showAcknowledged ? undefined : false,
    limit: 100,
  });

  const severities: Array<{ value: string; label: string }> = [
    { value: '', label: 'All severities' },
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
  ];

  return (
    <div className="mx-auto max-w-[1100px] space-y-6 px-3 py-4 sm:px-4 lg:px-0">
      {/* Header */}
      <div className="surface-panel flex flex-col gap-4 p-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <Bell className="w-6 h-6 text-subtle" />
          <div>
            <h1 className="text-xl font-semibold text-heading">Signal Alerts</h1>
            <p className="text-sm text-subtle">Anomalies detected by change detection</p>
          </div>
        </div>
        {summary && summary.unacknowledged > 0 && (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-700">
            <AlertCircle className="w-4 h-4" />
            {summary.unacknowledged} unreviewed
          </span>
        )}
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {(['critical', 'high', 'medium', 'low'] as Severity[]).map((sev) => {
            const cfg = SEVERITY_CONFIG[sev];
            const count = summary.by_severity[sev] ?? 0;
            return (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev === severityFilter ? '' : sev)}
                className={`rounded-lg border p-3 text-left transition-all ${cfg.border} ${cfg.bg} ${severityFilter === sev ? 'ring-2 ring-offset-1 ring-current' : 'hover:shadow-sm'}`}
              >
                <p className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</p>
                <p className={`text-2xl font-bold mt-0.5 ${cfg.color}`}>{count}</p>
              </button>
            );
          })}
        </div>
      )}

      {/* Top metrics */}
      {summary && Object.keys(summary.by_metric).length > 0 && (
        <div className="rounded-lg border border-border bg-surface p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-subtle" />
            <h2 className="text-sm font-semibold text-body">Most Alerted Metrics</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(summary.by_metric).map(([metric, count]: [string, number]) => (
              <span key={metric} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-muted border border-border rounded-full text-xs text-body">
                <span className="font-mono">{metric}</span>
                <span className="bg-border text-body rounded-full px-1.5 py-0.5 text-[10px] font-medium">{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="surface-panel flex flex-col gap-3 p-4 sm:flex-row sm:flex-wrap sm:items-center">
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="text-sm border border-border rounded-lg px-3 py-1.5 bg-surface text-body focus:outline-none focus:ring-2 focus:ring-primary/40"
        >
          {severities.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-body cursor-pointer">
          <input
            type="checkbox"
            checked={showAcknowledged}
            onChange={(e) => setShowAcknowledged(e.target.checked)}
            className="rounded border-border accent-primary"
          />
          Show acknowledged
        </label>
        {data && (
          <span className="text-sm text-subtle sm:ml-auto">{data.total} total · {data.unacknowledged} unreviewed</span>
        )}
      </div>

      {/* Alert list */}
      {loading && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div className="h-24 bg-muted rounded-lg animate-pulse" />
          ))}
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}
      {!loading && data && data.items.length === 0 && (
        <div className="text-center py-16 text-subtle">
          <CheckCircle className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="font-medium">No alerts</p>
          <p className="text-sm mt-1">Change detection hasn&apos;t found any anomalies yet</p>
        </div>
      )}
      {!loading && data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((alert: AlertResponse) => (
            <AlertRow key={alert.id} alert={alert} onAcknowledge={acknowledge} />
          ))}
        </div>
      )}
    </div>
  );
}
