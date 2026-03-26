'use client'

import Link from 'next/link'
import { useState } from 'react'
import { HelpCircle, FileText, Shield, Package, ChevronRight, ExternalLink, Search, Mail } from 'lucide-react'

// ── Article link ──────────────────────────────────────────────────────────────

function ArticleLink({ title, description, href }: { title: string; description: string; href: string }) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-xl border border-border bg-surface p-4 transition-all hover:border-primary/20 hover:shadow-sm group"
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-body group-hover:text-heading transition-colors">{title}</p>
        {description && <p className="mt-0.5 text-xs text-subtle">{description}</p>}
      </div>
      <ChevronRight className="h-4 w-4 flex-shrink-0 text-subtle group-hover:text-primary transition-colors" strokeWidth={1.5} />
    </Link>
  )
}

// ── Section header ────────────────────────────────────────────────────────────

function SectionHeader({ icon: Icon, title, description }: { icon: React.ElementType; title: string; description: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-muted">
        <Icon className="h-5 w-5 text-subtle" strokeWidth={1.5} />
      </div>
      <div>
        <h3 className="text-sm font-medium text-heading">{title}</h3>
        <p className="text-xs text-subtle">{description}</p>
      </div>
    </div>
  )
}

// ── License badge ─────────────────────────────────────────────────────────────

function LicenseBadge({ name, version, license }: { name: string; version: string; license: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-2.5">
      <div className="flex items-center gap-3">
        <p className="font-mono text-xs font-medium text-body">{name}</p>
        <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-subtle">{version}</span>
      </div>
      <span className="rounded-full border border-border bg-muted/50 px-2 py-0.5 text-[10px] text-subtle">{license}</span>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export function LegalSection() {
  const [helpQuery, setHelpQuery] = useState('')

  const filteredArticles = [
    { title: 'Getting started with Stem-Cogent', description: 'A walkthrough of the platform features', href: '/dashboard/home' },
    { title: 'How signals are generated', description: 'Understanding confidence scores and data sources', href: '/dashboard/signals' },
    { title: 'Creating your first data contract', description: 'Step-by-step guide to contract studio', href: '/dashboard/studio' },
    { title: 'Understanding the Library', description: 'AI-generated briefs and weekly reports explained', href: '/dashboard/library' },
    { title: 'API access and rate limits', description: 'Integrating Cogent data into your applications', href: '/dashboard/settings?tab=security' },
    { title: 'Billing and credit usage', description: 'How credits are calculated and billed', href: '/dashboard/settings?tab=plan' },
  ].filter(a =>
    !helpQuery || a.title.toLowerCase().includes(helpQuery.toLowerCase()) || a.description.toLowerCase().includes(helpQuery.toLowerCase())
  )

  return (
    <div className="flex flex-col gap-8">

      {/* ── Help Center ───────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="mb-5">
          <SectionHeader icon={HelpCircle} title="Help Center" description="Documentation, guides, and FAQs" />
        </div>

        {/* Search */}
        <div className="mb-4 flex items-center gap-2 rounded-xl border border-border bg-muted px-3 py-2 focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20">
          <Search className="h-4 w-4 flex-shrink-0 text-subtle" strokeWidth={1.5} />
          <input
            value={helpQuery}
            onChange={e => setHelpQuery(e.target.value)}
            placeholder="Search help articles…"
            className="flex-1 bg-transparent text-sm text-body placeholder:text-subtle focus:outline-none"
          />
        </div>

        {/* Articles */}
        <div className="flex flex-col gap-2">
          {filteredArticles.length > 0
            ? filteredArticles.map(a => <ArticleLink key={a.title} {...a} />)
            : <p className="py-4 text-center text-xs text-subtle">No articles match "{helpQuery}"</p>
          }
        </div>

        {/* Contact support */}
        <div className="mt-5 flex items-center justify-between rounded-xl border border-primary/20 bg-primary/5 px-4 py-3">
          <div>
            <p className="text-sm font-medium text-heading">Still need help?</p>
            <p className="text-xs text-subtle">Our support team responds within 4 hours on business days.</p>
          </div>
          <a
            href="mailto:support@cogent.ai"
            className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-medium text-white hover:bg-primary-hover transition-colors"
          >
            <Mail className="h-3.5 w-3.5" strokeWidth={1.5} />
            Contact support
          </a>
        </div>
      </div>

      {/* ── Terms of Service ─────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="mb-5">
          <SectionHeader icon={FileText} title="Terms of Service" description="Last updated: March 2026" />
        </div>
        <div className="prose prose-sm max-w-none text-subtle">
          <p className="text-xs leading-relaxed">
            By accessing and using the Stem-Cogent platform, you agree to be bound by our Terms of Service. These cover
            license scope &amp; restrictions, service level agreements (99.9% uptime), data ownership (User Content vs.
            Derived Intelligence), acceptable use policy, AI transparency commitments, and limitation of liability.
          </p>
          <p className="mt-3 text-xs leading-relaxed">
            Stem-Cogent reserves the right to modify these terms with 30 days&apos; notice. Enterprise customers with
            executed agreements are governed by their specific contract terms until renewal.
          </p>
        </div>
        <a
          href="/legal/terms"
          className="mt-4 flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
        >
          <ExternalLink className="h-3.5 w-3.5" strokeWidth={1.5} />
          Read full Terms of Service
        </a>
      </div>

      {/* ── Privacy Policy ────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="mb-5">
          <SectionHeader icon={Shield} title="Privacy Policy" description="NDPA 2023 & GDPR compliant — How we collect, use, and protect your data" />
        </div>
        <div className="grid grid-cols-2 gap-3 mb-5">
          {[
            { label: 'Data collected',   text: 'Account info, usage patterns, search queries, and contract definitions — strictly minimised' },
            { label: 'Data retention',   text: 'Active data retained while your account is active; deleted 90 days after closure' },
            { label: 'Third parties',    text: 'We do not sell your data. Sub-processors listed with 30-day notice of changes' },
            { label: 'Your rights',      text: 'Access, rectification, portability (JSON/CSV), erasure, and the right to object' },
          ].map(item => (
            <div key={item.label} className="rounded-xl border border-border bg-muted/40 p-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-subtle mb-1">{item.label}</p>
              <p className="text-xs leading-relaxed text-body">{item.text}</p>
            </div>
          ))}
        </div>
        <div className="flex gap-4">
          <a
            href="/legal/privacy"
            className="flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
          >
            <ExternalLink className="h-3.5 w-3.5" strokeWidth={1.5} />
            Read full Privacy Policy
          </a>
          <a
            href="/legal/data-processing"
            className="flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
          >
            <ExternalLink className="h-3.5 w-3.5" strokeWidth={1.5} />
            Data Processing Addendum
          </a>
        </div>
      </div>

      {/* ── Licenses ─────────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="mb-5">
          <SectionHeader icon={Package} title="Open Source Licenses" description="Third-party libraries used in this product" />
        </div>
        <div className="flex flex-col gap-2">
          {[
            { name: 'Next.js',        version: '14.2.4',  license: 'MIT'     },
            { name: 'React',          version: '18.3.1',  license: 'MIT'     },
            { name: 'Tailwind CSS',   version: '3.4.3',   license: 'MIT'     },
            { name: 'Recharts',       version: '2.12.5',  license: 'MIT'     },
            { name: 'Lucide React',   version: '0.378.0', license: 'ISC'     },
            { name: 'Auth0 Next.js',  version: '3.5.0',   license: 'MIT'     },
            { name: 'Leaflet',        version: '1.9.4',   license: 'BSD-2'   },
            { name: 'React Flow',     version: '11.11.3', license: 'MIT'     },
            { name: 'Framer Motion',  version: '11.2.9',  license: 'MIT'     },
          ].map(l => <LicenseBadge key={l.name} {...l} />)}
        </div>
      </div>

      {/* ── App version ──────────────────────────────────────────────────── */}
      <p className="text-center text-[11px] text-subtle">
        Stem-Cogent v1.0.0 · Built Mar 2026 · Release changes are published through deployment change management.
      </p>
    </div>
  )
}
