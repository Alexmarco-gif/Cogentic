import { Skeleton } from '@/components/ui/Skeleton'

/**
 * Home page skeleton — mirrors the real layout:
 * MorningBrief → StrategicStatus cards → heatmap + live feed + moat widget
 */
export default function HomeLoading() {
  return (
    <div className="px-4 sm:px-6 py-6 max-w-[1400px] mx-auto space-y-6">

      {/* ── MorningBrief ────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-2">
            <Skeleton className="h-5 w-52" />
            <Skeleton className="h-3 w-80" />
          </div>
          <div className="flex gap-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-9 w-20 rounded-xl" />
            ))}
          </div>
        </div>
      </div>

      {/* ── Strategic Status ────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <Skeleton className="h-3.5 w-36" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="rounded-2xl border border-border bg-surface p-4 shadow-card space-y-3">
              <Skeleton className="h-8 w-8 rounded-xl" />
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-5 w-10" />
              <Skeleton className="h-2 w-full rounded-full" />
            </div>
          ))}
        </div>
      </section>

      {/* ── Main grid ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Feed + Heatmap */}
        <div className="lg:col-span-2 space-y-4">
          {/* Heatmap */}
          <div className="rounded-2xl border border-border bg-surface p-4 shadow-card">
            <Skeleton className="h-3 w-28 mb-4" />
            <div className="grid grid-cols-7 gap-1.5">
              {Array.from({ length: 49 }).map((_, i) => (
                <Skeleton key={i} className="h-8 rounded-lg" />
              ))}
            </div>
          </div>

          {/* Live feed items */}
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="rounded-2xl border border-border bg-surface p-4 shadow-card flex gap-4">
                <Skeleton className="h-10 w-10 rounded-xl flex-shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="flex justify-between gap-2">
                    <Skeleton className="h-3 w-44" />
                    <Skeleton className="h-5 w-16 rounded-full flex-shrink-0" />
                  </div>
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-2/3" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sidebar widgets */}
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-2xl border border-border bg-surface p-4 shadow-card space-y-3">
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-7 w-16" />
              <Skeleton className="h-2 w-full rounded-full" />
            </div>
          ))}
        </div>

      </div>
    </div>
  )
}
