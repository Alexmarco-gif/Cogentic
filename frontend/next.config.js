const isDevelopment = process.env.NODE_ENV !== 'production'

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Compress output
  compress: true,

  // ESLint peer deps (@typescript-eslint) are not installed — run lint
  // separately with `npm run lint` after installing dev deps.
  eslint: { ignoreDuringBuilds: true },

  // Standalone output for Docker deployments — production only.
  // Enabling in dev breaks /_next/static/ chunk serving (HMR 404s).
  output: process.env.NODE_ENV === 'production' ? 'standalone' : undefined,

  // Optimise images (remotePatterns replaces deprecated 'domains')
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'lh3.googleusercontent.com' },
      { protocol: 'https', hostname: 'avatars.githubusercontent.com' },
      { protocol: 'https', hostname: 's.gravatar.com' },
    ],
    formats: ['image/avif', 'image/webp'],
  },

  // Ensure packages that use browser APIs aren't accidentally bundled on the server
  experimental: {
    optimizePackageImports: ['lucide-react', 'framer-motion', 'recharts'],
    sri: process.env.NODE_ENV === 'production' ? { algorithm: 'sha256' } : undefined,
  },

  async headers() {
    return [
      {
        // Service worker must be served with no-cache so updates are picked up
        source: '/sw.js',
        headers: [
          { key: 'Cache-Control',  value: 'public, max-age=0, must-revalidate' },
          { key: 'Service-Worker-Allowed', value: '/' },
          { key: 'Content-Type',  value: 'application/javascript' },
        ],
      },
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options',        value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy',        value: 'strict-origin-when-cross-origin' },
          { key: 'X-XSS-Protection',       value: '1; mode=block' },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload',
          },
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              `script-src 'self'${isDevelopment ? " 'unsafe-eval'" : ''}`,
              // The app still uses controlled inline style attributes in a few places,
              // so styles remain temporarily whitelisted while scripts are hardened.
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: https:",
              "font-src 'self' data:",
              "connect-src 'self' https://*.auth0.com wss://*.auth0.com https://*.sentry.io https://*.posthog.com",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join('; '),
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=(self)',
          },
        ],
      },
    ]
  },

  async rewrites() {
    return [
      {
        source:      '/api/v1/:path*',
        destination: `${process.env.BACKEND_URL || 'http://localhost:8000'}/api/v1/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
