'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

interface StreamingTextProps {
  /** Full text to stream in */
  text: string
  /** Characters per interval tick — default 3 */
  speed?: number
  /** Interval ms — default 30 */
  interval?: number
  /** Called when streaming completes */
  onComplete?: () => void
  className?: string
}

// ─── Component ────────────────────────────────────────────────────────────────

export function StreamingText({
  text,
  speed = 3,
  interval = 30,
  onComplete,
  className,
}: StreamingTextProps) {
  const [displayed, setDisplayed] = React.useState('')
  const indexRef = React.useRef(0)

  React.useEffect(() => {
    // Reset when text changes
    setDisplayed('')
    indexRef.current = 0

    const timer = setInterval(() => {
      indexRef.current = Math.min(indexRef.current + speed, text.length)
      setDisplayed(text.slice(0, indexRef.current))

      if (indexRef.current >= text.length) {
        clearInterval(timer)
        onComplete?.()
      }
    }, interval)

    return () => clearInterval(timer)
  }, [text, speed, interval, onComplete])

  return (
    <span className={cn('whitespace-pre-wrap', className)}>
      {displayed}
      {/* Blinking cursor while streaming */}
      {displayed.length < text.length && (
        <span
          aria-hidden="true"
          className="inline-block w-0.5 h-[1em] bg-current align-text-bottom ml-0.5 animate-pulse"
        />
      )}
    </span>
  )
}
