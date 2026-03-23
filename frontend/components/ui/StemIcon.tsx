import * as React from 'react'
import Image from 'next/image'
import { cn } from '@/lib/utils'

interface StemIconProps extends React.SVGProps<SVGSVGElement> {
  size?: number
  variant?: 'brand' | 'charcoal' | 'white'
}

const STEM_ICON_COLORS = {
  brand: '#2563EB',
  charcoal: '#111827',
  white: '#FFFFFF',
} as const

/** Product mark tuned to match the shipped brand icon variants. */
export function StemIcon({
  size = 20,
  className,
  variant = 'brand',
  'aria-label': ariaLabel,
  ...props
}: StemIconProps) {
  if (variant === 'brand') {
    return (
      <span
        className={cn('relative inline-flex shrink-0 overflow-hidden', className)}
        style={{ width: size, height: size }}
        role={ariaLabel ? 'img' : undefined}
        aria-label={ariaLabel}
        aria-hidden={ariaLabel ? undefined : true}
      >
        <Image
          src="/stem-icon-180x180-corrected.png"
          alt={ariaLabel ?? ''}
          fill
          sizes={`${size}px`}
          className="object-contain"
        />
      </span>
    )
  }

  const fill = STEM_ICON_COLORS[variant]

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 512 512"
      role={ariaLabel ? 'img' : undefined}
      aria-hidden={ariaLabel ? undefined : true}
      aria-label={ariaLabel}
      focusable="false"
      className={cn('shrink-0', className)}
      {...props}
    >
      <rect x="144" y="108" width="112" height="112" rx="22" fill={fill} />
      <rect x="280" y="108" width="136" height="136" rx="24" fill={fill} />
      <rect x="96" y="244" width="160" height="160" rx="26" fill={fill} />
      <rect x="292" y="256" width="124" height="124" rx="23" fill={fill} />
    </svg>
  )
}
