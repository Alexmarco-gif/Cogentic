import { redirect } from 'next/navigation'
import { auth0 } from '@/lib/auth0'

// Root → redirect to login if unauthenticated, dashboard if authenticated
export default async function RootPage() {
  const session = await auth0.getSession()
  if (session) {
    redirect('/dashboard/home')
  } else {
    redirect('/login')
  }
}
