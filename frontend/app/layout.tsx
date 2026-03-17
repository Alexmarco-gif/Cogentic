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
    default:  'Cogent',
    template: '%s — Cogent',
  },
  description: 'Strategic intelligence platform for enterprise analysts',
  manifest:    '/manifest.json',
  appleWebApp: {
    capable:         true,
    statusBarStyle:  'default',
    title:           'Cogent',
  },
  icons: {
    icon:   '/stem-cogent.svg',
    apple:  '/stem-cogent.svg',
  },
  openGraph: {
    title:       'Cogent',
    description: 'Strategic intelligence platform',
    type:        'website',
  },
}

export const viewport: Viewport = {
  themeColor:          '#4F46E5',
  width:               'device-width',
  initialScale:        1,
  maximumScale:        1,
  userScalable:        false,
  viewportFit:         'cover',  // enables safe-area-inset CSS vars
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`} suppressHydrationWarning>
      <head>
        {/* Apply stored theme BEFORE first paint to prevent flash */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                const stored = JSON.parse(localStorage.getItem('cogent-theme') || '{}');
                if (stored.state && stored.state.theme === 'dark') {
                  document.documentElement.classList.add('dark');
                }
              } catch(e) {}
            `,
          }}
        />
      </head>
      <body className="font-sans bg-canvas text-body transition-colors duration-200">
        <PricingProvider>
          <Auth0Provider>
            <ThemeProvider>
              {children}
            </ThemeProvider>
          </Auth0Provider>
        </PricingProvider>
        <ServiceWorkerRegistration />
      </body>
    </html>
  )
}
