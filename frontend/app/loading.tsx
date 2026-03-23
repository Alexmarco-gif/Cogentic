import { Skeleton } from '@/components/ui/Skeleton'
import { StemIcon } from '@/components/ui/StemIcon'

// Root-level loading — shown while auth/global suspense resolves
export default function RootLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas">
      <div className="flex flex-col items-center gap-5">
        <div className="relative flex h-28 w-28 items-center justify-center">
          <div className="absolute inset-0 rounded-[32px] bg-primary/12 blur-2xl animate-pulse" />
          <div className="absolute inset-[10px] rounded-[28px] border border-primary/10 bg-white/75 shadow-card backdrop-blur dark:bg-surface/90" />
          <div className="relative flex h-[4.5rem] w-[4.5rem] items-center justify-center rounded-[24px] border border-primary/12 bg-white shadow-[0_24px_54px_-28px_rgba(37,99,235,0.48)] dark:bg-surface">
            <StemIcon
              size={38}
              variant="brand"
              className="animate-float"
              aria-label="Cogent"
            />
          </div>
        </div>

        <div className="space-y-3 text-center">
          <p className="text-[0.86rem] font-semibold text-heading">Preparing your workspace</p>
          <div className="flex items-center justify-center gap-2">
            <span className="h-2 w-2 rounded-full bg-primary animate-bounce" />
            <span className="h-2 w-2 rounded-full bg-heading animate-bounce [animation-delay:140ms]" />
            <span className="h-2 w-2 rounded-full bg-primary/45 animate-bounce [animation-delay:280ms]" />
          </div>
        </div>

        <Skeleton className="h-2.5 w-24 rounded-full" />
      </div>
    </div>
  )
}
