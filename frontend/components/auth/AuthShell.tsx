'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, ArrowUpRight, LockKeyhole, ShieldCheck, Sparkles, Waves } from 'lucide-react'
import { StemIcon } from '@/components/ui/StemIcon'
import { cn } from '@/lib/utils'

type Pillar = {
  title: string
  description: string
}

type Provider = 'google' | 'linkedin' | 'github'

interface ProviderButtonProps {
  provider: Provider
  href: string
}

interface AuthShellProps {
  badge: string
  title: string
  description: string
  pillars: readonly Pillar[]
  panelLabel: string
  panelTitle: string
  panelDescription: string
  footerPrompt: string
  footerDescription: string
  footerHref: string
  footerAction: string
  children: React.ReactNode
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09Z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23Z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84Z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53Z" fill="#EA4335" />
    </svg>
  )
}

function LinkedInIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-[#0A66C2]" aria-hidden>
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286ZM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065Zm1.782 13.019H3.555V9h3.564v11.452ZM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003Z" />
    </svg>
  )
}

function GithubIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-[#24292F]" aria-hidden>
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0 0 22 12.017C22 6.484 17.522 2 12 2Z" />
    </svg>
  )
}

function ProviderIcon({ provider }: { provider: Provider }) {
  if (provider === 'google') return <GoogleIcon />
  if (provider === 'linkedin') return <LinkedInIcon />
  return <GithubIcon />
}

function ProviderLabel({ provider }: { provider: Provider }) {
  if (provider === 'google') return <>Google</>
  if (provider === 'linkedin') return <>LinkedIn</>
  return <>GitHub</>
}

export function AuthProviderButton({ provider, href }: ProviderButtonProps) {
  return (
    <a
      href={href}
      className="button-press flex min-h-[52px] items-center justify-center gap-2 rounded-[18px] border border-border bg-surface px-4 py-3 text-[0.84rem] font-semibold text-body transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover hover:bg-surface-2 hover:shadow-[0_16px_36px_-28px_rgba(15,23,42,0.45)]"
    >
      <ProviderIcon provider={provider} />
      <ProviderLabel provider={provider} />
    </a>
  )
}

export function AuthDivider({ label }: { label: string }) {
  return (
    <div className="my-7 flex items-center gap-3">
      <div className="h-px flex-1 bg-border" />
      <span className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-subtle">{label}</span>
      <div className="h-px flex-1 bg-border" />
    </div>
  )
}

export function AuthNotice({
  icon,
  children,
  tone = 'primary',
}: {
  icon?: React.ReactNode
  children: React.ReactNode
  tone?: 'primary' | 'neutral'
}) {
  return (
    <div
      className={cn(
        'rounded-[20px] border px-4 py-3 text-[0.82rem] leading-relaxed',
        tone === 'primary'
          ? 'border-primary/12 bg-primary/5 text-body'
          : 'border-border bg-surface text-body',
      )}
    >
      <div className="flex items-start gap-2.5">
        {icon ? <span className="mt-0.5 shrink-0 text-primary">{icon}</span> : null}
        <div>{children}</div>
      </div>
    </div>
  )
}

function PillarCard({ title, description }: Pillar) {
  return (
    <div className="rounded-[20px] border border-border bg-white/80 px-3 py-3 shadow-[0_18px_44px_-36px_rgba(15,23,42,0.55)] backdrop-blur">
      <p className="text-[0.82rem] font-semibold text-heading">{title}</p>
      <p className="mt-1 text-[0.76rem] text-subtle">{description}</p>
    </div>
  )
}

function SignalTicker({ items }: { items: readonly Pillar[] }) {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (items.length <= 1) return
    const timer = window.setInterval(() => {
      setIndex((value) => (value + 1) % items.length)
    }, 2600)

    return () => window.clearInterval(timer)
  }, [items])

  const item = items[index]

  return (
    <div className="rounded-[24px] border border-primary/12 bg-primary/5 px-4 py-3">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Waves size={16} strokeWidth={1.8} />
        </div>
        <div className="min-w-0">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-subtle">Live signal</p>
          <p key={item.title} className="animate-fade-up mt-1 text-[0.92rem] font-semibold text-heading">
            {item.title}
          </p>
        </div>
      </div>
    </div>
  )
}

function InsightBoard({ items }: { items: readonly Pillar[] }) {
  const dashboardCards = useMemo(
    () => items.slice(0, 3).map((item, index) => ({
      id: item.title,
      label: `0${index + 1}`,
      title: item.title,
      detail: index === 0 ? 'Signals monitored' : index === 1 ? 'Priority surfaced' : 'Decision support ready',
    })),
    [items],
  )

  return (
    <div className="grid gap-3">
      <div className="rounded-[28px] border border-border bg-[#111827] p-5 text-white shadow-[0_38px_90px_-52px_rgba(15,23,42,0.92)]">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-white/60">Market view</p>
            <p className="mt-2 text-[1.05rem] font-semibold text-white">A calmer operating surface for change, signals, and next moves.</p>
          </div>
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10">
            <StemIcon size={20} variant="white" aria-label="Cogent" />
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-2.5 sm:grid-cols-3">
          {dashboardCards.map((card) => (
            <div key={card.id} className="animate-float-gentle rounded-[20px] border border-white/10 bg-white/5 px-3 py-3" style={{ animationDelay: `${dashboardCards.indexOf(card) * 120}ms` }}>
              <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-white/50">{card.label}</p>
              <p className="mt-2 text-[0.82rem] font-semibold text-white">{card.title}</p>
              <p className="mt-1 text-[0.72rem] text-white/60">{card.detail}</p>
            </div>
          ))}
        </div>

        <div className="mt-5 flex items-center gap-2 text-[0.78rem] text-white/72">
          <span className="live-dot" />
          Quietly updated as new signals are reviewed.
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <PillarCard title="Changes tracked" description="Earlier visibility" />
        <PillarCard title="Noise reduced" description="Clearer focus" />
        <PillarCard title="Decisions supported" description="Faster action" />
      </div>
    </div>
  )
}

export function AuthShell({
  badge,
  title,
  description,
  pillars,
  panelLabel,
  panelTitle,
  panelDescription,
  footerPrompt,
  footerDescription,
  footerHref,
  footerAction,
  children,
}: AuthShellProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-canvas">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(148,163,184,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.08)_1px,transparent_1px)] bg-[size:34px_34px] [mask-image:radial-gradient(circle_at_center,black,transparent_78%)]" />
      <div className="pointer-events-none absolute left-[-8rem] top-[-7rem] h-[22rem] w-[22rem] rounded-full bg-primary/10 blur-3xl" />
      <div className="pointer-events-none absolute bottom-[-10rem] right-[-6rem] h-[24rem] w-[24rem] rounded-full bg-slate-900/8 blur-3xl" />

      <div className="relative mx-auto flex min-h-screen max-w-[1460px] items-center px-4 py-4 sm:px-6 sm:py-5 lg:px-8">
        <div className="grid w-full gap-4 lg:grid-cols-[minmax(0,1.08fr)_minmax(0,30rem)] xl:gap-5">
          <section className="animate-fade-up order-2 relative overflow-hidden rounded-[34px] border border-border bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.98))] p-5 shadow-[0_38px_120px_-64px_rgba(15,23,42,0.55)] sm:p-7 lg:order-1 lg:min-h-[calc(100vh-4rem)] lg:p-10 xl:p-12">
            <div className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.16),transparent_55%)]" />
            <div className="relative flex h-full flex-col justify-between gap-7 lg:gap-10">
              <div className="flex flex-col gap-6 lg:gap-8">
                <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex items-center gap-4">
                    <div className="flex h-14 w-14 items-center justify-center rounded-[22px] border border-border bg-white shadow-[0_18px_42px_-28px_rgba(37,99,235,0.48)]">
                      <StemIcon size={28} variant="brand" aria-label="Cogent" />
                    </div>
                    <div>
                      <p className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-subtle">Cogent by Stem</p>
                      <p className="mt-1 text-[0.9rem] font-semibold text-heading">Strategic market intelligence</p>
                    </div>
                  </div>

                  <div className="inline-flex items-center gap-2 self-start rounded-full border border-primary/15 bg-primary/6 px-3.5 py-2 text-[0.76rem] font-semibold text-primary">
                    <Sparkles size={14} strokeWidth={1.7} />
                    {badge}
                  </div>
                </div>

                <div className="max-w-2xl">
                  <h1 className="max-w-[14ch] text-display text-heading sm:max-w-[12ch]">{title}</h1>
                  <p className="mt-3 max-w-[54ch] text-body">{description}</p>
                </div>

                <SignalTicker items={pillars} />
                <InsightBoard items={pillars} />
              </div>

              <div className="animate-fade-up grid gap-3 rounded-[28px] border border-border bg-white/75 p-4 backdrop-blur sm:grid-cols-[1.15fr_0.85fr] sm:p-5" style={{ animationDelay: '120ms' }}>
                <div>
                  <div className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5 text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-subtle">
                    <ShieldCheck size={14} strokeWidth={1.7} />
                    Trusted flow
                  </div>
                  <p className="mt-4 text-[0.96rem] font-semibold text-heading">
                    Built to help financial teams see change early and act with less guesswork.
                  </p>
                </div>

                <div className="grid gap-2">
                  {['See change', 'Know what matters', 'Move faster'].map((item) => (
                    <div key={item} className="flex items-center justify-between gap-2 rounded-[18px] border border-border bg-surface px-3 py-2 text-[0.8rem] font-medium text-body">
                      <span>{item}</span>
                      <ArrowUpRight className="h-3.5 w-3.5 text-primary" strokeWidth={1.8} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="animate-fade-up order-1 surface-elevated flex flex-col justify-center rounded-[34px] px-4 py-5 sm:px-6 sm:py-6 lg:order-2 lg:min-h-[calc(100vh-4rem)] lg:px-8 lg:py-8" style={{ animationDelay: '80ms' }}>
            <div className="mx-auto flex w-full max-w-[26rem] flex-col gap-7">
              <div className="flex items-center justify-between gap-3">
                <Link href="/" className="inline-flex items-center gap-2 text-[0.82rem] font-semibold text-body transition-colors hover:text-heading">
                  <StemIcon size={18} variant="brand" aria-label="Cogent" />
                  Cogent
                </Link>
                <div className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5 text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-subtle">
                  <LockKeyhole size={13} strokeWidth={1.7} />
                  Secure access
                </div>
              </div>

              <div>
                <p className="eyebrow">{panelLabel}</p>
                <h2 className="mt-3 text-display text-heading">{panelTitle}</h2>
                <p className="mt-4 text-body">{panelDescription}</p>
              </div>

              {children}

              <div className="rounded-[24px] border border-border bg-surface px-4 py-4">
                <p className="text-[0.86rem] font-semibold text-heading">{footerPrompt}</p>
                <p className="mt-1 text-[0.8rem] leading-relaxed text-subtle">{footerDescription}</p>
                <Link
                  href={footerHref}
                  className="button-press mt-4 inline-flex items-center gap-2 rounded-full border border-border bg-surface-2 px-4 py-2 text-[0.8rem] font-semibold text-heading transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover"
                >
                  {footerAction}
                  <ArrowRight size={14} />
                </Link>
              </div>

              <div className="flex flex-col gap-3 border-t border-border pt-1 text-[0.74rem] text-subtle sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
                <div className="inline-flex items-center gap-2">
                  <ShieldCheck size={13} strokeWidth={1.7} className="text-primary" />
                  Secure access by Stem Systems Ltd.
                </div>
                <div className="flex items-center gap-3">
                  <Link href="/legal/terms" className="transition-colors hover:text-body">
                    Terms
                  </Link>
                  <Link href="/legal/privacy" className="transition-colors hover:text-body">
                    Privacy
                  </Link>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
