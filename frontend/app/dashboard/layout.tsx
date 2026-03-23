import { Shell } from '@/components/ui/Shell'
import { PageTransition } from '@/components/ui/PageTransition'
import { OnboardingProvider } from '@/components/onboarding/OnboardingProvider'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <Shell>
      <OnboardingProvider>
        <PageTransition>
          {children}
        </PageTransition>
      </OnboardingProvider>
    </Shell>
  )
}
