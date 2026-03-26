'use client'

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

import {
  friendlyErrorMessage,
  getCreditBalance,
  getCurrentPricing,
  getFeatureAccess,
} from '@/lib/api'
import type { CreditBalanceResponse } from '@/lib/api'

interface PricingContextType {
  tier: string
  features: Record<string, boolean>
  credits: CreditBalanceResponse
  loading: boolean
  pricingResolved: boolean
  featuresResolved: boolean
  creditsResolved: boolean
  error: string | null
  refresh: () => Promise<void>
}

const PricingContext = createContext<PricingContextType | null>(null)

const FALLBACK: Omit<PricingContextType, 'refresh'> = {
  tier: 'explorer',
  features: {},
  credits: {
    allocated: 0,
    consumed: 0,
    remaining: 0,
    overage: 0,
    overage_rate: 0,
  },
  loading: false,
  pricingResolved: false,
  featuresResolved: false,
  creditsResolved: false,
  error: null,
}

interface PricingProviderProps {
  children: ReactNode
}

export function PricingProvider({ children }: PricingProviderProps) {
  const [pricingData, setPricingData] = useState<PricingContextType>({
    ...FALLBACK,
    refresh: async () => {},
  })
  const [loading, setLoading] = useState(true)

  const fetchPricingData = async () => {
    try {
      setLoading(true)

      const [pricing, features, credits] = await Promise.all([
        getCurrentPricing(),
        getFeatureAccess(),
        getCreditBalance(),
      ])

      setPricingData({
        tier: pricing.tier,
        features: features.features,
        credits,
        loading: false,
        pricingResolved: true,
        featuresResolved: true,
        creditsResolved: true,
        error: null,
        refresh: fetchPricingData,
      })
    } catch (error) {
      setPricingData({
        ...FALLBACK,
        error: friendlyErrorMessage(error),
        refresh: fetchPricingData,
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchPricingData()
  }, [])

  return (
    <PricingContext.Provider value={{ ...pricingData, loading }}>
      {children}
    </PricingContext.Provider>
  )
}

export function usePricing() {
  const context = useContext(PricingContext)
  if (!context) {
    throw new Error('usePricing must be used within PricingProvider')
  }
  return context
}
