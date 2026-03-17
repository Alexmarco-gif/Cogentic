'use client'

import { useEffect } from 'react'

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('Dashboard error:', error)
  }, [error])

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4">
      <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-8 text-center max-w-lg">
        <h2 className="text-lg font-semibold text-red-400 mb-2">
          Something went wrong
        </h2>
        <p className="text-sm text-zinc-400 mb-4">
          An error occurred while loading this page. You can try again or
          navigate to a different section.
        </p>
        {error.digest && (
          <p className="text-xs text-zinc-500 mb-4 font-mono">
            Error ID: {error.digest}
          </p>
        )}
        <button
          onClick={reset}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  )
}
