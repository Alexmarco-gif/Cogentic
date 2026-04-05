import {
  buildProviderExtractionConfig,
  getDefaultSourcePreset,
  getDefaultSourceUrlForPreset,
  getProviderLabel,
  getSourcePlaceholder,
} from '@/lib/contracts/providerPresets'

describe('provider presets', () => {
  it('defaults social contracts to the X preset', () => {
    expect(getDefaultSourcePreset('social')).toBe('x')
    expect(getDefaultSourceUrlForPreset('x')).toBe('https://api.twitter.com/2/tweets/search/recent')
  })

  it('builds NewsAPI extraction config from the studio query context', () => {
    expect(
      buildProviderExtractionConfig({
        sourceType: 'api',
        preset: 'newsapi',
        query: 'banking competition',
        industryName: 'Banking',
        region: 'Nigeria',
      }),
    ).toEqual({
      provider: 'newsapi',
      params: {
        q: 'banking competition Banking Nigeria',
      },
    })
  })

  it('exposes NGX Pulse market and stocks presets with sensible defaults', () => {
    expect(getSourcePlaceholder('api', 'ngx_pulse_market')).toBe(
      'https://ngxpulse.ng/api/ngxdata/market',
    )
    expect(getDefaultSourceUrlForPreset('ngx_pulse_stocks')).toBe(
      'https://ngxpulse.ng/api/ngxdata/stocks',
    )
    expect(getProviderLabel('ngx_market_data')).toBe('NGX Pulse API')

    expect(
      buildProviderExtractionConfig({
        sourceType: 'api',
        preset: 'ngx_pulse_market',
        query: 'market summary',
        industryName: 'Capital Markets',
        region: 'Nigeria',
      }),
    ).toEqual({
      provider: 'ngx_market_data',
      pulse_endpoint: 'market',
    })

    expect(
      buildProviderExtractionConfig({
        sourceType: 'api',
        preset: 'ngx_pulse_stocks',
        query: 'equity movers',
        industryName: 'Capital Markets',
        region: 'Nigeria',
      }),
    ).toEqual({
      provider: 'ngx_market_data',
      pulse_endpoint: 'stocks',
    })
  })

  it('builds X extraction config and linkedin placeholders', () => {
    expect(
      buildProviderExtractionConfig({
        sourceType: 'social',
        preset: 'x',
        query: 'payments infra',
        industryName: 'Fintech',
        region: 'Nigeria',
      }),
    ).toEqual({
      provider: 'x',
      platform: 'x',
      params: {
        query: 'payments infra Fintech Nigeria',
      },
    })

    expect(getSourcePlaceholder('scraper', 'linkedin_public')).toBe(
      'https://www.linkedin.com/company/your-company/',
    )
  })
})
