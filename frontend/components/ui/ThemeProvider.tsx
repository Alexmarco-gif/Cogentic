'use client'

import { useEffect } from 'react'
import { useThemeStore } from '@/lib/stores/themeStore'

/**
 * Applies the stored theme class to <html> on mount and on every change.
 * Must be rendered inside the <body> so it runs on the client.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useThemeStore((s) => s.theme)

  // Subscribe to zustand rehydration so the effect re-runs
  // after the persisted store has read from localStorage
  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
  }, [theme])

  // Also listen for the store rehydration event
  useEffect(() => {
    const unsub = useThemeStore.persist.onFinishHydration((state) => {
      const root = document.documentElement
      if (state.theme === 'dark') {
        root.classList.add('dark')
      } else {
        root.classList.remove('dark')
      }
    })
    return unsub
  }, [])

  return <>{children}</>
}
