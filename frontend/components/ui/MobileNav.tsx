'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Home, Search, Activity, Globe, BookOpen,
  FileCode2, Settings, X,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'

// ── Route definitions ─────────────────────────────────────────────────────────

const PRIMARY_TABS = [
  { href: '/dashboard/home',        icon: Home,     label: 'Home'      },
  { href: '/dashboard/investigate', icon: Search,   label: 'Search'    },
  { href: '/dashboard/signals',     icon: Activity, label: 'Signals'   },
  { href: '/dashboard/domains',     icon: Globe,    label: 'Domains'   },
  { href: '/dashboard/library',     icon: BookOpen, label: 'Library'   },
] as const

const MORE_TABS = [
  { href: '/dashboard/studio',   icon: FileCode2, label: 'Studio'   },
  { href: '/dashboard/settings', icon: Settings,  label: 'Settings' },
] as const

// ── Component ─────────────────────────────────────────────────────────────────

/**
 * Bottom tab bar visible on mobile (hidden on md+).
 * "More" button opens a spring-animated bottom sheet with additional routes.
 */
export function MobileNav() {
  const pathname    = usePathname()
  const [open, setOpen] = useState(false)

  return (
    <>
      {/* ── Bottom tab bar ──────────────────────────────────────── */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-40 flex md:hidden border-t border-border bg-surface/95 backdrop-blur-sm"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
        aria-label="Mobile navigation"
      >
        {PRIMARY_TABS.map(({ href, icon: Icon, label }) => {
          const active = pathname?.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex flex-1 flex-col items-center justify-center py-2 gap-0.5',
                'text-[10px] font-medium transition-colors',
                active ? 'text-primary' : 'text-subtle hover:text-body',
              )}
              aria-current={active ? 'page' : undefined}
            >
              <Icon
                size={20}
                strokeWidth={1.5}
                className={active ? 'stroke-primary' : undefined}
              />
              <span>{label}</span>
            </Link>
          )
        })}

        {/* More ··· button */}
        <button
          onClick={() => setOpen(true)}
          aria-label="More navigation options"
          className="flex flex-1 flex-col items-center justify-center py-2 gap-0.5 text-[10px] font-medium text-subtle hover:text-body transition-colors"
        >
          <span className="flex gap-0.5 items-center h-5" aria-hidden="true">
            <span className="w-1 h-1 rounded-full bg-current" />
            <span className="w-1 h-1 rounded-full bg-current" />
            <span className="w-1 h-1 rounded-full bg-current" />
          </span>
          <span>More</span>
        </button>
      </nav>

      {/* ── More sheet ──────────────────────────────────────────── */}
      <AnimatePresence>
        {open && (
          <>
            {/* Backdrop */}
            <motion.div
              className="fixed inset-0 z-50 bg-black/40 md:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, transition: { duration: 0.15 } }}
              onClick={() => setOpen(false)}
              aria-hidden="true"
            />

            {/* Sheet */}
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label="More navigation"
              className="fixed bottom-0 left-0 right-0 z-50 rounded-t-3xl border-t border-border bg-surface px-6 pt-5 md:hidden"
              style={{ paddingBottom: 'max(2rem, env(safe-area-inset-bottom))' }}
              initial={{ y: '100%' }}
              animate={{ y: 0, transition: { type: 'spring', damping: 32, stiffness: 320 } }}
              exit={{ y: '100%', transition: { duration: 0.2, ease: 'easeIn' } }}
            >
              {/* Handle */}
              <div
                aria-hidden="true"
                className="absolute top-3 left-1/2 -translate-x-1/2 w-10 h-1 rounded-full bg-border"
              />

              <div className="flex items-center justify-between mb-5">
                <p className="text-sm font-medium text-heading">More</p>
                <button
                  onClick={() => setOpen(false)}
                  className="rounded-full p-1.5 hover:bg-muted transition-colors text-subtle"
                  aria-label="Close"
                >
                  <X size={16} strokeWidth={1.5} />
                </button>
              </div>

              <div className="grid grid-cols-4 gap-3">
                {MORE_TABS.map(({ href, icon: Icon, label }) => (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      'flex flex-col items-center gap-2 rounded-2xl p-4 transition-colors',
                      pathname?.startsWith(href)
                        ? 'bg-primary/10 text-primary'
                        : 'bg-muted text-body hover:bg-muted/70',
                    )}
                  >
                    <Icon size={22} strokeWidth={1.5} />
                    <span className="text-[11px] font-medium">{label}</span>
                  </Link>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
