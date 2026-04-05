export type StudioSourceType = 'api' | 'rss' | 'scraper' | 'social' | 'webhook'
export type ContractSourcePreset =
  | 'generic'
  | 'newsapi'
  | 'ngx_market_data'
  | 'ngx_pulse_market'
  | 'ngx_pulse_stocks'
  | 'x'
  | 'linkedin_public'

export interface StudioProviderOption {
  value: ContractSourcePreset
  label: string
  description: string
}

export const SOURCE_PRESET_OPTIONS: Record<StudioSourceType, StudioProviderOption[]> = {
  api: [
    {
      value: 'generic',
      label: 'Generic API',
      description: 'Use a custom REST endpoint with contract-defined extraction rules.',
    },
    {
      value: 'newsapi',
      label: 'NewsAPI',
      description: 'Wire the contract to NewsAPI article search with app-managed auth.',
    },
    {
      value: 'ngx_pulse_market',
      label: 'NGX Pulse Market',
      description: 'Track NGX Pulse market summary data with the default market endpoint.',
    },
    {
      value: 'ngx_pulse_stocks',
      label: 'NGX Pulse Stocks',
      description: 'Track the NGX Pulse all-stocks feed for exchange-wide price and volume movement.',
    },
  ],
  rss: [
    {
      value: 'generic',
      label: 'Generic RSS',
      description: 'Track a public RSS or Atom feed URL.',
    },
  ],
  scraper: [
    {
      value: 'generic',
      label: 'Generic scraper',
      description: 'Scrape a public page with custom selectors.',
    },
    {
      value: 'linkedin_public',
      label: 'LinkedIn public page',
      description: 'Scrape a public LinkedIn company or profile page snapshot.',
    },
  ],
  social: [
    {
      value: 'x',
      label: 'X',
      description: 'Search X posts with the platform bearer token stored in runtime config.',
    },
  ],
  webhook: [
    {
      value: 'generic',
      label: 'Webhook',
      description: 'Deliver newly ingested signals to your own endpoint.',
    },
  ],
}

const DEFAULT_SOURCE_URLS: Partial<Record<ContractSourcePreset, string>> = {
  newsapi: 'https://newsapi.org/v2/everything',
  ngx_pulse_market: 'https://ngxpulse.ng/api/ngxdata/market',
  ngx_pulse_stocks: 'https://ngxpulse.ng/api/ngxdata/stocks',
  x: 'https://api.twitter.com/2/tweets/search/recent',
}

const PRESET_PLACEHOLDERS: Record<ContractSourcePreset, string> = {
  generic: 'https://example.com/feed-or-api',
  newsapi: DEFAULT_SOURCE_URLS.newsapi!,
  ngx_market_data: DEFAULT_SOURCE_URLS.ngx_pulse_market!,
  ngx_pulse_market: DEFAULT_SOURCE_URLS.ngx_pulse_market!,
  ngx_pulse_stocks: DEFAULT_SOURCE_URLS.ngx_pulse_stocks!,
  x: DEFAULT_SOURCE_URLS.x!,
  linkedin_public: 'https://www.linkedin.com/company/your-company/',
}

export function getDefaultSourcePreset(sourceType: StudioSourceType): ContractSourcePreset {
  return SOURCE_PRESET_OPTIONS[sourceType][0]?.value ?? 'generic'
}

export function getProviderOptions(sourceType: StudioSourceType): StudioProviderOption[] {
  return SOURCE_PRESET_OPTIONS[sourceType]
}

export function getProviderLabel(preset: ContractSourcePreset): string {
  const option = Object.values(SOURCE_PRESET_OPTIONS)
    .flat()
    .find((candidate) => candidate.value === preset)
  if (option?.label) {
    return option.label
  }
  if (preset === 'ngx_market_data') {
    return 'NGX Pulse API'
  }
  return preset
}

export function getDefaultSourceUrlForPreset(preset: ContractSourcePreset): string {
  return DEFAULT_SOURCE_URLS[preset] ?? ''
}

export function getSourcePlaceholder(
  sourceType: StudioSourceType,
  preset: ContractSourcePreset,
): string {
  if (sourceType === 'webhook') {
    return 'https://your-service.com/webhook'
  }

  return PRESET_PLACEHOLDERS[preset] ?? PRESET_PLACEHOLDERS.generic
}

export function getSourcePresetDescription(
  sourceType: StudioSourceType,
  preset: ContractSourcePreset,
): string {
  return (
    getProviderOptions(sourceType).find((option) => option.value === preset)?.description
    ?? 'Provide the source entrypoint the contract should monitor.'
  )
}

export function buildProviderExtractionConfig(input: {
  sourceType: StudioSourceType
  preset: ContractSourcePreset
  query: string
  industryName?: string
  region: string
}): Record<string, unknown> {
  const fallbackQuery = [input.query.trim(), input.industryName ?? '', input.region]
    .filter(Boolean)
    .join(' ')
    .trim()

  switch (input.preset) {
    case 'newsapi':
      return {
        provider: 'newsapi',
        params: fallbackQuery ? { q: fallbackQuery } : {},
      }
    case 'ngx_market_data':
    case 'ngx_pulse_market':
      return {
        provider: 'ngx_market_data',
        pulse_endpoint: 'market',
      }
    case 'ngx_pulse_stocks':
      return {
        provider: 'ngx_market_data',
        pulse_endpoint: 'stocks',
      }
    case 'x':
      return {
        provider: 'x',
        platform: 'x',
        params: fallbackQuery ? { query: fallbackQuery } : {},
      }
    case 'linkedin_public':
      return {
        provider: 'linkedin_public',
      }
    case 'generic':
    default:
      return {}
  }
}
