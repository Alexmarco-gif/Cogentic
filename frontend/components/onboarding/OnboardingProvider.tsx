'use client'

import type { ReactNode } from 'react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { usePathname } from 'next/navigation'
import { AnimatePresence, motion } from 'framer-motion'
import { Compass, Sparkles, X } from 'lucide-react'

type TourStep = {
  selector: string
  title: string
  body: string
  placement?: 'top' | 'bottom' | 'left' | 'right'
}

type TourMap = Record<string, TourStep[]>

type HighlightBox = {
  top: number
  left: number
  width: number
  height: number
}

const STORAGE_KEY = 'cogent:onboarding:v1'
const INSET = 10
const ONBOARDING_ENABLED = process.env.NEXT_PUBLIC_ONBOARDING_ENABLED !== 'false'

const TOURS: TourMap = {
  '/dashboard/home': [
    {
      selector: '[data-onboarding="home-primary-action"]',
      title: 'Start with one clear action',
      body: 'This hero makes the next best move obvious so the page never feels like a dead-end dashboard.',
      placement: 'bottom',
    },
    {
      selector: '[data-onboarding="home-steps"]',
      title: 'Keep setup progressive',
      body: 'These steps reduce overwhelm by showing the setup journey in a simple order instead of surfacing everything at once.',
      placement: 'bottom',
    },
    {
      selector: '[data-onboarding="home-actions"]',
      title: 'Jump straight into common tasks',
      body: 'Use these quick actions for high-intent flows such as creating contracts, opening investigations, or refreshing the workspace.',
      placement: 'top',
    },
  ],
  '/dashboard/studio': [
    {
      selector: '[data-onboarding="studio-tracker"]',
      title: 'Studio starts with a clear workflow',
      body: 'The tracker keeps contract creation, validation, and activation in a visible sequence instead of hiding progress from the user.',
      placement: 'bottom',
    },
    {
      selector: '[data-onboarding="studio-definition"]',
      title: 'Define the brief first',
      body: 'Start on the left by shaping the contract, selecting industry scope, and refining the parameters before launch.',
      placement: 'right',
    },
    {
      selector: '[data-onboarding="studio-intelligence"]',
      title: 'Review the intelligence output',
      body: 'The right pane keeps the live draft, evidence, and activation context visible so users do not lose momentum.',
      placement: 'left',
    },
  ],
  '/dashboard/signals': [
    {
      selector: '[data-onboarding="signals-header"]',
      title: 'Signals should answer what changed',
      body: 'The page header frames urgency and recency so the user immediately understands what deserves attention.',
      placement: 'bottom',
    },
    {
      selector: '[data-onboarding="signals-stats"]',
      title: 'Scan before diving in',
      body: 'The summary bar gives a fast read on total volume, critical items, unread changes, and saved work.',
      placement: 'bottom',
    },
    {
      selector: '[data-onboarding="signals-toolbar"]',
      title: 'Filter down to intent',
      body: 'Search and filters sit up front so the user can narrow the feed before opening individual items.',
      placement: 'bottom',
    },
    {
      selector: '[data-onboarding="signals-search"]',
      title: 'Search across entities and topics',
      body: 'This search is the fastest way to pivot from broad monitoring to a very specific signal or keyword.',
      placement: 'bottom',
    },
  ],
  '/dashboard/investigate': [
    {
      selector: '[data-onboarding="investigate-header"]',
      title: 'Investigate keeps the thread focused',
      body: 'The header frames the active thread, the current scope, and the purpose of the workspace before the user starts asking questions.',
      placement: 'bottom',
    },
    {
      selector: '[data-onboarding="investigate-scope"]',
      title: 'Set scope before querying',
      body: 'Choosing the industry upfront makes the investigation more relevant and prevents noisy evidence from crowding the thread.',
      placement: 'bottom',
    },
    {
      selector: '[data-onboarding="investigate-chat"]',
      title: 'Ask for what you need',
      body: 'The chat side is for framing the question, iterating on the prompt, and keeping the active conversation alive.',
      placement: 'right',
    },
    {
      selector: '[data-onboarding="investigate-evidence"]',
      title: 'Verify with structured evidence',
      body: 'Recommendations, citations, and process steps stay visible on the right so the user can validate the output quickly.',
      placement: 'left',
    },
  ],
  '/dashboard/marketplace': [
    {
      selector: '[data-onboarding="marketplace-header"]',
      title: 'Browse sources without losing context',
      body: 'Marketplace makes discovery clear up front by separating source browsing, access state, and subscription intent.',
      placement: 'bottom',
    },
    {
      selector: '[data-onboarding="marketplace-filters"]',
      title: 'Filter before subscribing',
      body: 'Users can narrow the catalog by search, signal type, and industry before making any commitment.',
      placement: 'bottom',
    },
    {
      selector: '[data-onboarding="marketplace-results"]',
      title: 'Cards should explain value quickly',
      body: 'The results area is where source quality, access state, and subscription actions are surfaced in one glance.',
      placement: 'top',
    },
  ],
  '/dashboard/library': [
    {
      selector: '[data-onboarding="library-header"]',
      title: 'Library should feel organized immediately',
      body: 'The header frames what is stored here and keeps the latest weekly report close to the top of the page.',
      placement: 'bottom',
    },
    {
      selector: '[data-onboarding="library-toolbar"]',
      title: 'Search and filters lead the workflow',
      body: 'Users should be able to narrow briefs before they scroll, which is why the toolbar sits directly under the page summary.',
      placement: 'bottom',
    },
    {
      selector: '[data-onboarding="library-results"]',
      title: 'Recent output stays easy to scan',
      body: 'The results body is structured for quick review, saved items, and opening the right brief without modal overload.',
      placement: 'top',
    },
  ],
  '/dashboard/settings': [
    {
      selector: '[data-onboarding="settings-header"]',
      title: 'Settings should stay calm and clear',
      body: 'This header keeps the purpose of the page obvious instead of dropping the user into a wall of account options.',
      placement: 'bottom',
    },
    {
      selector: '[data-onboarding="settings-tabs"]',
      title: 'Progressive disclosure matters here too',
      body: 'Tabs keep advanced controls grouped so users can focus on one decision area at a time.',
      placement: 'bottom',
    },
    {
      selector: '[data-onboarding="settings-content"]',
      title: 'Edit in context',
      body: 'The content area keeps changes inline so users stay oriented while updating profile, security, or privacy settings.',
      placement: 'top',
    },
  ],
}

function readCompletedRoutes(): Record<string, boolean> {
  if (typeof window === 'undefined') {
    return {}
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {}
  } catch {
    return {}
  }
}

function writeCompletedRoute(pathname: string) {
  if (typeof window === 'undefined') {
    return
  }

  const next = {
    ...readCompletedRoutes(),
    [pathname]: true,
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

function getHighlightBox(rect: DOMRect): HighlightBox {
  const width = Math.min(rect.width + INSET * 2, window.innerWidth - 24)

  return {
    top: Math.max(rect.top - INSET, 12),
    left: clamp(rect.left - INSET, 12, Math.max(12, window.innerWidth - width - 12)),
    width,
    height: rect.height + INSET * 2,
  }
}

export function OnboardingProvider({
  children,
}: {
  children: ReactNode
}) {
  const pathname = usePathname()
  const steps = useMemo(() => TOURS[pathname] ?? [], [pathname])
  const [isOpen, setIsOpen] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [highlight, setHighlight] = useState<HighlightBox | null>(null)

  const isSupportedPage = ONBOARDING_ENABLED && steps.length > 0
  const currentStep = steps[stepIndex]

  const findAvailableStep = useCallback(
    (startIndex: number) => {
      for (let index = startIndex; index < steps.length; index += 1) {
        const element = document.querySelector(steps[index].selector) as HTMLElement | null
        if (element) {
          return index
        }
      }

      return -1
    },
    [steps],
  )

  const openTour = useCallback(
    (preferredIndex = 0) => {
      if (!steps.length || typeof window === 'undefined') {
        return
      }

      const availableIndex = findAvailableStep(preferredIndex)
      if (availableIndex === -1) {
        return
      }

      setStepIndex(availableIndex)
      setIsOpen(true)
    },
    [findAvailableStep, steps.length],
  )

  const closeTour = useCallback(
    (markCompleted: boolean) => {
      setIsOpen(false)
      setHighlight(null)

      if (markCompleted && pathname) {
        writeCompletedRoute(pathname)
      }
    },
    [pathname],
  )

  const moveStep = useCallback(
    (direction: 1 | -1) => {
      if (!steps.length) {
        return
      }

      if (direction < 0) {
        setStepIndex((current) => Math.max(current - 1, 0))
        return
      }

      const nextIndex = findAvailableStep(stepIndex + 1)
      if (nextIndex === -1) {
        closeTour(true)
        return
      }

      setStepIndex(nextIndex)
    },
    [closeTour, findAvailableStep, stepIndex, steps.length],
  )

  useEffect(() => {
    if (!isSupportedPage || typeof window === 'undefined') {
      setIsOpen(false)
      setHighlight(null)
      return
    }

    const completedRoutes = readCompletedRoutes()
    if (completedRoutes[pathname]) {
      setIsOpen(false)
      setHighlight(null)
      return
    }

    const timeout = window.setTimeout(() => {
      openTour()
    }, 650)

    const retryTimeout = window.setTimeout(() => {
      const firstSelector = steps[0]?.selector
      if (!firstSelector || document.querySelector(firstSelector)) {
        return
      }

      openTour()
    }, 1600)

    return () => {
      window.clearTimeout(timeout)
      window.clearTimeout(retryTimeout)
    }
  }, [isSupportedPage, openTour, pathname])

  useEffect(() => {
    if (!isOpen || !currentStep) {
      return
    }

    const updateHighlight = () => {
      const element = document.querySelector(currentStep.selector) as HTMLElement | null
      if (!element) {
        const nextIndex = findAvailableStep(stepIndex + 1)
        if (nextIndex === -1) {
          closeTour(true)
        } else {
          setStepIndex(nextIndex)
        }
        return
      }

      element.scrollIntoView({
        block: 'center',
        inline: 'nearest',
        behavior: 'smooth',
      })

      const rect = element.getBoundingClientRect()
      setHighlight(getHighlightBox(rect))
    }

    const frame = window.requestAnimationFrame(updateHighlight)
    const handleScroll = () => {
      const element = document.querySelector(currentStep.selector) as HTMLElement | null
      if (!element) {
        return
      }

      const rect = element.getBoundingClientRect()
      setHighlight(getHighlightBox(rect))
    }

    window.addEventListener('resize', handleScroll)
    window.addEventListener('scroll', handleScroll, true)

    return () => {
      window.cancelAnimationFrame(frame)
      window.removeEventListener('resize', handleScroll)
      window.removeEventListener('scroll', handleScroll, true)
    }
  }, [closeTour, currentStep, findAvailableStep, isOpen, stepIndex])

  useEffect(() => {
    if (!isSupportedPage) {
      return
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        closeTour(true)
        return
      }

      if ((event.key === '?' || (event.key === '/' && event.shiftKey)) && !isOpen) {
        event.preventDefault()
        openTour()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [closeTour, isOpen, isSupportedPage, openTour])

  const tooltipStyle = useMemo(() => {
    if (typeof window === 'undefined' || !highlight) {
      return {
        bottom: 16,
        left: 16,
        right: 16,
      }
    }

    if (window.innerWidth < 768) {
      return {
        bottom: 16,
        left: 16,
        right: 16,
      }
    }

    const width = 340
    const maxLeft = window.innerWidth - width - 16
    const centeredLeft = clamp(highlight.left, 16, maxLeft)

    if (currentStep?.placement === 'left') {
      return {
        top: clamp(highlight.top, 16, window.innerHeight - 240),
        left: clamp(highlight.left - width - 20, 16, maxLeft),
        width,
      }
    }

    if (currentStep?.placement === 'right') {
      return {
        top: clamp(highlight.top, 16, window.innerHeight - 240),
        left: clamp(highlight.left + highlight.width + 20, 16, maxLeft),
        width,
      }
    }

    if (currentStep?.placement === 'top') {
      return {
        top: clamp(highlight.top - 220, 16, window.innerHeight - 240),
        left: centeredLeft,
        width,
      }
    }

    return {
      top: clamp(highlight.top + highlight.height + 18, 16, window.innerHeight - 240),
      left: centeredLeft,
      width,
    }
  }, [currentStep?.placement, highlight])

  if (!ONBOARDING_ENABLED) {
    return <>{children}</>
  }

  return (
    <>
      {children}

      {isSupportedPage && !isOpen && (
        <motion.button
          type="button"
          onClick={() => openTour()}
          className="button-press fixed bottom-20 right-5 z-[70] inline-flex items-center gap-2 rounded-full border border-border bg-surface/95 px-4 py-2 text-[0.76rem] font-semibold text-heading shadow-card backdrop-blur md:bottom-5"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
        >
          <Compass size={14} />
          Page guide
        </motion.button>
      )}

      <AnimatePresence>
        {isOpen && currentStep && highlight && (
          <>
            <motion.div
              key={`${pathname}-${stepIndex}-highlight`}
              className="pointer-events-none fixed z-[80] rounded-[28px] border border-primary/45 bg-primary/5 shadow-[0_0_0_9999px_rgba(7,10,18,0.45)]"
              initial={{ opacity: 0 }}
              animate={{
                opacity: 1,
                top: highlight.top,
                left: highlight.left,
                width: highlight.width,
                height: highlight.height,
              }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
            />

            <motion.aside
              key={`${pathname}-${stepIndex}-tooltip`}
              className="fixed z-[90] overflow-hidden rounded-[28px] border border-border bg-surface/98 p-5 shadow-elevated backdrop-blur"
              style={tooltipStyle}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-2">
                  <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-2.5 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-primary">
                    <Sparkles size={12} />
                    {stepIndex + 1} of {steps.length}
                  </div>
                  <div>
                    <h3 className="text-[1rem] font-semibold text-heading">{currentStep.title}</h3>
                    <p className="mt-2 text-[0.82rem] leading-6 text-body">{currentStep.body}</p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => closeTour(true)}
                  className="button-press inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface-2 text-subtle transition-colors hover:text-heading"
                  aria-label="Close onboarding guide"
                >
                  <X size={14} />
                </button>
              </div>

              <div className="mt-5 flex items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => closeTour(true)}
                  className="button-press rounded-full border border-border bg-surface-2 px-3.5 py-2 text-[0.75rem] font-semibold text-subtle transition-colors hover:text-heading"
                >
                  Skip guide
                </button>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => moveStep(-1)}
                    disabled={stepIndex === 0}
                    className="button-press rounded-full border border-border bg-surface px-3.5 py-2 text-[0.75rem] font-semibold text-heading transition disabled:cursor-not-allowed disabled:opacity-45"
                  >
                    Back
                  </button>
                  <button
                    type="button"
                    onClick={() => moveStep(1)}
                    className="button-press rounded-full bg-primary px-4 py-2 text-[0.75rem] font-semibold text-white transition hover:bg-primary-hover"
                  >
                    {stepIndex === steps.length - 1 ? 'Finish' : 'Next'}
                  </button>
                </div>
              </div>

              <p className="mt-4 text-[0.7rem] text-subtle">
                Press <span className="font-mono text-[0.68rem] text-heading">Shift + /</span> anytime to reopen this page guide.
              </p>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
