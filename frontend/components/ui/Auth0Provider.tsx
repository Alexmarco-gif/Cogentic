'use client'

import { Auth0Provider as Auth0ClientProvider } from '@auth0/nextjs-auth0/client'

export function Auth0Provider({ children }: { children: React.ReactNode }) {
  return <Auth0ClientProvider>{children}</Auth0ClientProvider>
}
