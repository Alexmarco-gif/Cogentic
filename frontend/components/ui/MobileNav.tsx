'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Activity,
  BookOpen,
  FileCode2,
  Globe,
  Home,
  Settings,
  X,
} from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import { cn } from '@/lib/utils'

const PRIMARY_TABS = [
  { href: '/dashboard/home', icon: Home, label: 'Home' },
  { href: '/dashboard/signals', icon: Activity, label: 'Signals' },
  { href: '/dashboard/domains', icon: Globe, label: 'Domains' },
  { href: '/dashboard/library', icon: BookOpen, label: 'Library' },
] as const

const MORE_TABS = [
  { href: '/dashboard/studio', icon: FileCode2, label: 'Studio' },
  { href: '/dashboard/settings', icon: Settings, label: 'Settings' },
] as const

export function MobileNav() {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  return (
    <>
      <nav
        className="glass fixed bottom-3 left-3 right-3 z-40 flex rounded-[24px] border md:hidden"
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
                'flex flex-1 flex-col items-center justify-center gap-1 py-3 text-[0.68rem] font-semibold transition-all duration-200',
                active ? 'text-primary' : 'text-subtle',
              )}
              aria-current={active ? 'page' : undefined}
            >
              <span className={cn(
                'flex h-9 w-9 items-center justify-center rounded-2xl transition-all duration-200',
                active ? 'bg-primary/10 text-primary' : 'text-subtle',
              )}>
                <Icon size={18} strokeWidth={1.8} />
              </span>
              <span>{label}</span>
            </Link>
          )
        })}

        <button
          onClick={() => setOpen(true)}
          aria-label="More navigation options"
          className="flex flex-1 flex-col items-center justify-center gap-1 py-3 text-[0.68rem] font-semibold text-subtle transition-colors"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-surface">
            <span className="flex items-center gap-1" aria-hidden="true">
              <span className="h-1 w-1 rounded-full bg-current" />
              <span className="h-1 w-1 rounded-full bg-current" />
              <span className="h-1 w-1 rounded-full bg-current" />
            </span>
          </span>
          <span>More</span>
        </button>
      </nav>

      <AnimatePresence>
        {open && (
          <>
            <motion.div
              className="fixed inset-0 z-50 bg-black/40 md:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, transition: { duration: 0.15 } }}
              onClick={() => setOpen(false)}
              aria-hidden="true"
            />

            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label="More navigation"
              className="surface-elevated fixed bottom-0 left-0 right-0 z-50 rounded-t-[30px] px-5 pt-5 md:hidden"
              style={{ paddingBottom: 'max(2rem, env(safe-area-inset-bottom))' }}
              initial={{ y: '100%' }}
              animate={{ y: 0, transition: { type: 'spring', damping: 30, stiffness: 320 } }}
              exit={{ y: '100%', transition: { duration: 0.2, ease: 'easeIn' } }}
            >
              <div
                aria-hidden="true"
                className="mx-auto mb-4 h-1 w-12 rounded-full bg-border"
              />

              <div className="mb-5 flex items-center justify-between">
                <div>
                  <p className="text-title">More actions</p>
                  <p className="text-[0.78rem] text-subtle">Keep the essentials visible. Open the rest when you need them.</p>
                </div>
                <button
                  onClick={() => setOpen(false)}
                  className="focus-ring button-press rounded-full p-2 text-subtle transition-colors hover:bg-surface-2 hover:text-heading"
                  aria-label="Close"
                >
                  <X size={16} strokeWidth={1.8} />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {MORE_TABS.map(({ href, icon: Icon, label }) => (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      'button-press rounded-[22px] border px-4 py-4 transition-all duration-200',
                      pathname?.startsWith(href)
                        ? 'border-primary/20 bg-primary/10 text-primary'
                        : 'border-border bg-surface text-body hover:bg-surface-2',
                    )}
                  >
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-2xl bg-surface-2">
                      <Icon size={18} strokeWidth={1.8} />
                    </div>
                    <p className="text-[0.86rem] font-semibold">{label}</p>
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
