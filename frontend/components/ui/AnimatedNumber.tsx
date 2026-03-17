'use client'

import { useEffect, useRef, useState } from 'react'
import { useInView } from 'framer-motion'

interface AnimatedNumberProps {
  /** Target number to count up to */
  value: number
  /** Animation duration in ms (default 800) */
  duration?: number
  /** Optional string prepended to the number (e.g. "$") */
  prefix?: string
  /** Optional string appended to the number (e.g. "%") */
  suffix?: string
  /** Decimal places to show (default 0) */
  decimals?: number
  className?: string
}

/**
 * Counts up from 0 → value when the element scrolls into view.
 * Uses requestAnimationFrame + easeOutQuart for a smooth feel.
 * Respects prefers-reduced-motion by skipping animation if set.
 */
export function AnimatedNumber({
  value,
  duration = 800,
  prefix = '',
  suffix = '',
  decimals = 0,
  className,
}: AnimatedNumberProps) {
  const ref      = useRef<HTMLSpanElement>(null)
  const inView   = useInView(ref, { once: true, margin: '-50px' })
  const startRef = useRef<number | null>(null)
  const frameRef = useRef<number>()
  const [display, setDisplay] = useState(0)

  useEffect(() => {
    if (!inView) return

    // Skip animation when user prefers reduced motion
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) {
      setDisplay(value)
      return
    }

    startRef.current = null

    function step(timestamp: number) {
      if (!startRef.current) startRef.current = timestamp
      const progress = Math.min((timestamp - startRef.current) / duration, 1)
      const eased    = 1 - Math.pow(1 - progress, 4) // easeOutQuart
      setDisplay(eased * value)
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(step)
      }
    }

    frameRef.current = requestAnimationFrame(step)
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current)
    }
  }, [inView, value, duration])

  return (
    <span ref={ref} className={className}>
      {prefix}{display.toFixed(decimals)}{suffix}
    </span>
  )
}
