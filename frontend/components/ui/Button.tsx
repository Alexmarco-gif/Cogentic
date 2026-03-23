'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

type ButtonVariant = 'primary' | 'ghost' | 'outline' | 'destructive'
type ButtonSize = 'sm' | 'md' | 'lg' | 'icon'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  asChild?: boolean
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'border-primary bg-primary text-white shadow-glow hover:-translate-y-0.5 hover:bg-primary-hover hover:shadow-[0_24px_48px_-28px_rgba(22,104,227,0.95)]',
  ghost:
    'border-transparent bg-transparent text-body hover:-translate-y-0.5 hover:bg-surface-2 hover:text-heading',
  outline:
    'border-border bg-surface text-heading hover:-translate-y-0.5 hover:border-border-hover hover:bg-surface-2',
  destructive:
    'border-critical bg-critical text-white shadow-[0_18px_42px_-26px_rgba(203,79,65,0.8)] hover:-translate-y-0.5 hover:opacity-95',
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-9 gap-1.5 px-4 text-[0.78rem]',
  md: 'h-10 gap-2 px-4.5 text-[0.88rem]',
  lg: 'h-11 gap-2 px-5 text-[0.94rem]',
  icon: 'h-10 w-10 justify-center p-0 text-[0.88rem]',
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      disabled,
      className,
      children,
      ...props
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          'button-press focus-ring inline-flex items-center justify-center rounded-xl border font-semibold tracking-[-0.01em]',
          'transition-all duration-200 ease-spring disabled:pointer-events-none disabled:opacity-50',
          variantClasses[variant],
          sizeClasses[size],
          className,
        )}
        {...props}
      >
        {loading ? (
          <>
            <Spinner />
            <span className="opacity-80">{children}</span>
          </>
        ) : (
          children
        )}
      </button>
    )
  },
)

Button.displayName = 'Button'

function Spinner() {
  return (
    <svg
      className="h-4 w-4 shrink-0 animate-spin"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4Z"
      />
    </svg>
  )
}
