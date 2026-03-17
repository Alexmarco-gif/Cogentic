'use client'

import { useState } from 'react'
import { useThemeStore } from '@/lib/stores/themeStore'
import { Sun, Moon, Monitor, Globe, Bell } from 'lucide-react'

// ── Option card ───────────────────────────────────────────────────────────────

function OptionCard<T extends string>({
  value,
  selected,
  onSelect,
  icon: Icon,
  label,
  description,
}: {
  value: T
  selected: boolean
  onSelect: (v: T) => void
  icon: React.ElementType
  label: string
  description?: string
}) {
  return (
    <button
      onClick={() => onSelect(value)}
      className={`flex items-start gap-3 rounded-xl border p-4 text-left transition-all ${
        selected
          ? 'border-primary/30 bg-primary/5 ring-1 ring-primary/20'
          : 'border-border bg-surface hover:border-primary/20 hover:bg-muted/50'
      }`}
    >
      <Icon className={`mt-0.5 h-5 w-5 flex-shrink-0 ${selected ? 'text-primary' : 'text-subtle'}`} strokeWidth={1.5} />
      <div>
        <p className={`text-sm font-medium ${selected ? 'text-primary' : 'text-body'}`}>{label}</p>
        {description && <p className="mt-0.5 text-xs text-subtle">{description}</p>}
      </div>
    </button>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export function PreferencesSection() {
  const { theme, toggleTheme } = useThemeStore()
  const [language, setLanguage]   = useState('en')
  const [timezone, setTimezone]   = useState('UTC')
  const [density, setDensity]     = useState<'comfortable' | 'compact'>('comfortable')

  return (
    <div className="flex flex-col gap-8">
      {/* ── Appearance ────────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <h3 className="mb-1 text-sm font-medium text-heading">Appearance</h3>
        <p className="mb-5 text-xs text-subtle">Choose your preferred colour scheme</p>
        <div className="grid grid-cols-3 gap-3">
          <OptionCard
            value="light"
            selected={theme === 'light'}
            onSelect={() => { if (theme !== 'light') toggleTheme() }}
            icon={Sun}
            label="Light"
            description="Clean white interface"
          />
          <OptionCard
            value="dark"
            selected={theme === 'dark'}
            onSelect={() => { if (theme !== 'dark') toggleTheme() }}
            icon={Moon}
            label="Dark"
            description="Easy on the eyes"
          />
          <OptionCard
            value="system"
            selected={false}
            onSelect={() => {}}
            icon={Monitor}
            label="System"
            description="Follow OS setting"
          />
        </div>
      </div>

      {/* ── Display density ──────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <h3 className="mb-1 text-sm font-medium text-heading">Display Density</h3>
        <p className="mb-5 text-xs text-subtle">Control how much information is shown at once</p>
        <div className="grid grid-cols-2 gap-3">
          <OptionCard
            value="comfortable"
            selected={density === 'comfortable'}
            onSelect={setDensity}
            icon={Globe}
            label="Comfortable"
            description="More spacing, easier to scan"
          />
          <OptionCard
            value="compact"
            selected={density === 'compact'}
            onSelect={setDensity}
            icon={Bell}
            label="Compact"
            description="More data per screen"
          />
        </div>
      </div>

      {/* ── Language & timezone ───────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <h3 className="mb-1 text-sm font-medium text-heading">Language & Region</h3>
        <p className="mb-5 text-xs text-subtle">Set your preferred language and time zone</p>
        <div className="grid grid-cols-2 gap-5 max-w-lg">
          <div>
            <label className="mb-1.5 block text-[11px] font-medium text-subtle">Language</label>
            <select
              value={language}
              onChange={e => setLanguage(e.target.value)}
              className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-body focus:border-primary/50 focus:outline-none"
            >
              <option value="en">English</option>
              <option value="fr">Français</option>
              <option value="pt">Português</option>
              <option value="es">Español</option>
              <option value="ar">العربية</option>
              <option value="zh">中文</option>
              <option value="ha">Hausa</option>
              <option value="yo">Yorùbá</option>
              <option value="ig">Igbo</option>
              <option value="sw">Kiswahili</option>
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-[11px] font-medium text-subtle">Time Zone</label>
            <select
              value={timezone}
              onChange={e => setTimezone(e.target.value)}
              className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-body focus:border-primary/50 focus:outline-none"
            >
              <option value="UTC">UTC (GMT +0)</option>
              <option value="Africa/Lagos">Africa/Lagos (WAT +1)</option>
              <option value="Africa/Accra">Africa/Accra (GMT +0)</option>
              <option value="Africa/Nairobi">Africa/Nairobi (EAT +3)</option>
              <option value="Africa/Johannesburg">Africa/Johannesburg (SAST +2)</option>
              <option value="Africa/Cairo">Africa/Cairo (EET +2)</option>
              <option value="Europe/London">Europe/London (GMT)</option>
              <option value="Europe/Paris">Europe/Paris (CET +1)</option>
              <option value="America/New_York">America/New_York (EST -5)</option>
              <option value="America/Chicago">America/Chicago (CST -6)</option>
              <option value="America/Los_Angeles">America/Los_Angeles (PST -8)</option>
              <option value="Asia/Dubai">Asia/Dubai (GST +4)</option>
              <option value="Asia/Singapore">Asia/Singapore (SGT +8)</option>
              <option value="Asia/Tokyo">Asia/Tokyo (JST +9)</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}
