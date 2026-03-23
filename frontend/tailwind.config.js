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
        canvas: 'var(--color-canvas)',
        surface: 'var(--color-surface)',
        'surface-2': 'var(--color-surface-2)',
        'surface-3': 'var(--color-surface-3)',
        hover: 'var(--color-hover)',
        muted: 'var(--color-muted)',
        border: 'var(--color-border)',
        'border-hover': 'var(--color-border-hover)',
        accent: 'var(--color-accent)',
        primary: {
          DEFAULT: 'var(--color-primary)',
          foreground: '#FFFFFF',
          hover: 'var(--color-primary-hover)',
          light: 'var(--color-primary-light)',
        },
        success: {
          DEFAULT: 'var(--color-success)',
          bg: 'var(--color-success-bg)',
        },
        warning: {
          DEFAULT: 'var(--color-warning)',
          bg: 'var(--color-warning-bg)',
        },
        critical: {
          DEFAULT: 'var(--color-critical)',
          bg: 'var(--color-critical-bg)',
        },
        neutral: 'var(--color-neutral)',
        heading: 'var(--color-heading)',
        body: 'var(--color-body)',
        data: 'var(--color-data)',
        subtle: 'var(--color-subtle)',
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'monospace'],
        serif: ['var(--font-serif)', 'Georgia', 'serif'],
      },
      fontSize: {
        display: ['3rem', { lineHeight: '1.02', fontWeight: '700', letterSpacing: '-0.04em' }],
        title: ['1rem', { lineHeight: '1.45', fontWeight: '600', letterSpacing: '-0.02em' }],
        body: ['0.9375rem', { lineHeight: '1.65', fontWeight: '500' }],
      },
      boxShadow: {
        card: '0 20px 50px -28px rgba(17, 24, 39, 0.14)',
        modal: '0 30px 80px -34px rgba(17, 24, 39, 0.2)',
        rail: '0 24px 60px -34px rgba(17, 24, 39, 0.22)',
        glow: '0 18px 48px -24px rgba(37, 99, 235, 0.5)',
      },
      borderRadius: {
        DEFAULT: '18px',
        card: '24px',
        pill: '9999px',
      },
      maxWidth: {
        feed: '800px',
        command: '680px',
        reader: '65ch',
        shell: '1440px',
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-right': {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        'slide-in-left': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        'slide-in-bottom': {
          '0%': { transform: 'translateY(18px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.45', transform: 'scale(1.08)' },
        },
        'cursor-blink': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-4px)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 240ms ease-out',
        'slide-in-right': 'slide-in-right 320ms cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-in-left': 'slide-in-left 320ms cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-in-bottom': 'slide-in-bottom 320ms cubic-bezier(0.16, 1, 0.3, 1)',
        shimmer: 'shimmer 2s infinite linear',
        'pulse-dot': 'pulse-dot 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'cursor-blink': 'cursor-blink 1s step-end infinite',
        float: 'float 4.5s ease-in-out infinite',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
