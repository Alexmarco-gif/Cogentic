'use client'

import { useEffect, useState } from 'react'
import { Globe, Moon, Sun } from 'lucide-react'
import { useThemeStore } from '@/lib/stores/themeStore'

const PREFERENCES_STORAGE_KEY = 'cogent-device-preferences'

interface DevicePreferences {
  language: string
  timezone: string
}

const DEFAULT_PREFERENCES: DevicePreferences = {
  language: 'en',
  timezone: 'UTC',
}

function loadStoredPreferences(): DevicePreferences {
  if (typeof window === 'undefined') {
    return DEFAULT_PREFERENCES
  }

  try {
    const raw = window.localStorage.getItem(PREFERENCES_STORAGE_KEY)
    if (!raw) {
      return {
        language: navigator.language?.slice(0, 2) || DEFAULT_PREFERENCES.language,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || DEFAULT_PREFERENCES.timezone,
      }
    }

    const parsed = JSON.parse(raw) as Partial<DevicePreferences>
    return {
      language: typeof parsed.language === 'string' ? parsed.language : DEFAULT_PREFERENCES.language,
      timezone: typeof parsed.timezone === 'string' ? parsed.timezone : DEFAULT_PREFERENCES.timezone,
    }
  } catch {
    return DEFAULT_PREFERENCES
  }
}

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

export function PreferencesSection() {
  const { theme, setTheme } = useThemeStore()
  const [language, setLanguage] = useState(DEFAULT_PREFERENCES.language)
  const [timezone, setTimezone] = useState(DEFAULT_PREFERENCES.timezone)

  useEffect(() => {
    const stored = loadStoredPreferences()
    setLanguage(stored.language)
    setTimezone(stored.timezone)
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    window.localStorage.setItem(
      PREFERENCES_STORAGE_KEY,
      JSON.stringify({ language, timezone }),
    )
  }, [language, timezone])

  return (
    <div className="flex flex-col gap-8">
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <h3 className="mb-1 text-sm font-medium text-heading">Appearance</h3>
        <p className="mb-5 text-xs text-subtle">
          Choose the visual mode for this browser. Theme changes are saved on this device.
        </p>
        <div className="grid grid-cols-2 gap-3">
          <OptionCard
            value="light"
            selected={theme === 'light'}
            onSelect={(value) => setTheme(value)}
            icon={Sun}
            label="Light"
            description="Clean white interface"
          />
          <OptionCard
            value="dark"
            selected={theme === 'dark'}
            onSelect={(value) => setTheme(value)}
            icon={Moon}
            label="Dark"
            description="Easy on the eyes"
          />
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <h3 className="mb-1 text-sm font-medium text-heading">Language & Region</h3>
        <p className="mb-5 text-xs text-subtle">
          These are device-level preferences today. Workspace-wide localization is not yet enabled.
        </p>
        <div className="grid max-w-lg grid-cols-1 gap-5 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-[11px] font-medium text-subtle">Language</label>
            <select
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
              className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-body focus:border-primary/50 focus:outline-none"
            >
              <option value="en">English</option>
              <option value="fr">French</option>
              <option value="pt">Portuguese</option>
              <option value="es">Spanish</option>
              <option value="ar">Arabic</option>
              <option value="zh">Chinese</option>
              <option value="ha">Hausa</option>
              <option value="yo">Yoruba</option>
              <option value="ig">Igbo</option>
              <option value="sw">Swahili</option>
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-[11px] font-medium text-subtle">Time Zone</label>
            <select
              value={timezone}
              onChange={(event) => setTimezone(event.target.value)}
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

        <div className="mt-5 rounded-xl border border-border bg-muted/30 px-4 py-3 text-xs text-subtle">
          These preferences help the interface feel consistent on this device, but they do not yet change organization-wide reports, alerts, or exported documents.
        </div>
      </div>
    </div>
  )
}
