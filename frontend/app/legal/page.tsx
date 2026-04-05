import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowRight, Building2, Database, FileText, Globe, Scale, Shield } from 'lucide-react'

export const metadata: Metadata = { title: 'Legal' }

const DOCUMENTS = [
  {
    href: '/legal/terms',
    icon: FileText,
    title: 'Terms of Service',
    description: 'Service rules, account use, billing, permitted use, IP, and liability terms for Cogent.',
    updated: 'March 2026',
  },
  {
    href: '/legal/privacy',
    icon: Shield,
    title: 'Privacy Notice',
    description: 'How Stem Systems Ltd. collects, uses, protects, and shares personal data in Cogent.',
    updated: 'March 2026',
  },
  {
    href: '/legal/data-processing',
    icon: Database,
    title: 'Enterprise DPA',
    description: 'Controller-processor summary for enterprise customers who need procurement or data processing terms.',
    updated: 'March 2026',
  },
]

const HIGHLIGHTS = [
  {
    icon: Scale,
    title: 'Nigeria-First Legal Basis',
    text: 'Our public legal documents are written primarily around the Nigeria Data Protection Act, 2023 and Nigerian contract and consumer law expectations.',
  },
  {
    icon: Globe,
    title: 'Cross-Border Processing With Safeguards',
    text: 'Where data moves across borders, we rely on lawful transfer mechanisms and enterprise-specific terms where needed.',
  },
  {
    icon: Building2,
    title: 'Company and Product Clarity',
    text: 'Stem Systems Ltd. is the company. Cogent is the product. The legal documents now reflect that distinction clearly.',
  },
]

export default function LegalHubPage() {
  return (
    <div className="flex flex-col gap-10">
      <div>
        <h1 className="mb-2 text-display text-heading">Legal and Compliance</h1>
        <p className="max-w-[65ch] text-sm leading-relaxed text-subtle">
          These documents explain the legal terms for using Cogent, how Stem Systems Ltd. handles personal data, and how
          enterprise data processing requests are handled.
        </p>
      </div>

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
                <h2 className="mb-1 text-sm font-semibold text-heading">{doc.title}</h2>
                <p className="text-xs leading-relaxed text-subtle">{doc.description}</p>
              </div>
              <div className="mt-5 flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-wider text-subtle">Updated {doc.updated}</span>
                <ArrowRight className="h-4 w-4 text-subtle transition-colors group-hover:text-primary" strokeWidth={1.5} />
              </div>
            </Link>
          )
        })}
      </div>

      <div>
        <h2 className="mb-4 text-heading text-heading">Key Principles</h2>
        <div className="flex flex-col gap-3">
          {HIGHLIGHTS.map(item => {
            const Icon = item.icon
            return (
              <div key={item.title} className="flex items-start gap-4 rounded-xl border border-border bg-surface p-5">
                <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-muted">
                  <Icon className="h-4 w-4 text-subtle" strokeWidth={1.5} />
                </div>
                <div>
                  <p className="text-sm font-medium text-heading">{item.title}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-subtle">{item.text}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="rounded-2xl border border-primary/20 bg-primary/5 p-6">
        <h3 className="mb-2 text-sm font-semibold text-heading">Governing law</h3>
        <p className="text-xs leading-relaxed text-body">
          Unless a separate enterprise agreement says otherwise, use of Cogent is governed by the laws of the Federal
          Republic of Nigeria.
        </p>
      </div>

      <div className="flex items-center justify-between rounded-xl border border-border bg-surface px-6 py-4">
        <div>
          <p className="text-sm font-medium text-heading">Questions about our legal documents?</p>
          <p className="text-xs text-subtle">Our legal team can help with contract, privacy, and enterprise review requests.</p>
        </div>
        <a
          href="mailto:legal@cogent.ai"
          className="flex-shrink-0 rounded-xl bg-primary px-5 py-2 text-xs font-medium text-white transition-colors hover:bg-primary-hover"
        >
          Contact Legal
        </a>
      </div>
    </div>
  )
}
