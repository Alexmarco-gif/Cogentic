import type { Metadata, Viewport } from 'next'
import { GeistSans } from 'geist/font/sans'
import { GeistMono } from 'geist/font/mono'
import './globals.css'
import { PricingProvider } from '@/lib/contexts/PricingContext'
import { ThemeProvider } from '@/components/ui/ThemeProvider'
import { Auth0Provider } from '@/components/ui/Auth0Provider'
import { ServiceWorkerRegistration } from '@/components/ui/ServiceWorkerRegistration'

export const metadata: Metadata = {
  title: {
    default: 'Stem-Cogent',
    template: '%s - Strategic Decision Intelligence Platform',
  },
  description: ' Strategic Decision Intelligence Platform',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'Stem-Cogent',
  },
  icons: {
    icon: [
      { url: '/stem-icon-180x180-corrected.png', sizes: '180x180', type: 'image/png' },
      { url: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/icon-512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: [
      { url: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
    shortcut: '/stem-icon-180x180-corrected.png',
  },
  openGraph: {
    title: 'Stem-Cogent',
    description: 'Strategic Decision Intelligence Platform',
    type: 'website',
  },
}

export const viewport: Viewport = {
  themeColor: '#2563EB',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                const stored = JSON.parse(localStorage.getItem('cogent-theme') || '{}');
                if (stored.state && stored.state.theme === 'dark') {
                  document.documentElement.classList.add('dark');
                }
              } catch (e) {}
            `,
          }}
        />
      </head>
      <body className="font-sans bg-canvas text-body transition-colors duration-200">
        <PricingProvider>
          <Auth0Provider>
            <ThemeProvider>{children}</ThemeProvider>
          </Auth0Provider>
        </PricingProvider>
        <ServiceWorkerRegistration />
      </body>
    </html>
  )
}
