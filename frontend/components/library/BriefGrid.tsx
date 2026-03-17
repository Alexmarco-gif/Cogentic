'use client'

import { BriefCard } from './BriefCard'
import type { LibraryBrief } from '@/lib/hooks/useLibrary'

interface BriefGridProps {
  briefs: LibraryBrief[]
  onOpen: (brief: LibraryBrief) => void
  onToggleSave: (id: string) => void
}

/**
 * BriefGrid renders briefs in a responsive masonry-style column layout.
 * Uses CSS columns so cards of varying heights fill naturally without a
 * JS masonry dependency. Cards animate in with a staggered fade-up.
 */
export function BriefGrid({ briefs, onOpen, onToggleSave }: BriefGridProps) {
  if (briefs.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 text-center">
        <p className="text-sm font-medium text-heading">No briefs found</p>
        <p className="text-xs text-subtle">Try adjusting your search or filters</p>
      </div>
    )
  }

  return (
    <div className="grid w-full grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
      {briefs.map((brief, i) => (
        <div
          key={brief.id}
          className="min-w-0"
          style={{
            animationName: 'fade-up',
            animationDuration: '320ms',
            animationTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
            animationFillMode: 'both',
            animationDelay: `${Math.min(i * 40, 320)}ms`,
          }}
        >
          <BriefCard
            brief={brief}
            onOpen={onOpen}
            onToggleSave={onToggleSave}
          />
        </div>
      ))}
    </div>
  )
}
