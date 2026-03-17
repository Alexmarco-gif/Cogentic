import { Skeleton } from '@/components/ui/Skeleton'
import { StemIcon } from '@/components/ui/StemIcon'

// Root-level loading — shown while auth/global suspense resolves
export default function RootLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas">
      <div className="flex flex-col items-center gap-4">
        {/* Stem logo mark */}
        <div className="relative">
          <div className="w-10 h-10 rounded-xl bg-primary/20 animate-pulse" />
          <StemIcon
            size={20}
            className="absolute inset-0 m-auto w-5 h-5 opacity-40 text-primary"
            aria-hidden
          />
        </div>
        <Skeleton className="h-2.5 w-20 rounded-full" />
      </div>
    </div>
  )
}
