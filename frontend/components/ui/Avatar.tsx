import * as React from 'react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

type AvatarSize = 'xs' | 'sm' | 'md' | 'lg'

interface AvatarProps {
  src?: string | null
  alt?: string
  fallback?: string  // 1-2 chars, e.g. "DC" for Dangote Cement
  size?: AvatarSize
  className?: string
}

// ─── Size map ─────────────────────────────────────────────────────────────────

const sizeClasses: Record<AvatarSize, { wrapper: string; text: string }> = {
  xs: { wrapper: 'w-6 h-6',  text: 'text-[10px]' },
  sm: { wrapper: 'w-8 h-8',  text: 'text-xs' },
  md: { wrapper: 'w-10 h-10', text: 'text-sm' },
  lg: { wrapper: 'w-12 h-12', text: 'text-base' },
}

// ─── Component ────────────────────────────────────────────────────────────────

export function Avatar({ src, alt, fallback, size = 'sm', className }: AvatarProps) {
  const [imgError, setImgError] = React.useState(false)
  const { wrapper, text } = sizeClasses[size]

  const initials = fallback
    ? fallback.slice(0, 2).toUpperCase()
    : alt
      ? alt.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
      : '?'

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded-full',
        'bg-primary-light text-primary font-medium shrink-0 overflow-hidden',
        wrapper,
        text,
        className,
      )}
      aria-label={alt}
    >
      {src && !imgError ? (
        <img
          src={src}
          alt={alt ?? ''}
          className="w-full h-full object-cover rounded-full"
          onError={() => setImgError(true)}
        />
      ) : (
        initials
      )}
    </span>
  )
}
