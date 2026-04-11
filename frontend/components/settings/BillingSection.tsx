'use client'

import { useMemo, useState } from 'react'
import { Check, CreditCard, ExternalLink, Mail, ReceiptText } from 'lucide-react'

import type { PaymentCard, BillingContact, Invoice, InvoiceStatus } from '@/lib/hooks/useSettings'

const STATUS_STYLES: Record<InvoiceStatus, string> = {
  Paid: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  Pending: 'border-amber-200 bg-amber-50 text-amber-700',
  Cancelled: 'border-rose-200 bg-rose-50 text-rose-700',
  Refund: 'border-sky-200 bg-sky-50 text-sky-700',
}

function FormField({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
}: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  type?: string
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[0.74rem] font-semibold uppercase tracking-[0.18em] text-subtle">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="focus-ring h-12 w-full rounded-[18px] border border-border bg-surface px-4 text-[0.92rem] text-heading placeholder:text-subtle transition-all duration-200 hover:border-border-hover"
      />
    </label>
  )
}

function SectionShell({
  eyebrow,
  title,
  description,
  action,
  children,
}: {
  eyebrow: string
  title: string
  description: string
  action?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="rounded-[28px] border border-border bg-surface p-5 shadow-card sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h3 className="mt-2 text-title text-heading">{title}</h3>
          <p className="mt-2 text-sm text-subtle">{description}</p>
        </div>
        {action}
      </div>
      <div className="mt-5">{children}</div>
    </div>
  )
}

interface BillingSectionProps {
  card: PaymentCard
  billingContact: BillingContact
  invoices: Invoice[]
  selectedInvoices: Set<string>
  onCardChange: (patch: Partial<PaymentCard>) => void
  onContactChange: (contact: BillingContact) => void
  onToggleInvoice: (id: string) => void
}

export function BillingSection({
  card,
  billingContact,
  invoices,
  selectedInvoices,
  onCardChange,
  onContactChange,
  onToggleInvoice,
}: BillingSectionProps) {
  const [showCardForm, setShowCardForm] = useState(false)

  const maskedNumber = useMemo(() => {
    const digits = card.cardNumber.replace(/\D/g, '')
    if (!digits) return 'No payment method added yet'
    return `•••• ${digits.slice(-4)}`
  }, [card.cardNumber])

  const allSelected = invoices.length > 0 && selectedInvoices.size === invoices.length

  function toggleAllInvoices() {
    if (allSelected) {
      invoices.forEach((invoice) => {
        if (selectedInvoices.has(invoice.id)) onToggleInvoice(invoice.id)
      })
      return
    }

    invoices.forEach((invoice) => {
      if (!selectedInvoices.has(invoice.id)) onToggleInvoice(invoice.id)
    })
  }

  return (
    <div className="flex flex-col gap-6">
      <SectionShell
        eyebrow="Billing"
        title="Payment method and billing contact"
        description="Keep saved payment details and invoice recipients up to date without exposing a heavy card form by default."
        action={
          <button
            onClick={() => setShowCardForm((value) => !value)}
            className="button-press inline-flex h-11 items-center justify-center rounded-[18px] border border-border bg-surface px-4 text-[0.84rem] font-semibold text-heading transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover hover:bg-surface-2"
          >
            {showCardForm ? 'Hide update form' : 'Update payment details'}
          </button>
        }
      >
        <div className="grid gap-4 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          <div className="rounded-[24px] border border-border bg-[linear-gradient(135deg,#111827,#1f2c43)] p-5 text-white shadow-[0_24px_70px_-40px_rgba(15,23,42,0.9)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-white/65">Saved method</p>
                <p className="mt-3 text-[1.15rem] font-semibold">{maskedNumber}</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10">
                <CreditCard className="h-5 w-5 text-white" strokeWidth={1.7} />
              </div>
            </div>

            <div className="mt-8 flex items-end justify-between gap-4">
              <div>
                <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-white/65">Cardholder</p>
                <p className="mt-1 text-[0.9rem] font-medium text-white/90">
                  {card.nameOnCard || 'Add the billing cardholder name'}
                </p>
              </div>
              <div className="text-right">
                <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-white/65">Expiry</p>
                <p className="mt-1 text-[0.9rem] font-medium text-white/90">{card.expiry || 'MM / YYYY'}</p>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-[24px] border border-border bg-muted/35 px-4 py-4">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-surface text-subtle">
                  <Mail className="h-4 w-4" strokeWidth={1.7} />
                </div>
                <div className="min-w-0">
                  <p className="text-[0.82rem] font-semibold text-heading">Billing email</p>
                  <p className="mt-1 text-[0.8rem] leading-relaxed text-subtle">
                    Invoices and payment confirmations are sent here.
                  </p>
                  <p className="mt-3 text-[0.92rem] font-medium text-body">{billingContact.email || 'No billing email added yet'}</p>
                </div>
              </div>
            </div>

            <div className="rounded-[24px] border border-border bg-surface px-4 py-4">
              <p className="text-[0.74rem] font-semibold uppercase tracking-[0.18em] text-subtle">Recipient</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={() => onContactChange({ ...billingContact, mode: 'existing' })}
                  className={`button-press rounded-[20px] border px-4 py-4 text-left transition-all ${
                    billingContact.mode === 'existing'
                      ? 'border-primary/20 bg-primary/6'
                      : 'border-border bg-surface hover:border-border-hover hover:bg-surface-2'
                  }`}
                >
                  <p className="text-[0.84rem] font-semibold text-heading">Use account email</p>
                  <p className="mt-1 text-[0.78rem] text-subtle">{billingContact.email || 'Sync from your account email'}</p>
                </button>

                <button
                  type="button"
                  onClick={() => onContactChange({ ...billingContact, mode: 'other' })}
                  className={`button-press rounded-[20px] border px-4 py-4 text-left transition-all ${
                    billingContact.mode === 'other'
                      ? 'border-primary/20 bg-primary/6'
                      : 'border-border bg-surface hover:border-border-hover hover:bg-surface-2'
                  }`}
                >
                  <p className="text-[0.84rem] font-semibold text-heading">Use another inbox</p>
                  <p className="mt-1 text-[0.78rem] text-subtle">Send invoices to finance or procurement.</p>
                </button>
              </div>

              {billingContact.mode === 'other' ? (
                <div className="mt-4">
                  <FormField
                    label="Billing email"
                    value={billingContact.email}
                    onChange={(value) => onContactChange({ ...billingContact, email: value })}
                    placeholder="billing@company.com"
                    type="email"
                  />
                </div>
              ) : null}
            </div>
          </div>
        </div>

        {showCardForm ? (
          <div className="mt-4 rounded-[24px] border border-border bg-muted/25 p-4 sm:p-5">
            <div className="grid gap-4 md:grid-cols-2">
              <FormField
                label="Cardholder name"
                value={card.nameOnCard}
                onChange={(value) => onCardChange({ nameOnCard: value })}
                placeholder="Stem Systems Ltd."
              />
              <FormField
                label="Card number"
                value={card.cardNumber}
                onChange={(value) => onCardChange({ cardNumber: value })}
                placeholder="•••• •••• •••• ••••"
              />
              <FormField
                label="Expiry"
                value={card.expiry}
                onChange={(value) => onCardChange({ expiry: value })}
                placeholder="MM / YYYY"
              />
              <FormField
                label="CVV"
                value={card.cvv}
                onChange={(value) => onCardChange({ cvv: value })}
                placeholder="•••"
                type="password"
              />
            </div>
          </div>
        ) : null}
      </SectionShell>

      <SectionShell
        eyebrow="Invoices"
        title="Billing history"
        description="Review billing records, select invoices, and keep payment history easy to scan on any screen size."
        action={
          <button
            onClick={toggleAllInvoices}
            className="button-press inline-flex h-11 items-center justify-center rounded-[18px] border border-border bg-surface px-4 text-[0.82rem] font-semibold text-heading transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover hover:bg-surface-2"
          >
            {allSelected ? 'Clear selection' : 'Select all'}
          </button>
        }
      >
        {invoices.length === 0 ? (
          <div className="rounded-[24px] border border-dashed border-border bg-muted/20 px-4 py-5 text-sm text-subtle">
            No invoices yet. Your first billing record will appear here after the first successful payment cycle.
          </div>
        ) : (
          <>
            <div className="space-y-3 md:hidden">
              {invoices.map((invoice) => {
                const isSelected = selectedInvoices.has(invoice.id)

                return (
                  <button
                    key={invoice.id}
                    type="button"
                    onClick={() => onToggleInvoice(invoice.id)}
                    className={`w-full rounded-[24px] border px-4 py-4 text-left transition-all ${
                      isSelected ? 'border-primary/20 bg-primary/6' : 'border-border bg-surface hover:bg-surface-2'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-[0.88rem] font-semibold text-heading">{invoice.name}</p>
                        <p className="mt-1 text-[0.78rem] text-subtle">{invoice.date}</p>
                      </div>
                      <span className={`rounded-full border px-2.5 py-1 text-[0.72rem] font-semibold ${STATUS_STYLES[invoice.status]}`}>
                        {invoice.status}
                      </span>
                    </div>

                    <div className="mt-4 flex items-center justify-between gap-3">
                      <div>
                        <p className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-subtle">Amount</p>
                        <p className="mt-1 text-[0.96rem] font-semibold text-heading">${invoice.amount.toLocaleString()}</p>
                      </div>
                      <span
                        className={`inline-flex h-6 w-6 items-center justify-center rounded-full border ${
                          isSelected ? 'border-primary bg-primary text-white' : 'border-border bg-surface text-transparent'
                        }`}
                      >
                        <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
                      </span>
                    </div>

                    <div className="mt-4 flex items-center gap-2 text-[0.78rem] font-medium text-primary">
                      <ExternalLink className="h-3.5 w-3.5" strokeWidth={1.7} />
                      {invoice.tracking}
                    </div>
                    <p className="mt-1 text-[0.76rem] text-subtle">{invoice.address}</p>
                  </button>
                )
              })}
            </div>

            <div className="hidden overflow-x-auto md:block">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-border text-[0.68rem] uppercase tracking-[0.18em] text-subtle">
                  <tr>
                    <th className="pb-3 pr-4 font-semibold">Select</th>
                    <th className="pb-3 pr-4 font-semibold">Invoice</th>
                    <th className="pb-3 pr-4 font-semibold">Date</th>
                    <th className="pb-3 pr-4 font-semibold">Amount</th>
                    <th className="pb-3 pr-4 font-semibold">Status</th>
                    <th className="pb-3 font-semibold">Reference</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((invoice) => {
                    const isSelected = selectedInvoices.has(invoice.id)

                    return (
                      <tr key={invoice.id} className="border-b border-border/70 last:border-0">
                        <td className="py-4 pr-4">
                          <button
                            type="button"
                            onClick={() => onToggleInvoice(invoice.id)}
                            className={`inline-flex h-5 w-5 items-center justify-center rounded border ${
                              isSelected ? 'border-primary bg-primary text-white' : 'border-border bg-surface text-transparent'
                            }`}
                          >
                            <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
                          </button>
                        </td>
                        <td className="py-4 pr-4">
                          <div className="flex items-center gap-3">
                            <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-muted text-subtle">
                              <ReceiptText className="h-4 w-4" strokeWidth={1.7} />
                            </div>
                            <div>
                              <p className="font-semibold text-heading">{invoice.name}</p>
                              <p className="text-[0.76rem] text-subtle">{invoice.address}</p>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 pr-4 text-body">{invoice.date}</td>
                        <td className="py-4 pr-4 font-semibold text-heading">${invoice.amount.toLocaleString()}</td>
                        <td className="py-4 pr-4">
                          <span className={`rounded-full border px-2.5 py-1 text-[0.72rem] font-semibold ${STATUS_STYLES[invoice.status]}`}>
                            {invoice.status}
                          </span>
                        </td>
                        <td className="py-4 text-primary">
                          <span className="inline-flex items-center gap-2 text-[0.82rem] font-semibold">
                            <ExternalLink className="h-3.5 w-3.5" strokeWidth={1.7} />
                            {invoice.tracking}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </SectionShell>
    </div>
  )
}
