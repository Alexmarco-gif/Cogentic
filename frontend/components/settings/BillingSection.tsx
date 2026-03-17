'use client'

import { useState } from 'react'
import { CreditCard, Mail, MoreVertical, Check, ExternalLink } from 'lucide-react'
import type { PaymentCard, BillingContact, Invoice, InvoiceStatus } from '@/lib/hooks/useSettings'

// ── Status badge ──────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<InvoiceStatus, string> = {
  Paid:      'text-emerald-600 bg-emerald-50 border-emerald-200',
  Pending:   'text-amber-600 bg-amber-50 border-amber-200',
  Cancelled: 'text-rose-600 bg-rose-50 border-rose-200',
  Refund:    'text-sky-600 bg-sky-50 border-sky-200',
}

// ── Masked card display ───────────────────────────────────────────────────────

function CardChip() {
  return (
    <div className="flex h-8 w-12 items-center justify-center rounded-md bg-gradient-to-br from-amber-300 to-amber-500 shadow-sm">
      <div className="h-4 w-6 rounded-sm border border-amber-600/30 bg-amber-200/50" />
    </div>
  )
}

// ── Input field ───────────────────────────────────────────────────────────────

function FormField({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
  prefix,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  type?: string
  prefix?: React.ReactNode
}) {
  return (
    <div>
      <label className="mb-1.5 block text-[11px] font-medium text-subtle">{label}</label>
      <div className="flex items-center gap-2 rounded-xl border border-border bg-surface px-3 py-2 focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20">
        {prefix}
        <input
          type={type}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className="flex-1 bg-transparent text-sm text-body placeholder:text-subtle focus:outline-none"
        />
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

interface BillingSectionProps {
  card: PaymentCard
  billingContact: BillingContact
  invoices: Invoice[]
  selectedInvoices: Set<string>
  onCardChange: (patch: Partial<PaymentCard>) => void
  onContactChange: (c: BillingContact) => void
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
  const [addCardOpen, setAddCardOpen] = useState(false)

  // Select all toggle
  const allSelected   = invoices.length > 0 && selectedInvoices.size === invoices.length
  const handleSelectAll = () => {
    if (allSelected) {
      invoices.forEach(inv => { if (selectedInvoices.has(inv.id)) onToggleInvoice(inv.id) })
    } else {
      invoices.forEach(inv => { if (!selectedInvoices.has(inv.id)) onToggleInvoice(inv.id) })
    }
  }

  return (
    <div className="flex flex-col gap-8">
      {/* ── Section header ───────────────────────────────────────────────── */}
      <div>
        <h2 className="text-xl font-medium text-heading">Payment Method</h2>
        <p className="mt-0.5 text-sm text-subtle">Update your billing details and address.</p>
      </div>

      {/* ── Card details ─────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="mb-5 flex items-start justify-between">
          <div>
            <h3 className="text-sm font-medium text-heading">Card Details</h3>
            <p className="mt-0.5 text-xs text-subtle">Update your billing details and address.</p>
          </div>
          <button
            onClick={() => setAddCardOpen(v => !v)}
            className="flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
          >
            + Add another card
          </button>
        </div>

        <div className="grid grid-cols-2 gap-5">
          {/* Left: name + card number */}
          <div className="flex flex-col gap-4">
            <FormField
              label="Name on your Card"
              value={card.nameOnCard}
              onChange={v => onCardChange({ nameOnCard: v })}
              placeholder="Full name"
            />
            <FormField
              label="Card Number"
              value={card.cardNumber}
              onChange={v => onCardChange({ cardNumber: v })}
              placeholder="•••• •••• •••• ••••"
              prefix={<CardChip />}
            />
          </div>

          {/* Right: expiry + CVV */}
          <div className="flex flex-col gap-4">
            <FormField
              label="Expiry"
              value={card.expiry}
              onChange={v => onCardChange({ expiry: v })}
              placeholder="MM / YYYY"
            />
            <FormField
              label="CVV"
              value={card.cvv}
              onChange={v => onCardChange({ cvv: v })}
              placeholder="•••"
              type="password"
            />
          </div>
        </div>

        {addCardOpen && (
          <div className="mt-5 rounded-xl border border-dashed border-primary/30 bg-primary/5 p-4 text-center text-xs text-subtle">
            Card form fields would appear here (Stripe / Paystack integration)
          </div>
        )}
      </div>

      {/* ── Contact email ────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="mb-4">
          <h3 className="text-sm font-medium text-heading">Contact email</h3>
          <p className="mt-0.5 text-xs text-subtle">Where should invoices be sent?</p>
        </div>

        <div className="flex flex-col gap-3">
          {/* Send to existing */}
          <label className="flex cursor-pointer items-start gap-3">
            <div className={`mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full border-2 transition-colors ${
              billingContact.mode === 'existing'
                ? 'border-primary bg-primary'
                : 'border-border bg-surface'
            }`}>
              {billingContact.mode === 'existing' && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
            </div>
            <div>
              <p className="text-sm text-body">Send to the existing email</p>
              <p className="text-xs text-subtle">{billingContact.email}</p>
            </div>
          </label>
          <button
            onClick={() => onContactChange({ ...billingContact, mode: 'existing' })}
            className="sr-only"
          />

          {/* Add another email */}
          <label className="flex cursor-pointer items-start gap-3">
            <div
              onClick={() => onContactChange({ ...billingContact, mode: 'other' })}
              className={`mt-0.5 flex h-4 w-4 flex-shrink-0 cursor-pointer items-center justify-center rounded-full border-2 transition-colors ${
                billingContact.mode === 'other'
                  ? 'border-primary bg-primary'
                  : 'border-border bg-surface'
              }`}
            >
              {billingContact.mode === 'other' && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
            </div>
            <p className="text-sm text-body">Add another email address</p>
          </label>

          {billingContact.mode === 'other' && (
            <div className="ml-7">
              <FormField
                label="Email address"
                value=""
                onChange={() => {}}
                placeholder="invoices@company.com"
                prefix={<Mail className="h-4 w-4 text-subtle" strokeWidth={1.5} />}
              />
            </div>
          )}
        </div>
      </div>

      {/* ── Billing history ──────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface shadow-card overflow-hidden">
        <div className="px-6 py-4 border-b border-border">
          <h3 className="text-sm font-medium text-heading">Billing History</h3>
          <p className="mt-0.5 text-xs text-subtle">See the transaction you made</p>
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="w-10 px-4 py-3 text-left">
                <div
                  onClick={handleSelectAll}
                  className={`flex h-4 w-4 cursor-pointer items-center justify-center rounded border transition-colors ${
                    allSelected ? 'border-primary bg-primary' : 'border-border bg-surface'
                  }`}
                >
                  {allSelected && <Check className="h-2.5 w-2.5 text-white" strokeWidth={3} />}
                </div>
              </th>
              {['Invoice', 'Date', 'Amount', 'Status', 'Tracking & Address'].map(col => (
                <th key={col} className="px-3 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-subtle">
                  {col}
                </th>
              ))}
              <th className="w-10" />
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv, i) => {
              const isSelected = selectedInvoices.has(inv.id)
              return (
                <tr
                  key={inv.id}
                  className={`border-b border-border last:border-0 transition-colors ${
                    isSelected ? 'bg-primary/5' : i % 2 === 0 ? 'bg-surface' : 'bg-muted/30'
                  }`}
                >
                  <td className="px-4 py-3.5">
                    <div
                      onClick={() => onToggleInvoice(inv.id)}
                      className={`flex h-4 w-4 cursor-pointer items-center justify-center rounded border transition-colors ${
                        isSelected ? 'border-primary bg-primary' : 'border-border bg-surface'
                      }`}
                    >
                      {isSelected && <Check className="h-2.5 w-2.5 text-white" strokeWidth={3} />}
                    </div>
                  </td>
                  <td className="px-3 py-3.5 text-sm text-body">{inv.name}</td>
                  <td className="px-3 py-3.5 text-sm text-subtle">{inv.date}</td>
                  <td className="px-3 py-3.5 text-sm font-medium text-heading">${inv.amount.toLocaleString()}</td>
                  <td className="px-3 py-3.5">
                    <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${STATUS_STYLES[inv.status]}`}>
                      {inv.status}
                    </span>
                  </td>
                  <td className="px-3 py-3.5">
                    <div>
                      <p className="flex items-center gap-1 text-xs font-medium text-primary hover:underline cursor-pointer">
                        <ExternalLink className="h-3 w-3" strokeWidth={1.5} />
                        {inv.tracking}
                      </p>
                      <p className="text-[11px] text-subtle">{inv.address}</p>
                    </div>
                  </td>
                  <td className="px-3 py-3.5">
                    <button className="text-subtle hover:text-body transition-colors">
                      <MoreVertical className="h-4 w-4" strokeWidth={1.5} />
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
