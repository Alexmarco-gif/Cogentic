import type { Metadata } from 'next'
import Link from 'next/link'
import { FileText, Shield, Database, ArrowRight, Scale, Globe, Building2 } from 'lucide-react'

export const metadata: Metadata = { title: 'Legal' }

const DOCUMENTS = [
  {
    href:        '/legal/terms',
    icon:        FileText,
    title:       'Terms of Service',
    description: 'License scope, acceptable use, SLA commitments, IP ownership, and limitation of liability.',
    updated:     'March 2026',
  },
  {
    href:        '/legal/privacy',
    icon:        Shield,
    title:       'Privacy Policy',
    description: 'How we collect, process, store, and protect data — compliant with NDPA 2023, GDPR, and the EU Data Act.',
    updated:     'March 2026',
  },
  {
    href:        '/legal/data-processing',
    icon:        Database,
    title:       'Data Processing Addendum',
    description: 'Controller/Processor roles, sub-processor transparency, security measures, and cross-border transfer safeguards.',
    updated:     'March 2026',
  },
]

const HIGHLIGHTS = [
  {
    icon:  Scale,
    title: 'Decision Support, Not Advice',
    text:  'Stem-Cogent provides confidence-calibrated signals for informational purposes. All business decisions remain your responsibility.',
  },
  {
    icon:  Globe,
    title: 'Global Compliance',
    text:  'Our legal framework covers NDPA 2023 (Nigeria), GDPR (EU), the EU Data Act 2025, and AI transparency requirements.',
  },
  {
    icon:  Building2,
    title: 'Enterprise-Grade Data Governance',
    text:  'Signal Contracts define data ownership. Your input stays yours; derived intelligence is governed by clear IP terms.',
  },
]

export default function LegalHubPage() {
  return (
    <div className="flex flex-col gap-10">
      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-display text-heading mb-2">Legal &amp; Compliance</h1>
        <p className="text-sm text-subtle leading-relaxed max-w-[65ch]">
          Transparency is a core principle of the Cogent platform. These documents govern how we operate,
          process data, and protect your rights as a user and enterprise customer.
        </p>
      </div>

      {/* ── Document cards ────────────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {DOCUMENTS.map(doc => {
          const Icon = doc.icon
          return (
            <Link
              key={doc.href}
              href={doc.href}
              className="group flex flex-col justify-between rounded-2xl border border-border bg-surface p-6 shadow-card transition-all hover:border-primary/30 hover:shadow-md"
            >
              <div>
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Icon className="h-5 w-5" strokeWidth={1.5} />
                </div>
                <h2 className="text-sm font-semibold text-heading mb-1">{doc.title}</h2>
                <p className="text-xs text-subtle leading-relaxed">{doc.description}</p>
              </div>
              <div className="mt-5 flex items-center justify-between">
                <span className="text-[10px] text-subtle uppercase tracking-wider">Updated {doc.updated}</span>
                <ArrowRight className="h-4 w-4 text-subtle group-hover:text-primary transition-colors" strokeWidth={1.5} />
              </div>
            </Link>
          )
        })}
      </div>

      {/* ── Key highlights ────────────────────────────────────────────────── */}
      <div>
        <h2 className="text-heading text-heading mb-4">Key Principles</h2>
        <div className="flex flex-col gap-3">
          {HIGHLIGHTS.map(h => {
            const Icon = h.icon
            return (
              <div key={h.title} className="flex items-start gap-4 rounded-xl border border-border bg-surface p-5">
                <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-muted">
                  <Icon className="h-4 w-4 text-subtle" strokeWidth={1.5} />
                </div>
                <div>
                  <p className="text-sm font-medium text-heading">{h.title}</p>
                  <p className="mt-0.5 text-xs text-subtle leading-relaxed">{h.text}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Jurisdictional notice ─────────────────────────────────────────── */}
      <div className="rounded-2xl border border-primary/20 bg-primary/5 p-6">
        <h3 className="text-sm font-semibold text-heading mb-2">Jurisdictional Governing Law</h3>
        <p className="text-xs text-body leading-relaxed">
          These agreements are governed by the laws of the Federal Republic of Nigeria.
          Any disputes arising from or relating to the use of the Cogent platform shall be subject
          to the exclusive jurisdiction of the Federal High Court of Nigeria, unless a separate
          enterprise agreement specifies alternative jurisdiction. For EU-based customers, GDPR
          provisions apply concurrently.
        </p>
      </div>

      {/* ── Contact ───────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between rounded-xl border border-border bg-surface px-6 py-4">
        <div>
          <p className="text-sm font-medium text-heading">Questions about our legal documents?</p>
          <p className="text-xs text-subtle">Our legal and compliance team is available for enterprise inquiries.</p>
        </div>
        <a
          href="mailto:legal@cogent.ai"
          className="flex-shrink-0 rounded-xl bg-primary px-5 py-2 text-xs font-medium text-white hover:bg-primary-hover transition-colors"
        >
          Contact Legal
        </a>
      </div>
    </div>
  )
}
