'use client'

import { useEffect } from 'react'

/**
 * Registers the PWA service worker on mount.
 * Only runs in production and in browsers that support service workers.
 * Renders no UI — drop it anywhere in the component tree.
 */
export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      return
    }

    if (process.env.NODE_ENV !== 'production') {
      // Prevent stale production SW from hijacking local development.
      navigator.serviceWorker.getRegistrations().then(regs => {
        regs.forEach(reg => {
          void reg.unregister()
        })
      })
      return
    }

    navigator.serviceWorker
      .register('/sw.js', { scope: '/' })
      .then(reg => console.info('[SW] Registered:', reg.scope))
      .catch(err => console.warn('[SW] Registration failed:', err))
  }, [])

  return null
}
