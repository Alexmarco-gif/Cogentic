'use client'

import { useEffect, useRef, useState } from 'react'

/* ─────────────────────────────────────────────────────────────────────────────
   Slide data
───────────────────────────────────────────────────────────────────────────── */

const SLIDES = [
  {
    src: '/1 (1).png',
    alt: 'Executive using Cogent intelligence platform',
    objectPosition: 'top',
    gradient: 'linear-gradient(to top, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.18) 55%, rgba(0,0,0,0.28) 100%)',
  },
  {
    src: '/1 (2).png',
    alt: 'Strategic business professional with dashboard',
    objectPosition: 'center',
    gradient: 'linear-gradient(to top, rgba(0,0,0,0.82) 0%, rgba(0,0,0,0.28) 55%, rgba(0,0,0,0.18) 100%)',
  },
  {
    src: '/1 (3).png',
    alt: 'Executive in modern skyscraper office',
    objectPosition: 'center',
    gradient: 'linear-gradient(to top, rgba(0,0,0,0.92) 0%, rgba(0,0,0,0.22) 55%, rgba(0,0,0,0.14) 100%)',
  },
]

const DELAY = 5000

/* ─────────────────────────────────────────────────────────────────────────────
   TypewriterText
   Uses setTimeout chaining — simplest approach, no closure capture issues
───────────────────────────────────────────────────────────────────────────── */

export function TypewriterText({
  text,
  speed = 42,
  className = '',
}: {
  text: string
  speed?: number
  className?: string
}) {
  const [count, setCount] = useState(0)

  // Reset when text changes
  useEffect(() => {
    setCount(0)
  }, [text])

  // Each render with count < length schedules the next character
  useEffect(() => {
    if (count >= text.length) return
    const id = setTimeout(() => setCount(c => c + 1), speed)
    return () => clearTimeout(id)
  }, [count, text, speed])

  const done = count >= text.length

  return (
    <span className={className}>
      {text.slice(0, count)}
      <span
        aria-hidden
        style={{
          display: 'inline-block',
          width: '2px',
          height: '1em',
          background: 'currentColor',
          verticalAlign: 'middle',
          marginLeft: '2px',
          marginBottom: '-1px',
          animation: done ? 'auth-cursor-blink 1s step-end infinite' : 'none',
          opacity: done ? undefined : 1,
        }}
      />
    </span>
  )
}

/* ─────────────────────────────────────────────────────────────────────────────
   AuthSlideshow
   IMPORTANT: parent grid container must use h-screen (real height),
   not just min-h-screen, so this div gets a real pixel height to fill.
───────────────────────────────────────────────────────────────────────────── */

interface AuthSlideshowProps {
  children?: React.ReactNode
}

export function AuthSlideshow({ children }: AuthSlideshowProps) {
  const [idx, setIdx]         = useState(0)
  const [progKey, setProgKey] = useState(0)
  const timerRef              = useRef<ReturnType<typeof setInterval> | null>(null)

  function startAutoplay() {
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      setIdx(prev => (prev + 1) % SLIDES.length)
      setProgKey(k => k + 1)
    }, DELAY)
  }

  useEffect(() => {
    startAutoplay()
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function goTo(i: number) {
    if (i === idx) return
    setIdx(i)
    setProgKey(k => k + 1)
    startAutoplay()
  }

  return (
    <div
      className="hidden lg:block"
      style={{
        position: 'relative',
        height: '100%',       // fills grid cell (grid must have real height)
        overflow: 'hidden',
        backgroundColor: '#0f172a',
      }}
    >
      {/* ── Slide layers ────────────────────────────────────── */}
      {SLIDES.map((slide, i) => (
        <div
          key={slide.src}
          style={{
            position: 'absolute',
            inset: 0,
            opacity: i === idx ? 1 : 0,
            transition: 'opacity 1.1s ease-in-out',
          }}
        >
          <img
            src={slide.src}
            alt={slide.alt}
            style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              objectPosition: slide.objectPosition,
              display: 'block',
            }}
            loading={i === 0 ? 'eager' : 'lazy'}
          />
          {/* vignette overlay */}
          <div style={{ position: 'absolute', inset: 0, background: slide.gradient }} />
        </div>
      ))}

      {/* ── Content layer ───────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          padding: '2rem',
          zIndex: 10,
        }}
      >
        {children}
      </div>

      {/* ── Progress-dot indicators ─────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          bottom: '1.75rem',
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          zIndex: 20,
        }}
      >
        {SLIDES.map((_, i) => (
          <button
            key={i}
            onClick={() => goTo(i)}
            aria-label={`Go to slide ${i + 1}`}
            style={{
              border: 'none',
              cursor: 'pointer',
              padding: 0,
              borderRadius: '9999px',
              overflow: 'hidden',
              height: '5px',
              width: i === idx ? '28px' : '5px',
              background: i === idx ? '#ffffff' : 'rgba(255,255,255,0.35)',
              transition: 'width 0.35s ease, background 0.35s ease',
              position: 'relative',
              flexShrink: 0,
            }}
          >
            {i === idx && (
              <span
                key={progKey}
                style={{
                  position: 'absolute',
                  inset: 0,
                  width: '0%',
                  background: 'rgba(255,255,255,0.55)',
                  animation: `auth-progress ${DELAY}ms linear forwards`,
                }}
              />
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
