/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // All colors reference CSS variables — dark mode works automatically
        canvas:     'var(--color-canvas)',
        surface:    'var(--color-surface)',
        'surface-2': 'var(--color-surface-2)',
        'surface-3': 'var(--color-surface-3)',
        hover:      'var(--color-hover)',
        muted:      'var(--color-muted)',
        border:     'var(--color-border)',
        'border-hover': 'var(--color-border-hover)',
        accent:     'var(--color-accent)',
        primary: {
          DEFAULT:    'var(--color-primary)',
          foreground: '#FFFFFF',
          hover:      'var(--color-primary-hover)',
          light:      'var(--color-primary-light)',
        },
        success: {
          DEFAULT: 'var(--color-success)',
          bg:      'var(--color-success-bg)',
        },
        warning: {
          DEFAULT: 'var(--color-warning)',
          bg:      'var(--color-warning-bg)',
        },
        critical: {
          DEFAULT: 'var(--color-critical)',
          bg:      'var(--color-critical-bg)',
        },
        neutral:  'var(--color-neutral)',
        heading:  'var(--color-heading)',
        body:     'var(--color-body)',
        data:     'var(--color-data)',
        subtle:   'var(--color-subtle)',
      },
      fontFamily: {
        sans:  ['var(--font-geist-sans)', 'Inter', 'system-ui', 'sans-serif'],
        mono:  ['var(--font-geist-mono)', '"JetBrains Mono"', 'monospace'],
        serif: ['Merriweather', 'Georgia', 'serif'],
      },
      fontSize: {
        'display': ['2rem', { lineHeight: '1.2', fontWeight: '300' }],
        'heading':  ['1.25rem', { lineHeight: '1.4', fontWeight: '400' }],
      },
      boxShadow: {
        'card':   '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        'modal':  '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
        'rail':   '1px 0 0 0 #E2E8F0',
      },
      borderRadius: {
        DEFAULT: '8px',
        'card':  '8px',
        'pill':  '9999px',
      },
      maxWidth: {
        'feed':    '800px',
        'command': '600px',
        'reader':  '65ch',
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
      keyframes: {
        'fade-up': {
          '0%':   { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-right': {
          '0%':   { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        'slide-in-left': {
          '0%':   { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        'slide-in-bottom': {
          '0%':   { transform: 'translateY(100%)' },
          '100%': { transform: 'translateY(0)' },
        },
        'shimmer': {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.4' },
        },
        'cursor-blink': {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0' },
        },
      },
      animation: {
        'fade-up':          'fade-up 200ms ease-out',
        'slide-in-right':   'slide-in-right 300ms cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-in-left':    'slide-in-left 300ms cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-in-bottom':  'slide-in-bottom 300ms cubic-bezier(0.16, 1, 0.3, 1)',
        'shimmer':          'shimmer 2s infinite linear',
        'pulse-dot':        'pulse-dot 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'cursor-blink':     'cursor-blink 1s step-end infinite',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
