import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: {
    template: '%s — Cogent',
    default:  'Cogent',
  },
}

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
