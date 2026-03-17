'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Eye, EyeOff, ArrowRight } from 'lucide-react'
import { StemIcon } from '@/components/ui/StemIcon'

// ── SVG brand icons ───────────────────────────────────────────────────────────

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
  )
}

function LinkedInIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-[#0A66C2]" aria-hidden>
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  )
}

function GithubIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-[#24292F]" aria-hidden>
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  )
}

// ── Decorative right panel — Signup ──────────────────────────────────────────

function RightPanel() {
  return (
    <div className="hidden lg:block relative overflow-hidden">
      <img
        src="/1 (3).png"
        alt="Executive in a modern skyscraper using Cogent intelligence platform"
        className="absolute inset-0 h-full w-full object-cover object-center"
        loading="eager"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/25 to-black/15" />
      <div className="absolute inset-0 bg-indigo-950/20" />

      <div className="relative h-full flex flex-col justify-between p-8">

        {/* Top bar */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 rounded-full bg-white/10 backdrop-blur-sm border border-white/15 px-3 py-1.5">
            <span className="text-[11px] font-semibold text-white/90 tracking-wide">Market Intelligence</span>
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white shadow-xl">
            <StemIcon size={24} className="h-6 w-6 text-[#4F46E5]" aria-label="Cogent" />
          </div>
        </div>

        {/* Bottom content */}
        <div className="space-y-5">
          <div>
            <p className="text-2xl font-bold text-white leading-snug max-w-[300px]">
              Join the most strategic executive teams.
            </p>
            <p className="mt-2 text-sm text-white/70 leading-relaxed max-w-[280px]">
              Real-time signals, AI-crafted briefs, and sector intelligence —
              for decision making and market study.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {['Real-time signals', 'AI synthesis', 'Insightful Data', 'API access', 'Decision Making'].map(f => (
              <span
                key={f}
                className="rounded-full bg-white/10 backdrop-blur-sm border border-white/15 px-3 py-1 text-[11px] font-medium text-white/90"
              >
                {f}
              </span>
            ))}
          </div>

          <div className="flex items-center gap-3 pt-3 border-t border-white/10">
            <div className="flex -space-x-2">
              {[
                { initial: 'B', bg: '#6366f1' },
                { initial: 'C', bg: '#8b5cf6' },
                { initial: 'O', bg: '#ec4899' },
                { initial: 'N', bg: '#f59e0b' },
              ].map((a, i) => (
                <div
                  key={i}
                  className="h-7 w-7 rounded-full border-2 border-black/40 flex items-center justify-center text-white text-[10px] font-bold"
                  style={{ background: a.bg }}
                >
                  {a.initial}
                </div>
              ))}
            </div>
            <p className="text-[12px] text-white/70 leading-snug">
              Trusted by strategic teams across<br />emerging &amp; frontier markets
            </p>
          </div>
        </div>

      </div>
    </div>
  )
}

// ── Signup page ───────────────────────────────────────────────────────────────

export default function SignupPage() {
  const [showPassword, setShowPassword] = useState(false)

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-white">

      {/* ── Left: form panel ──────────────────────────────── */}
      <div className="flex flex-col items-center justify-center px-8 py-12 sm:px-16">
        <div className="w-full max-w-[400px] space-y-7">

          {/* Logo */}
          <div className="flex flex-col items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600 shadow-lg shadow-indigo-200">
              <StemIcon size={32} className="h-8 w-8 text-white" aria-label="Cogent" />
            </div>
            <div className="text-center">
              <h1 className="text-[22px] font-bold text-slate-800 tracking-tight">
                Create your{' '}
                <span className="text-indigo-600">Stem-Cogent</span>{' '}account
              </h1>
              <p className="mt-1 text-[13px] text-slate-500 leading-relaxed max-w-[300px]">
                Start with a free account — no credit card required.
              </p>
            </div>
          </div>

          {/* ── Social buttons ─────────────────────────────── */}
          <div className="grid grid-cols-3 gap-3">
            <a
              href="/api/auth/login?connection=google-oauth2&screen_hint=signup"
              className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-[13px] font-medium text-slate-700 shadow-sm transition-all hover:bg-slate-50 hover:border-slate-300 hover:shadow-md"
            >
              <GoogleIcon />
              <span>Google</span>
            </a>
            <a
              href="/api/auth/login?connection=linkedin&screen_hint=signup"
              className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-[13px] font-medium text-slate-700 shadow-sm transition-all hover:bg-slate-50 hover:border-slate-300 hover:shadow-md"
            >
              <LinkedInIcon />
              <span>LinkedIn</span>
            </a>
            <a
              href="/api/auth/login?connection=github&screen_hint=signup"
              className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-[13px] font-medium text-slate-700 shadow-sm transition-all hover:bg-slate-50 hover:border-slate-300 hover:shadow-md"
            >
              <GithubIcon />
              <span>GitHub</span>
            </a>
          </div>

          {/* ── Divider ─────────────────────────────────────── */}
          <div className="relative flex items-center gap-3">
            <div className="flex-1 border-t border-slate-200" />
            <span className="shrink-0 text-[11px] font-medium text-slate-400 uppercase tracking-wider">
              Or sign up with email
            </span>
            <div className="flex-1 border-t border-slate-200" />
          </div>

          {/* ── Form → Auth0 signup ─────────────────────────── */}
          <form action="/api/auth/login" method="GET" className="space-y-4">
            <input type="hidden" name="screen_hint" value="signup" />

            {/* Full name */}
            <div className="space-y-1.5">
              <label htmlFor="name" className="block text-[13px] font-medium text-slate-700">
                Full name
              </label>
              <input
                id="name"
                type="text"
                name="name_hint"
                placeholder="Enter your full name"
                autoComplete="name"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-[14px] text-slate-800 placeholder:text-slate-400 outline-none transition-all focus:border-indigo-400 focus:bg-white focus:ring-2 focus:ring-indigo-100"
              />
            </div>

            {/* Email */}
            <div className="space-y-1.5">
              <label htmlFor="email" className="block text-[13px] font-medium text-slate-700">
                Email
              </label>
              <input
                id="email"
                type="email"
                name="login_hint"
                placeholder="Enter your email"
                autoComplete="email"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-[14px] text-slate-800 placeholder:text-slate-400 outline-none transition-all focus:border-indigo-400 focus:bg-white focus:ring-2 focus:ring-indigo-100"
              />
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label htmlFor="password" className="block text-[13px] font-medium text-slate-700">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Create a strong password"
                  autoComplete="new-password"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 pr-11 text-[14px] text-slate-800 placeholder:text-slate-400 outline-none transition-all focus:border-indigo-400 focus:bg-white focus:ring-2 focus:ring-indigo-100"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              <p className="text-[11px] text-slate-400">Minimum 8 characters</p>
            </div>

            {/* Terms */}
            <label className="flex items-start gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                required
                className="mt-0.5 h-3.5 w-3.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-200"
              />
              <span className="text-[12px] text-slate-500 leading-relaxed">
                I agree to the{' '}
                <a href="/legal/terms" className="text-indigo-600 hover:underline">Terms of Service</a>
                {' '}and{' '}
                <a href="/legal/privacy" className="text-indigo-600 hover:underline">Privacy Policy</a>
              </span>
            </label>

            {/* Submit */}
            <button
              type="submit"
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-[14px] font-semibold text-white shadow-md shadow-indigo-200 transition-all hover:bg-indigo-700 hover:shadow-lg hover:shadow-indigo-200 active:scale-[0.98]"
            >
              Create account
              <ArrowRight size={15} />
            </button>
          </form>

          {/* ── Login link ──────────────────────────────────── */}
          <p className="text-center text-[13px] text-slate-500">
            Already have an account?{' '}
            <Link
              href="/login"
              className="font-semibold text-indigo-600 hover:text-indigo-700 hover:underline transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>

      {/* ── Right: brand panel ────────────────────────────── */}
      <RightPanel />
    </div>
  )
}
