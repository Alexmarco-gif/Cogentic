'use client'

import Link from 'next/link'
import { ArrowRight, CheckCircle2, Sparkles } from 'lucide-react'
import { StemIcon } from '@/components/ui/StemIcon'

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

function ValuePanel() {
  return (
    <div className="relative hidden overflow-hidden rounded-[32px] border border-white/10 bg-[#111827] lg:block">
      <img
        src="/1 (3).png"
        alt="Team using Cogent in a modern executive environment"
        className="absolute inset-0 h-full w-full object-cover object-center"
      />
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(17,24,39,0.18),rgba(17,24,39,0.9))]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(37,99,235,0.3),transparent_32%)]" />

      <div className="relative flex h-full flex-col justify-between p-8 xl:p-10">
        <div className="flex items-center justify-between">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-white/85 backdrop-blur">
            <Sparkles size={13} />
            Strategic workflows
          </div>
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white shadow-xl">
            <StemIcon size={24} variant="brand" aria-label="Cogent" />
          </div>
        </div>

        <div className="space-y-8">
          <div className="max-w-xl">
            <p className="text-[2.6rem] font-bold leading-[1.02] tracking-[-0.05em] text-white">
              Build a workspace your team wants to return to.
            </p>
            <p className="mt-4 max-w-lg text-[0.96rem] text-white">
              Start with a clean operating flow: create a contract, connect sources, and let Cogent organize what matters most.
            </p>
          </div>

          <div className="rounded-[28px] border border-white/10 bg-black/25 p-5 backdrop-blur">
            <p className="text-[0.76rem] font-semibold uppercase tracking-[0.18em] text-white">What happens next</p>
            <div className="mt-4 space-y-3">
              {[
                'Create your first monitoring contract',
                'Invite your team when you are ready',
                'Review live signals and generated briefs',
              ].map((item, index) => (
                <div key={item} className="flex items-center gap-3 text-[0.9rem] text-white">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10 text-[0.72rem] font-semibold text-white">
                    {index + 1}
                  </div>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {[
              'Keyboard-first search and command palette',
              'Fewer modal interruptions, more inline momentum',
              'Clear activity logs and premium empty states',
              'Fast onboarding with smart defaults',
            ].map((item) => (
              <div key={item} className="flex items-start gap-3 rounded-[22px] border border-white/12 bg-white/10 p-4 text-[0.84rem] text-white backdrop-blur">
                <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-white" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function SignupPage() {
  return (
    <div className="min-h-screen bg-canvas px-4 py-4 sm:px-6 sm:py-6 lg:px-8">
      <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-[1540px] gap-4 lg:grid-cols-[minmax(0,0.98fr)_minmax(0,1.02fr)]">
        <div className="surface-elevated flex flex-col justify-center px-6 py-8 sm:px-10 lg:px-12 xl:px-16">
          <div className="mx-auto w-full max-w-[30rem]">
            <div className="mb-8">
              <div className="mb-6 inline-flex h-14 w-14 items-center justify-center rounded-[22px] border border-border bg-white shadow-glow">
                <StemIcon size={28} variant="brand" aria-label="Cogent" />
              </div>
              <p className="eyebrow">Start your workspace</p>
              <h1 className="mt-3 text-display text-heading">Create your account and launch with intent.</h1>
              <p className="mt-4 max-w-md text-body">
                Begin with a secure sign up, then move straight into your first contract, source setup, and live intelligence feed.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <a
                href="/api/auth/login?connection=google-oauth2&screen_hint=signup"
                className="button-press flex min-h-[52px] items-center justify-center gap-2 rounded-[20px] border border-border bg-surface px-4 py-3 text-[0.84rem] font-semibold text-body transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover hover:bg-surface-2"
              >
                <GoogleIcon />
                Google
              </a>
              <a
                href="/api/auth/login?connection=linkedin&screen_hint=signup"
                className="button-press flex min-h-[52px] items-center justify-center gap-2 rounded-[20px] border border-border bg-surface px-4 py-3 text-[0.84rem] font-semibold text-body transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover hover:bg-surface-2"
              >
                <LinkedInIcon />
                LinkedIn
              </a>
              <a
                href="/api/auth/login?connection=github&screen_hint=signup"
                className="button-press flex min-h-[52px] items-center justify-center gap-2 rounded-[20px] border border-border bg-surface px-4 py-3 text-[0.84rem] font-semibold text-body transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover hover:bg-surface-2"
              >
                <GithubIcon />
                GitHub
              </a>
            </div>

            <div className="my-7 flex items-center gap-3">
              <div className="h-px flex-1 bg-border" />
              <span className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-subtle">
                Or sign up with email
              </span>
              <div className="h-px flex-1 bg-border" />
            </div>

            <form action="/api/auth/login" method="GET" className="space-y-4">
              <input type="hidden" name="screen_hint" value="signup" />

              <div className="space-y-2">
                <label htmlFor="name" className="text-[0.82rem] font-semibold text-heading">
                  Full name
                </label>
                <input
                  id="name"
                  type="text"
                  name="name_hint"
                  placeholder="Your full name"
                  autoComplete="name"
                  className="focus-ring h-12 w-full rounded-[20px] border border-border bg-surface px-4 text-[0.92rem] text-heading placeholder:text-subtle transition-all duration-200 hover:border-border-hover focus:border-primary/25"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="email" className="text-[0.82rem] font-semibold text-heading">
                  Work email
                </label>
                <input
                  id="email"
                  type="email"
                  name="login_hint"
                  placeholder="you@company.com"
                  autoComplete="email"
                  className="focus-ring h-12 w-full rounded-[20px] border border-border bg-surface px-4 text-[0.92rem] text-heading placeholder:text-subtle transition-all duration-200 hover:border-border-hover focus:border-primary/25"
                />
              </div>

              <div className="rounded-[22px] border border-primary/12 bg-primary/5 px-4 py-3 text-[0.82rem] text-body">
                Password creation and verification happen on the secure Auth0 page right after you continue.
              </div>

              <label className="flex items-start gap-3 rounded-[22px] border border-border bg-surface px-4 py-4">
                <input
                  type="checkbox"
                  required
                  className="mt-0.5 h-4 w-4 rounded border-border text-primary focus:ring-primary/25"
                />
                <span className="text-[0.8rem] text-body">
                  I agree to the{' '}
                  <a href="/legal/terms" className="font-semibold text-primary transition-colors hover:text-primary-hover">Terms of Service</a>
                  {' '}and{' '}
                  <a href="/legal/privacy" className="font-semibold text-primary transition-colors hover:text-primary-hover">Privacy Notice</a>.
                </span>
              </label>

              <button
                type="submit"
                className="button-press flex h-12 w-full items-center justify-center gap-2 rounded-[20px] bg-primary px-6 text-[0.9rem] font-semibold text-white shadow-glow transition-all duration-200 hover:-translate-y-0.5 hover:bg-primary-hover"
              >
                Create secure account
                <ArrowRight size={16} />
              </button>
            </form>

            <div className="mt-8 flex flex-col items-start gap-4 rounded-[24px] border border-border bg-surface px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-[0.86rem] font-semibold text-heading">Already have access?</p>
                <p className="text-[0.78rem] text-subtle">Return to your workspace and continue from your latest signal review.</p>
              </div>
              <Link
                href="/login"
                className="button-press inline-flex items-center gap-2 rounded-full border border-border bg-surface-2 px-4 py-2 text-[0.8rem] font-semibold text-heading transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover"
              >
                Log in
                <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </div>

        <ValuePanel />
      </div>
    </div>
  )
}
