import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowLeft, Database, FileText, Scale, Shield } from 'lucide-react'

export const metadata: Metadata = {
  title: {
    template: '%s - Cogent Legal',
    default: 'Legal - Cogent',
  },
}

const NAV_LINKS = [
  { href: '/legal', label: 'Overview', icon: Scale },
  { href: '/legal/terms', label: 'Terms of Service', icon: FileText },
  { href: '/legal/privacy', label: 'Privacy Notice', icon: Shield },
  { href: '/legal/data-processing', label: 'Enterprise DPA', icon: Database },
]

export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-canvas">
      <header className="sticky top-0 z-30 border-b border-border bg-surface/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm font-medium text-body transition-colors hover:text-heading"
          >
            <ArrowLeft className="h-4 w-4" strokeWidth={1.5} />
            Back to Cogent
          </Link>
          <Link href="/" className="text-lg font-semibold tracking-tight text-heading">
            Cogent
          </Link>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-6 py-10 lg:grid lg:grid-cols-[220px_1fr] lg:gap-12">
        <aside className="mb-8 lg:mb-0">
          <nav className="sticky top-24 flex flex-row gap-1 overflow-x-auto pb-2 lg:flex-col lg:overflow-visible lg:pb-0">
            {NAV_LINKS.map(link => {
              const Icon = link.icon
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className="flex items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm text-body transition-colors hover:bg-muted hover:text-heading"
                >
                  <Icon className="h-4 w-4 flex-shrink-0 text-subtle" strokeWidth={1.5} />
                  {link.label}
                </Link>
              )
            })}
          </nav>
        </aside>

        <main className="min-w-0">{children}</main>
      </div>

      <footer className="mt-16 border-t border-border bg-surface">
        <div className="mx-auto max-w-5xl px-6 py-8">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <p className="text-xs text-subtle">&copy; {new Date().getFullYear()} Stem Systems Ltd. All rights reserved.</p>
            <div className="flex gap-6">
              <Link href="/legal/terms" className="text-xs text-subtle transition-colors hover:text-body">
                Terms
              </Link>
              <Link href="/legal/privacy" className="text-xs text-subtle transition-colors hover:text-body">
                Privacy
              </Link>
              <Link href="/legal/data-processing" className="text-xs text-subtle transition-colors hover:text-body">
                DPA
              </Link>
              <a href="mailto:legal@cogent.ai" className="text-xs text-subtle transition-colors hover:text-body">
                legal@cogent.ai
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
