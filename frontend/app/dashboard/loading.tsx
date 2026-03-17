import { Skeleton } from '@/components/ui/Skeleton'

// Dashboard layout-level loading — shown between route navigations
export default function DashboardLoading() {
  return (
    <div
      className={[
        // Match Shell's offset so skeleton aligns with real content
        'pl-0 md:pl-[var(--nav-rail-collapsed)]',
        'pt-[var(--omnibar-height)]',
        'pb-16 md:pb-0',
        'min-h-screen bg-canvas',
      ].join(' ')}
    >
      <div className="px-4 sm:px-6 py-6 max-w-[1400px] mx-auto space-y-6">

        {/* Header card */}
        <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
          <div className="flex items-center gap-4">
            <Skeleton className="h-9 w-9 rounded-xl shrink-0" />
            <div className="space-y-2 flex-1">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-72" />
            </div>
          </div>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="rounded-2xl border border-border bg-surface p-4 shadow-card space-y-3"
            >
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-8 w-14" />
              <Skeleton className="h-2 w-full rounded-full" />
            </div>
          ))}
        </div>

        {/* Main grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Feed */}
          <div className="lg:col-span-2 space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="rounded-2xl border border-border bg-surface p-4 shadow-card flex gap-4"
              >
                <Skeleton className="h-10 w-10 rounded-xl flex-shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <Skeleton className="h-3 w-40" />
                    <Skeleton className="h-5 w-16 rounded-full" />
                  </div>
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-3/4" />
                  <Skeleton className="h-2 w-24 mt-1" />
                </div>
              </div>
            ))}
          </div>

          {/* Sidebar */}
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="rounded-2xl border border-border bg-surface p-4 shadow-card space-y-2"
              >
                <Skeleton className="h-3 w-24" />
                <Skeleton className="h-6 w-16" />
              </div>
            ))}
          </div>

        </div>
      </div>
    </div>
  )
}
