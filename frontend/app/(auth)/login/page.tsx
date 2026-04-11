'use client'

import { useState } from 'react'
import { ArrowRight } from 'lucide-react'
import {
  AuthDivider,
  AuthProviderButton,
  AuthShell,
} from '@/components/auth/AuthShell'

const LOGIN_PILLARS = [
  {
    title: 'See what is changing',
    description: 'Track meaningful shifts earlier.',
  },
  {
    title: 'Know what matters',
    description: 'Cut through noise faster.',
  },
  {
    title: 'Decide faster with confidence',
    description: 'Move with clearer context.',
  },
  {
    title: 'Reduce guesswork',
    description: 'Make fewer blind calls.',
  },
] as const

export default function LoginPage() {
  const [remember, setRemember] = useState(false)

  return (
    <AuthShell
      badge="See what is changing"
      title="See what is changing."
      description="Return to a calmer market-intelligence workspace built for focus, clarity, and quicker decisions."
      pillars={LOGIN_PILLARS}
      panelLabel="Welcome back"
      panelTitle="Continue with confidence."
      panelDescription="Sign back in, review what changed, and keep moving."
      footerPrompt="New to Cogent?"
      footerDescription="Create your account and start tracking what matters."
      footerHref="/signup"
      footerAction="Create account"
    >
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3 sm:gap-3">
        <AuthProviderButton provider="google" href="/api/auth/login?connection=google-oauth2" />
        <AuthProviderButton provider="linkedin" href="/api/auth/login?connection=linkedin" />
        <AuthProviderButton provider="github" href="/api/auth/login?connection=github" />
      </div>

      <AuthDivider label="Or continue with email" />

      <form action="/api/auth/login" method="GET" className="space-y-3.5 sm:space-y-4">
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
            className="focus-ring h-12 w-full rounded-[18px] border border-border bg-surface px-4 text-[0.92rem] text-heading placeholder:text-subtle transition-all duration-200 hover:border-border-hover focus:border-primary/25"
          />
        </div>

        <div className="flex items-center justify-between gap-4">
          <label className="flex cursor-pointer items-center gap-2 text-[0.82rem] text-body">
            <input
              type="checkbox"
              checked={remember}
              onChange={(event) => setRemember(event.target.checked)}
              className="h-4 w-4 rounded border-border text-primary focus:ring-primary/25"
            />
            Keep me signed in
          </label>
          <a
            href="/api/auth/login?screen_hint=reset"
            className="text-[0.82rem] font-semibold text-primary transition-colors hover:text-primary-hover"
          >
            Reset password
          </a>
        </div>

        <button
          type="submit"
          className="button-press flex min-h-[52px] w-full items-center justify-center gap-2 rounded-[18px] bg-primary px-6 text-[0.9rem] font-semibold text-white shadow-[0_22px_46px_-24px_rgba(37,99,235,0.78)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-primary-hover"
        >
          Continue to secure sign in
          <ArrowRight size={16} />
        </button>
      </form>
    </AuthShell>
  )
}
