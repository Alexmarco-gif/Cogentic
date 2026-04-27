import { ArrowRight, Mail, User } from 'lucide-react'
import {
  AuthDivider,
  AuthProviderButton,
  AuthShell,
} from '@/components/auth/AuthShell'

const SIGNUP_PILLARS = [
  {
    title: 'See what is changing',
    description: 'Spot shifts earlier.',
  },
  {
    title: 'Know what matters',
    description: 'Focus on the signals that count.',
  },
  {
    title: 'Decide faster with confidence',
    description: 'Move from noise to action.',
  },
  {
    title: 'Reduce guesswork',
    description: 'Act with more clarity.',
  },
] as const

export default function SignupPage() {
  return (
    <AuthShell
      badge="Know what matters"
      title="Know what matters. Decide faster."
      description="Cogent gives financial teams a clearer view of change, so decisions happen faster and with less guesswork."
      pillars={SIGNUP_PILLARS}
      panelLabel="Start with clarity"
      panelTitle="Create your secure account."
      panelDescription="Set up access and start with a clearer, more focused operating view."
      footerPrompt="Already have access?"
      footerDescription="Return to your workspace and pick up where you left off."
      footerHref="/login"
      footerAction="Log in"
    >
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3 sm:gap-3">
        <AuthProviderButton provider="google" href="/api/auth/login?connection=google-oauth2&screen_hint=signup" />
        <AuthProviderButton provider="linkedin" href="/api/auth/login?connection=linkedin&screen_hint=signup" />
        <AuthProviderButton provider="github" href="/api/auth/login?connection=github&screen_hint=signup" />
      </div>

      <AuthDivider label="Or sign up with email" />

      <form action="/api/auth/login" method="GET" className="space-y-4 sm:space-y-4">
        <input type="hidden" name="screen_hint" value="signup" />

        <div className="space-y-2">
          <label htmlFor="name" className="text-[0.82rem] font-semibold text-heading">
            Full name
          </label>
          <div className="focus-within:ring-1 focus-within:ring-primary/15 flex h-12 w-full items-center gap-3 rounded-[18px] border border-border bg-surface px-4 transition-all duration-200 hover:border-border-hover focus-within:border-primary/25">
            <User className="h-4 w-4 text-subtle" strokeWidth={1.8} />
            <input
              id="name"
              type="text"
              name="name_hint"
              placeholder="Your full name"
              autoComplete="name"
              className="focus-ring h-full w-full bg-transparent text-[0.92rem] text-heading placeholder:text-subtle"
            />
          </div>
        </div>

        <div className="space-y-2">
          <label htmlFor="email" className="text-[0.82rem] font-semibold text-heading">
            Work email
          </label>
          <div className="focus-within:ring-1 focus-within:ring-primary/15 flex h-12 w-full items-center gap-3 rounded-[18px] border border-border bg-surface px-4 transition-all duration-200 hover:border-border-hover focus-within:border-primary/25">
            <Mail className="h-4 w-4 text-subtle" strokeWidth={1.8} />
            <input
              id="email"
              type="email"
              name="login_hint"
              placeholder="you@company.com"
              autoComplete="email"
              className="focus-ring h-full w-full bg-transparent text-[0.92rem] text-heading placeholder:text-subtle"
            />
          </div>
          <p className="text-[0.74rem] text-subtle">We’ll use this to create and route your workspace access.</p>
        </div>

        <label className="flex items-start gap-3 rounded-[20px] border border-border bg-surface px-4 py-4">
          <input
            type="checkbox"
            required
            className="mt-0.5 h-4 w-4 rounded border-border text-primary focus:ring-primary/25"
          />
          <span className="text-[0.8rem] leading-relaxed text-body">
            I agree to the{' '}
            <a href="/legal/terms" className="font-semibold text-primary transition-colors hover:text-primary-hover">
              Terms of Service
            </a>{' '}
            and{' '}
            <a href="/legal/privacy" className="font-semibold text-primary transition-colors hover:text-primary-hover">
              Privacy Notice
            </a>
            .
          </span>
        </label>

        <button
          type="submit"
          className="button-press flex min-h-[52px] w-full items-center justify-center gap-2 rounded-[18px] bg-primary px-6 text-[0.88rem] font-semibold text-white shadow-[0_22px_46px_-24px_rgba(37,99,235,0.78)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-primary-hover"
        >
          Create secure account
          <ArrowRight size={16} />
        </button>
      </form>
    </AuthShell>
  )
}
