import { Shell } from '@/components/ui/Shell'
import { PageTransition } from '@/components/ui/PageTransition'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <Shell>
      <PageTransition>
        {children}
      </PageTransition>
    </Shell>
  )
}
