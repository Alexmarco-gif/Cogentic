'use client'

import { motion, type HTMLMotionProps } from 'framer-motion'

// ── Variants ──────────────────────────────────────────────────────────────────

const containerVariants = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.06,
      delayChildren:   0.02,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.2, ease: [0.16, 1, 0.3, 1] as const },
  },
}

// ── StaggerList ───────────────────────────────────────────────────────────────

type DivMotionProps = { children: React.ReactNode; className?: string } & Omit<HTMLMotionProps<'div'>, 'variants' | 'initial' | 'animate'>

/**
 * Animate children in sequence with a stagger delay.
 * Pair with <StaggerItem> for each child.
 */
export function StaggerList({ children, className, ...props }: DivMotionProps) {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  )
}

// ── StaggerItem ───────────────────────────────────────────────────────────────

/**
 * Direct child of <StaggerList>.
 * Inherits stagger timing from the container via framer-motion variant propagation.
 */
export function StaggerItem({ children, className, ...props }: DivMotionProps) {
  return (
    <motion.div variants={itemVariants} className={className} {...props}>
      {children}
    </motion.div>
  )
}
