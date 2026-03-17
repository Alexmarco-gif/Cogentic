import * as React from 'react'
import { cn } from '@/lib/utils'

interface StemIconProps extends React.SVGProps<SVGSVGElement> {
  size?: number
}

/** Stem brand mark derived from stem-cogent.svg; uses currentColor for tinting. */
export function StemIcon({ size = 20, className, ...props }: StemIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 512 512"
      role="img"
      aria-hidden="true"
      className={cn('shrink-0', className)}
      {...props}
    >
      <rect x="144" y="108" width="112" height="112" rx="22" fill="currentColor" />
      <rect x="280" y="108" width="136" height="136" rx="24" fill="currentColor" />
      <rect x="96" y="244" width="160" height="160" rx="26" fill="currentColor" />
      <rect x="292" y="256" width="124" height="124" rx="23" fill="currentColor" />
    </svg>
  )
}
