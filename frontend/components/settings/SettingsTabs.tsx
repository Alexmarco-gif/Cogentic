'use client'

import { cn } from '@/lib/utils'
import type { SettingsTab } from '@/lib/hooks/useSettings'
import { SETTINGS_TABS } from '@/lib/hooks/useSettings'

interface SettingsTabsProps {
  activeTab: SettingsTab
  onTabChange: (tab: SettingsTab) => void
}

export function SettingsTabs({ activeTab, onTabChange }: SettingsTabsProps) {
  return (
    <div className="border-b border-border">
      <nav className="flex gap-0 overflow-x-auto" aria-label="Settings navigation">
        {SETTINGS_TABS.map(tab => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={cn(
                'relative whitespace-nowrap px-4 py-3 text-sm transition-colors focus-visible:outline-none',
                isActive
                  ? 'font-medium text-heading'
                  : 'font-normal text-subtle hover:text-body',
              )}
            >
              {tab.label}
              {isActive && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full bg-primary" />
              )}
            </button>
          )
        })}
      </nav>
    </div>
  )
}
