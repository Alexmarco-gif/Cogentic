import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowLeft, FileText, Shield, Database, Scale } from 'lucide-react'

export const metadata: Metadata = {
  title: {
    template: '%s — Stem-Cogent Legal',
    default:  'Legal — Stem-Cogent',
  },
}

const NAV_LINKS = [
  { href: '/legal',                label: 'Overview',               icon: Scale },
  { href: '/legal/terms',          label: 'Terms of Service',       icon: FileText },
  { href: '/legal/privacy',        label: 'Privacy Policy',         icon: Shield },
  { href: '/legal/data-processing', label: 'Data Processing',       icon: Database },
]

export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-canvas">
      {/* ── Top bar ───────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 border-b border-border bg-surface/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm font-medium text-body hover:text-heading transition-colors"
          >
            <ArrowLeft className="h-4 w-4" strokeWidth={1.5} />
            Back to Stem-Cogent
          </Link>
          <Link href="/" className="text-lg font-semibold text-heading tracking-tight">
            Cogent
          </Link>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-6 py-10 lg:grid lg:grid-cols-[220px_1fr] lg:gap-12">
        {/* ── Sidebar nav ─────────────────────────────────────────────────── */}
        <aside className="mb-8 lg:mb-0">
          <nav className="sticky top-24 flex flex-row lg:flex-col gap-1 overflow-x-auto lg:overflow-visible pb-2 lg:pb-0">
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

        {/* ── Content ─────────────────────────────────────────────────────── */}
        <main className="min-w-0">{children}</main>
      </div>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer className="border-t border-border bg-surface mt-16">
        <div className="mx-auto max-w-5xl px-6 py-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs text-subtle">&copy; {new Date().getFullYear()} Cogent Technologies Ltd. All rights reserved.</p>
            <div className="flex gap-6">
              <Link href="/legal/terms" className="text-xs text-subtle hover:text-body transition-colors">Terms</Link>
              <Link href="/legal/privacy" className="text-xs text-subtle hover:text-body transition-colors">Privacy</Link>
              <Link href="/legal/data-processing" className="text-xs text-subtle hover:text-body transition-colors">DPA</Link>
              <a href="mailto:legal@cogent.ai" className="text-xs text-subtle hover:text-body transition-colors">legal@cogent.ai</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
