'use client'

import { useState, useCallback, useEffect } from 'react'
import { getMyProfile, updateMyProfile } from '@/lib/api/users'
import { getCurrentUser } from '@/lib/api/auth'
import { listApiKeys, createApiKey, revokeApiKey, rotateApiKey } from '@/lib/api/api_keys'
import { getCreditBalance } from '@/lib/api/pricing'
import { listMySessions, revokeMySession } from '@/lib/api/sessions'
import type {
  APIKeyResponse,
  CreateAPIKeyRequest,
  MappedCreateAPIKeyResponse,
} from '@/lib/api/types'
import type { UserSession } from '@/lib/api/sessions'

// ── Tab definition ────────────────────────────────────────────────────────────

export type SettingsTab =
  | 'profile'
  | 'preferences'
  | 'notifications'
  | 'security'
  | 'integrations'
  | 'billing'
  | 'plan'
  | 'usage'
  | 'data'
  | 'legal'

export const SETTINGS_TABS: { id: SettingsTab; label: string }[] = [
  { id: 'profile',       label: 'My Profile'     },
  { id: 'preferences',   label: 'Preferences'    },
  { id: 'notifications', label: 'Notifications'  },
  { id: 'security',      label: 'Security'       },
  { id: 'plan',          label: 'Plan & Billing' },
  { id: 'usage',         label: 'Usage'          },
  { id: 'data',          label: 'Data & Privacy' },
  { id: 'legal',         label: 'Legal & Help'   },
]

// ── Profile types ─────────────────────────────────────────────────────────────

export interface UserProfile {
  fullName:     string
  username:     string
  email:        string
  phone:        string
  dateOfBirth:  string
  address:      string
  city:         string
  postalCode:   string
  country:      string
  plan:         string
  taxId:        string
  typeCode:     string
  emailVerified: boolean
  phoneVerified: boolean
  avatarUrl?:   string
  coverGradient: string
}

// ── Billing types ─────────────────────────────────────────────────────────────

export type InvoiceStatus = 'Pending' | 'Paid' | 'Cancelled' | 'Refund'

export interface Invoice {
  id:       string
  name:     string
  date:     string
  amount:   number
  status:   InvoiceStatus
  tracking: string
  address:  string
}

export interface PaymentCard {
  nameOnCard:   string
  cardNumber:   string
  expiry:       string
  cvv:          string
}

export interface BillingContact {
  mode:  'existing' | 'other'
  email: string
}

// ── Notification types ────────────────────────────────────────────────────────

export interface NotificationPrefs {
  signalAlerts:    boolean
  weeklyDigest:    boolean
  contractUpdates: boolean
  systemAnnouncements: boolean
  emailEnabled:    boolean
  pushEnabled:     boolean
  smsEnabled:      boolean
}


// ── Integration types ─────────────────────────────────────────────────────────

export interface Integration {
  id:          string
  name:        string
  description: string
  category:    string
  connected:   boolean
  logoInitial: string
  color:       string
}

// ── Usage types ───────────────────────────────────────────────────────────────

export interface UsagePoint {
  month:    string
  credits:  number
  apiCalls: number
}

export interface PlanLimit {
  label:   string
  used:    number
  total:   number
  unit:    string
}

// ── Seed data ─────────────────────────────────────────────────────────────────

const DEFAULT_PROFILE: UserProfile = {
  fullName:      '',
  username:      '',
  email:         '',
  phone:         '',
  dateOfBirth:   '',
  address:       '',
  city:          '',
  postalCode:    '',
  country:       '',
  plan:          '',
  taxId:         '',
  typeCode:      '',
  emailVerified: false,
  phoneVerified: false,
  coverGradient: 'from-gray-100 via-gray-50 to-gray-100',
}

const DEFAULT_CARD: PaymentCard = {
  nameOnCard: '',
  cardNumber: '',
  expiry:     '',
  cvv:        '',
}

const DEFAULT_INVOICES: Invoice[] = []

const DEFAULT_NOTIFICATIONS: NotificationPrefs = {
  signalAlerts:        true,
  weeklyDigest:        true,
  contractUpdates:     true,
  systemAnnouncements: false,
  emailEnabled:        true,
  pushEnabled:         true,
  smsEnabled:          false,
}

const DEFAULT_INTEGRATIONS: Integration[] = [
  { id: 'slack',       name: 'Slack',         description: 'Push signal alerts to channels',     category: 'Communication', connected: true,  logoInitial: 'S', color: '#4A154B' },
  { id: 'notion',      name: 'Notion',        description: 'Export briefs to Notion pages',      category: 'Productivity',  connected: false, logoInitial: 'N', color: '#000000' },
  { id: 'google',      name: 'Google Sheets', description: 'Sync data contracts as spreadsheets',category: 'Data',         connected: true,  logoInitial: 'G', color: '#0F9D58' },
  { id: 'zapier',      name: 'Zapier',        description: 'Automate workflows with signal data', category: 'Automation',   connected: false, logoInitial: 'Z', color: '#FF4A00' },
  { id: 'webhook',     name: 'Webhooks',      description: 'Custom HTTP endpoint delivery',       category: 'Developer',     connected: false, logoInitial: 'W', color: '#4F46E5' },
  { id: 'powerbi',     name: 'Power BI',      description: 'Live dashboard data connector',       category: 'Data',         connected: false, logoInitial: 'P', color: '#F2C811' },
]

const DEFAULT_USAGE: UsagePoint[] = [
  { month: 'Aug', credits: 1200, apiCalls: 3400 },
  { month: 'Sep', credits: 1800, apiCalls: 4800 },
  { month: 'Oct', credits: 2100, apiCalls: 5200 },
  { month: 'Nov', credits: 1600, apiCalls: 4100 },
  { month: 'Dec', credits: 2800, apiCalls: 7200 },
  { month: 'Jan', credits: 3200, apiCalls: 8100 },
]

const DEFAULT_PLAN_LIMITS: PlanLimit[] = [
  { label: 'Credits used',  used: 3200, total: 5000,  unit: 'credits' },
  { label: 'API calls',     used: 8100, total: 20000, unit: 'calls'   },
  { label: 'Data contracts',used: 4,    total: 10,    unit: 'active'  },
  { label: 'Team members',  used: 2,    total: 5,     unit: 'seats'   },
]

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useSettings(initialTab: SettingsTab = 'profile') {
  const [activeTab, setActiveTabState] = useState<SettingsTab>(initialTab)

  // Keep activeTab in sync when initialTab changes (e.g. URL query param changes)
  useEffect(() => {
    setActiveTabState(initialTab)
  }, [initialTab])

  // Update URL query param when tab changes (without full navigation)
  const setActiveTab = useCallback((tab: SettingsTab) => {
    setActiveTabState(tab)
    // Update URL without triggering a full navigation
    const url = new URL(window.location.href)
    url.searchParams.set('tab', tab)
    window.history.replaceState({}, '', url.toString())
  }, [])

  // Resolved org ID (loaded from auth/me)
  const [orgId, setOrgId] = useState<string | null>(null)

  // Profile
  const [profile, setProfile]           = useState<UserProfile>(DEFAULT_PROFILE)
  const [isEditingProfile, setEditingProfile] = useState(false)

  // Load org ID + profile from backend on mount
  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [userCtx, profileData] = await Promise.all([
          getCurrentUser().catch(() => null),
          getMyProfile().catch(() => null),
        ])
        if (cancelled) return
        if (userCtx) setOrgId(userCtx.organization.id)
        if (profileData) {
          setProfile(prev => ({
            ...prev,
            fullName: profileData.name ?? prev.fullName,
            email: profileData.email ?? prev.email,
            avatarUrl: profileData.picture_url ?? prev.avatarUrl,
          }))
        }
      } catch {
        // Backend unavailable — keep defaults
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const updateProfile = useCallback(async (patch: Partial<UserProfile>) => {
    setProfile(p => ({ ...p, ...patch }))

    // Persist profile changes to backend (best-effort)
    try {
      const backendPatch: Record<string, string | undefined> = {}
      if (patch.fullName !== undefined) backendPatch.name = patch.fullName
      if (patch.avatarUrl !== undefined) backendPatch.picture_url = patch.avatarUrl
      if (Object.keys(backendPatch).length > 0) {
        await updateMyProfile(backendPatch as { name?: string; picture_url?: string })
      }
    } catch {
      // Profile update failed — local state is already updated
      console.error('Failed to persist profile update to backend')
    }
  }, [])

  // Billing
  const [card, setCard]                   = useState<PaymentCard>(DEFAULT_CARD)
  const [billingContact, setBillingContact] = useState<BillingContact>({
    mode: 'existing', email: DEFAULT_PROFILE.email,
  })
  const [invoices]                         = useState<Invoice[]>(DEFAULT_INVOICES)
  const [selectedInvoices, setSelected]    = useState<Set<string>>(new Set())
  const toggleInvoiceSelect = useCallback((id: string) => {
    setSelected(s => {
      const next = new Set(s)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }, [])

  // Notifications
  const [notifications, setNotifications] = useState<NotificationPrefs>(DEFAULT_NOTIFICATIONS)
  const toggleNotification = useCallback((key: keyof NotificationPrefs) => {
    setNotifications(n => ({ ...n, [key]: !n[key] }))
  }, [])

  // Security — sessions loaded from backend
  const [sessions, setSessions]   = useState<UserSession[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(true)
  const [twoFAEnabled, setTwoFA]  = useState(true)

  useEffect(() => {
    let cancelled = false
    async function loadSessions() {
      try {
        const data = await listMySessions()
        if (!cancelled) setSessions(data)
      } catch {
        // Keep empty — user will see no extra sessions, which is safe
      } finally {
        if (!cancelled) setSessionsLoading(false)
      }
    }
    loadSessions()
    return () => { cancelled = true }
  }, [])

  const revokeSession = useCallback(async (id: string) => {
    await revokeMySession(id)
    setSessions(s => s.filter(sess => sess.id !== id))
  }, [])

  // API Keys (loaded once orgId is resolved)
  const [apiKeys, setApiKeys] = useState<APIKeyResponse[]>([])

  useEffect(() => {
    if (!orgId) return
    let cancelled = false
    async function loadKeys() {
      try {
        const keys = await listApiKeys(orgId!)
        if (!cancelled) setApiKeys(keys)
      } catch {
        // Keep empty list — user may not be admin
      }
    }
    loadKeys()
    return () => { cancelled = true }
  }, [orgId])

  const handleRevokeApiKey = useCallback(async (keyId: string) => {
    if (!orgId) return
    await revokeApiKey(orgId, keyId)
    setApiKeys(prev => prev.filter(k => k.id !== keyId))
  }, [orgId])

  const handleCreateApiKey = useCallback(async (req: CreateAPIKeyRequest): Promise<MappedCreateAPIKeyResponse | null> => {
    if (!orgId) return null
    const result = await createApiKey(orgId, req)
    // Refresh list after creation
    const keys = await listApiKeys(orgId).catch(() => null)
    if (keys) setApiKeys(keys)
    return result
  }, [orgId])

  const handleRotateApiKey = useCallback(async (keyId: string): Promise<MappedCreateAPIKeyResponse | null> => {
    if (!orgId) return null
    const result = await rotateApiKey(orgId, keyId)
    const keys = await listApiKeys(orgId).catch(() => null)
    if (keys) setApiKeys(keys)
    return result
  }, [orgId])

  // Integrations
  const [integrations, setIntegrations] = useState<Integration[]>(DEFAULT_INTEGRATIONS)
  const toggleIntegration = useCallback((id: string) => {
    setIntegrations(ii => ii.map(i => i.id === id ? { ...i, connected: !i.connected } : i))
  }, [])

  // Usage — load from credits API; fall back to seed data
  const [usageData, setUsageData]   = useState<UsagePoint[]>(DEFAULT_USAGE)
  const [planLimits, setPlanLimits] = useState<PlanLimit[]>(DEFAULT_PLAN_LIMITS)

  useEffect(() => {
    let cancelled = false
    async function loadUsage() {
      try {
        const balance = await getCreditBalance()
        if (cancelled) return
        setPlanLimits(prev =>
          prev.map(limit => {
            if (limit.label === 'Credits used') {
              return { ...limit, used: balance.consumed, total: balance.allocated }
            }
            return limit
          })
        )
      } catch {
        // Keep defaults
      }
    }
    loadUsage()
    return () => { cancelled = true }
  }, [])

  return {
    // Tab
    activeTab, setActiveTab,
    // Profile
    profile, updateProfile, isEditingProfile, setEditingProfile,
    // Billing
    card, setCard, billingContact, setBillingContact,
    invoices, selectedInvoices, toggleInvoiceSelect,
    // Notifications
    notifications, toggleNotification,
    // Security
    sessions, sessionsLoading, twoFAEnabled, setTwoFA, revokeSession,
    // API Keys
    apiKeys, handleRevokeApiKey, handleCreateApiKey, handleRotateApiKey,
    // Integrations
    integrations, toggleIntegration,
    // Usage
    usageData, planLimits,
  }
}
