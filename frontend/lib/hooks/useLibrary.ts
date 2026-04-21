'use client'

import { useState, useMemo, useEffect, useCallback } from 'react'
import { friendlyErrorMessage } from '@/lib/api'
import { getBrief, listBriefs as fetchBriefsList } from '@/lib/api/briefs'
import {
  normalizeIntelligenceBrief,
} from '@/lib/briefs/schema'
import type { BriefResponse } from '@/lib/api/types'

// ── Types ─────────────────────────────────────────────────────────────────────

export type LibraryBriefType = 'ai-brief' | 'weekly-report' | 'deep-analysis' | 'sector-review'

export type LibraryBriefDomain =
  | 'Agriculture'
  | 'Finance'
  | 'Energy'
  | 'Technology'
  | 'Consumer'
  | 'Healthcare'
  | 'Cross-Sector'
  | 'Macro'

export interface LibraryBrief {
  id: string
  title: string
  subtitle?: string
  domain: LibraryBriefDomain
  type: LibraryBriefType
  /** ISO date string */
  publishedAt: string
  /** Human-readable relative date */
  relativeDate: string
  confidence: number             // 0–100
  tags: string[]
  summary: string                // 2-3 sentence abstract shown in ReaderModal
  /** Full body — array of {heading, paragraphs} sections */
  sections: LibrarySection[]
  author: 'AI Generated' | 'Cogent Research' | 'Sector Analyst'
  readTimeMinutes: number
  isSaved: boolean
}

export interface LibrarySection {
  heading: string
  content: string
}

export type LibrarySortKey = 'date' | 'confidence' | 'readTime' | 'title'
export type LibraryFilterDomain = LibraryBriefDomain | 'All'
export type LibraryFilterType = LibraryBriefType | 'All'

// Legacy fixture data retained only as a migration reference while Library cleanup continues.
// It is no longer used in the runtime fetching path.

const SEED_BRIEFS: LibraryBrief[] = [
  {
    id: 'lib-001',
    title: 'Impact of Fuel Subsidy Removal on Q3 Agri-Yields',
    subtitle: 'Supply chain cost transmission analysis across six crop categories',
    domain: 'Agriculture',
    type: 'deep-analysis',
    publishedAt: '2024-12-15T08:00:00Z',
    relativeDate: 'Dec 15, 2024',
    confidence: 87,
    tags: ['#Agriculture', '#Policy', '#Q3', '#Subsidy'],
    summary:
      'The removal of Nigeria\'s fuel subsidy in May 2023 transmitted significant cost increases to agricultural logistics, raising farm-gate-to-market transport costs by an estimated 23–31%. This analysis models the pass-through effect on six major crop categories — maize, cassava, tomato, yam, sorghum, and rice — identifying regional variance in yield realisation for Q3 2024 and downstream food price pressure.',
    sections: [
      {
        heading: 'Executive Summary',
        content:
          'Fuel subsidy removal elevated transport costs across Nigeria\'s agricultural supply chains by 23–31%. The North-Central and North-West zones faced the sharpest impact given longer haul distances to consumption centres in Lagos and Abuja. Maize and sorghum yields in Kaduna and Katsina recorded below-expectation realisation rates of 82% and 78% respectively against the Q3 harvest plan.',
      },
      {
        heading: 'Logistics Cost Transmission',
        content:
          'Pre-subsidy PMS prices averaged ₦185/litre. Post-removal spot rates stabilised around ₦617–650/litre by Q3 2024, a 233% increase. A 40-tonne truck covering the Kano–Lagos corridor (912 km) now costs ₦387,000 in fuel alone, up from ₦117,000. This cost is shared between aggregator and offtaker — typically 60/40 — with the 60% component passed directly into farmgate price spreads.',
      },
      {
        heading: 'Crop-Level Impact Analysis',
        content:
          'Tomato and leafy vegetables, being the most perishable, absorbed the largest unit-cost shock due to refrigerated transport premiums. Cassava, being domestically processed at origin, experienced the lowest impact. Maize showed a 12% higher unit cost of transfer, contributing to a 7.4% retail price increase in Lagos markets tracked through October 2024.',
      },
      {
        heading: 'Regional Variance',
        content:
          'Southern states (Ogun, Oyo, Delta) showed lower impact given proximity to both production clusters and urban demand centres. The Middle Belt — historically the food basket — showed the most acute supply chain stress. Kaduna State\'s agricultural commissioner confirmed 14 contract disruptions in mid-season as aggregators renegotiated offtake terms.',
      },
      {
        heading: 'Outlook',
        content:
          'Q4 2024 and Q1 2025 are expected to see partial normalisation as aggregators restructure logistics contracts onto fixed-fee rail and barge alternatives. Dangote Refinery output reaching commercial scale by Q2 2025 is the primary variable that could meaningfully reduce road transport costs by 15–22% on the key northern corridors.',
      },
    ],
    author: 'AI Generated',
    readTimeMinutes: 7,
    isSaved: false,
  },
  {
    id: 'lib-002',
    title: 'CBN Monetary Policy: Disinflation Trajectory & Rate Path',
    subtitle: 'MPR hold at 27.5% confirmed — forward guidance analysis',
    domain: 'Finance',
    type: 'ai-brief',
    publishedAt: '2025-01-08T09:30:00Z',
    relativeDate: 'Jan 8, 2025',
    confidence: 92,
    tags: ['#Finance', '#CBN', '#Inflation', '#MonetaryPolicy'],
    summary:
      'The CBN\'s January 2025 MPC meeting confirmed the MPR hold at 27.5%, signalling a pause in the tightening cycle as headline inflation showed a second consecutive monthly decline — from 34.8% in October to 33.1% in December 2024. This brief analyses the forward rate path, foreign exchange stability implications, and sector-level credit impact.',
    sections: [
      {
        heading: 'MPC Decision Context',
        content:
          'The Monetary Policy Committee voted 7-2 to hold the policy rate at 27.5%, with the Cash Reserve Ratio maintained at 45%. The two dissenting members advocated a 50bps cut, signalling that internal debate on the pace of easing has begun. Governor Cardoso\'s post-meeting statement emphasised that the disinflation trend must be "durably established" before accommodation commences.',
      },
      {
        heading: 'Inflation Dynamics',
        content:
          'Year-on-year headline inflation peaked at 34.80% in October 2024. December\'s print of 33.09% represents the first meaningful two-month decline since the subsidy removal shock. Food inflation remains the dominant driver at 39.8% YoY, though base effects from the 2023 disruption year will begin to provide mechanical relief from Q2 2025.',
      },
      {
        heading: 'Naira FX Implications',
        content:
          'The NAFEM window rate stabilised between ₦1,575–₦1,620/USD through January. CBN net reserve accretion of $1.2B in Q4 2024 (from Eurobond proceeds and Afrexim drawdowns) provides a meaningful buffer. Analysts at Stanbic IBTC project FX stability will hold through H1 2025 absent external shock.',
      },
      {
        heading: 'Sector Credit Impact',
        content:
          'Prime lending rates remain above 29%, constraining SME credit access. Manufacturing capacity utilisation declined to 52% in Q3 2024, partly attributed to working capital stress. The CBN\'s development finance interventions — particularly the ₦500B AGSMEIS facility — partially offset commercial credit tightness in priority sectors.',
      },
    ],
    author: 'Cogent Research',
    readTimeMinutes: 5,
    isSaved: true,
  },
  {
    id: 'lib-003',
    title: 'Weekly Intelligence Report — W3 January 2025',
    subtitle: 'Nigeria Market Intelligence · 14 signals synthesised',
    domain: 'Cross-Sector',
    type: 'weekly-report',
    publishedAt: '2025-01-19T07:00:00Z',
    relativeDate: 'Jan 19, 2025',
    confidence: 89,
    tags: ['#Weekly', '#Macro', '#Nigeria', '#CrossSector'],
    summary:
      'The third week of January brought accelerating clarity on three macro themes: disinflation confirmation, digital commerce growth momentum in Lagos, and expansion signals from regional agri-infrastructure. Fourteen signals were synthesised across Agriculture, Finance, Technology, and Energy domains.',
    sections: [
      {
        heading: 'Executive Summary',
        content:
          'W3 January 2025 featured the CBN MPC hold, Q3 agri-yield data revision, and Jumia\'s Q4 GMV disclosure. The overall signal environment tilts constructive with two critical risk items: escalating logistics costs in the Middle Belt and delayed MTN 5G expansion timelines in the North-West.',
      },
      {
        heading: 'Key Signals This Week',
        content:
          'CBN MPR hold at 27.5% (confidence: high). Jumia Nigeria GMV +34% YoY in Q4 2024 confirms digital commerce inflection. Babban Gona secures IFC $60M facility for farmer network expansion. MTN confirms North-West 5G rollout delayed to Q3 2025 due to right-of-way permitting. Dangote Refinery begins commercial PMS sales at ₦899/litre.',
      },
      {
        heading: 'Agriculture Domain',
        content:
          'Post-harvest aggregation season for maize and sorghum is active in the North-Central zone. Babban Gona\'s IFC facility unlock signals material expansion of the 1M-farmer network. Commodity price spreads between farm-gate and Lagos market remain elevated at 2.8× — above the 2.1× historical average.',
      },
      {
        heading: 'Finance Domain',
        content:
          'MPR hold confirmed. Nigeria\'s external reserves crossed $36B (gross) for the first time since mid-2023. Two DFI offices opened in Abuja — AIIB and IFC expanded presence — indicating foreign institutional confidence in the reform trajectory. Bank of Industry disbursed ₦87B in Q4 2024 across manufacturing and agriculture.',
      },
      {
        heading: 'Technology Domain',
        content:
          'Jumia Q4 GMV of $176M represents the strongest quarterly result in four years. JumiaPay\'s share of GMV reached 22%, a structural shift toward embedded digital payments. Lagos digital CPM (cost per thousand) in mobile advertising rose 19% QoQ, signalling competitive pressure among consumer brands for digital attention.',
      },
      {
        heading: 'Outlook for W4',
        content:
          'Watch for: NBS CPI print (expected Jan 22), Zenith Bank full-year results, and the Ondo State agricultural investment summit. The subsidy savings utilisation report expected from the Ministry of Finance will be a key signal for public investment direction in H1 2025.',
      },
    ],
    author: 'Cogent Research',
    readTimeMinutes: 9,
    isSaved: false,
  },
  {
    id: 'lib-004',
    title: 'Jumia Nigeria: Digital Commerce Inflection Analysis',
    subtitle: 'Q4 GMV +34% YoY — structural shift or base effect?',
    domain: 'Technology',
    type: 'deep-analysis',
    publishedAt: '2025-01-22T10:00:00Z',
    relativeDate: 'Jan 22, 2025',
    confidence: 84,
    tags: ['#Technology', '#eCommerce', '#Jumia', '#Lagos'],
    summary:
      'Jumia\'s Q4 2024 result — GMV of $176M (+34% YoY) with JumiaPay penetrating 22% of gross merchandise value — represents a genuine structural shift rather than a base effect. This analysis decomposes the growth drivers, evaluates the unit economics trajectory, and models the competitive implications for traditional retail and logistics incumbents.',
    sections: [
      {
        heading: 'Growth Decomposition',
        content:
          'Of the 34% YoY GMV growth, base effect from Q4 2023\'s currency devaluation-driven demand suppression accounts for approximately 11 percentage points. True volume growth is estimated at 23% — still the strongest organic print since 2020. Category mix has shifted materially: electronics fell from 38% to 29% of GMV as fashion, FMCG, and health categories accelerated.',
      },
      {
        heading: 'JumiaPay Structural Shift',
        content:
          'JumiaPay reaching 22% GMV share (up from 14% in Q4 2023) is the most significant structural development. Digital payment penetration reduces COD exposure — historically Jumia\'s highest unit-cost fulfilment pathway — and enables credit scoring for buy-now-pay-later integration. The implied annualised JumiaPay TPV approaches $150M, a threshold that attracts fintech partnership attention.',
      },
      {
        heading: 'Logistics Unit Economics',
        content:
          'With Dangote Refinery PMS at ₦899/litre representing a 31% discount to open-market prices for large fleet operators, Jumia\'s last-mile logistics cost per delivery fell an estimated 9% in Q4 2024. Combined with route density improvements in Lagos, return-item rates, and bulk sortation automation at the Oshodi hub, fulfilment cost per order is estimated at $2.10 — approaching break-even on a contribution basis.',
      },
      {
        heading: 'Competitive Implications',
        content:
          'Konga\'s 2024 restructuring removed it as a credible #2 platform. The market is bifurcating between Jumia (informal/value segment, national reach) and vertical players: Farmcrowdy (agriculture inputs), Healthplus (pharmacy), and WhatsApp Commerce native sellers. Traditional open-market traders in Lagos Alaba and Balogun markets increasingly use Jumia\'s B2B vendor channel as a distribution layer rather than a competitive threat.',
      },
    ],
    author: 'AI Generated',
    readTimeMinutes: 6,
    isSaved: false,
  },
  {
    id: 'lib-005',
    title: 'Dangote Refinery: Downstream Energy Market Disruption',
    subtitle: '650,000 bpd capacity — who wins, who loses?',
    domain: 'Energy',
    type: 'sector-review',
    publishedAt: '2025-01-10T11:00:00Z',
    relativeDate: 'Jan 10, 2025',
    confidence: 91,
    tags: ['#Energy', '#Dangote', '#Downstream', '#Logistics'],
    summary:
      'The Dangote Aliko Refinery\'s commercial PMS sales at ₦899/litre mark the most significant structural shift in Nigeria\'s downstream energy sector since deregulation. This sector review analyses the winners, losers, and second-order effects across logistics, manufacturing, and consumer retail in a 12-month forward window.',
    sections: [
      {
        heading: 'Refinery Output Context',
        content:
          'At nameplate capacity of 650,000 bpd, Dangote Refinery is the largest single-train refinery in the world. Current operating rate is estimated at 28–35% capacity (180,000–230,000 bpd), producing approximately 13.5 million litres of PMS per day. This covers roughly 40% of Nigeria\'s estimated 35 million litres/day domestic demand.',
      },
      {
        heading: 'Price Mechanism and Impact',
        content:
          'The ex-depot price of ₦899/litre equates to approximately $0.55/litre at current exchange — well below the import-parity cost floor. Major fleet operators (logistics, manufacturing, construction) with direct depot access capture an immediate 28–31% cost reduction versus open-market pump prices of ₦1,250–₦1,310/litre. This gap will narrow as NNPC reduces subsidised allocations.',
      },
      {
        heading: 'Logistics Sector Winners',
        content:
          'FMCG distributors, agricultural aggregators, and e-commerce last-mile operators with vehicle fleets exceeding 50 units qualify for direct depot offtake. AB InBev\'s Nigerian bottling operations, Dangote Cement\'s own transport fleet, and Friesland Campina (FrieslandCampina WAMCO) are positioned to capture the highest absolute savings. Estimated annual savings for a 100-truck FMCG fleet: ₦2.1B.',
      },
      {
        heading: 'Petrol Retail Disruption',
        content:
          'NNPC retail stations face margin compression as the spread between their fixed pricing and Dangote depot pricing tightens. Independent marketers that built profitability on arbitrage between black-market and regulated price will face structural elimination of that margin. The Nigerian Midstream and Downstream Petroleum Regulatory Authority (NMDPRA) has signalled 60-day licensing for new depot operators — attracting private entrants.',
      },
      {
        heading: '12-Month Forward View',
        content:
          'As Dangote ramps toward 60% utilisation by H2 2025, the price-setting dynamic will shift from import parity to domestic production cost. This should pull PMS prices toward ₦700–₦750/litre by Q3 2025, assuming naira stability. The downstream energy market will see consolidation: 3,000+ petrol stations are economically unviable at tight margins — expect a wave of closures or conversion to LPG.',
      },
    ],
    author: 'Sector Analyst',
    readTimeMinutes: 8,
    isSaved: true,
  },
  {
    id: 'lib-006',
    title: 'Nigeria FDI Pipeline: Infrastructure & Tech Sector Outlook',
    subtitle: 'Q1–Q2 2025 deal flow and institutional positioning',
    domain: 'Macro',
    type: 'ai-brief',
    publishedAt: '2025-01-25T08:30:00Z',
    relativeDate: 'Jan 25, 2025',
    confidence: 78,
    tags: ['#FDI', '#Infrastructure', '#Macro', '#Investment'],
    summary:
      'Foreign direct investment signals in Nigeria\'s infrastructure and technology sectors are strengthening for H1 2025. Two new DFI office openings in Abuja, an IFC mandate in agri-logistics, and expanding Prosus/Naspers interest in fintech infrastructure signal institutional confidence in the reform trajectory under the Tinubu administration.',
    sections: [
      {
        heading: 'DFI Institutional Signals',
        content:
          'The African Infrastructure Investment Bank (AIIB) and International Finance Corporation (IFC) both expanded Abuja-based presence in January 2025. This operational commitment — as distinct from paper mandates — typically precedes deal execution by 6–18 months and signals pipeline development activity is underway. Combined indicative pipeline: $800M–$1.2B across power, logistics, and digital infrastructure.',
      },
      {
        heading: 'Technology Sector Momentum',
        content:
          'Prosus (formerly Naspers) has been in commercial discussions with two payment infrastructure companies in Lagos — reportedly OPay and PalmPay\'s parent entity. The Nigerian fintech sector raised $438M in disclosed deals in 2024, down 31% from 2023 but showing higher average deal size, indicating a shift from seed/series A to growth capital. Flutterwave\'s pending NYSE listing process remains the signature exit catalyst for the sector.',
      },
      {
        heading: 'Government Cloud Infrastructure',
        content:
          'The Federal Government\'s ₦22B cloud infrastructure procurement — awarded to consortium of IXION Technologies and Microsoft Azure — represents the largest single government IT spend since 2018. Downstream contracts for systems integration, data migration, and managed services create a secondary procurement market estimated at ₦8–12B over 36 months.',
      },
      {
        heading: 'Risk Factors',
        content:
          'Currency repatriation risk remains the primary FDI deterrent. Despite NAFEM reform, institutional investors cite settlement delays and residual shadow FX as barriers. The proposed FIRS Value Added Tax reform (proposed increase from 7.5% to 10%) introduces an additional cost headwind for consumer-facing digital businesses that has not yet been priced into valuations.',
      },
    ],
    author: 'AI Generated',
    readTimeMinutes: 5,
    isSaved: false,
  },
  {
    id: 'lib-007',
    title: 'Agricultural Input Market: Fertiliser Price Dynamics',
    subtitle: 'Urea and NPK pricing across Northern Nigeria — Q4 2024',
    domain: 'Agriculture',
    type: 'sector-review',
    publishedAt: '2024-12-20T09:00:00Z',
    relativeDate: 'Dec 20, 2024',
    confidence: 81,
    tags: ['#Agriculture', '#Fertiliser', '#Inputs', '#NorthNigeria'],
    summary:
      'Urea and NPK fertiliser prices in Northern Nigeria\'s primary planting zones diverged sharply in Q4 2024 — driven by import substitution dynamics following the Dangote Fertiliser plant ramp-up, erratic NNPC-subsidised distribution, and foreign exchange constraints on competing importers. This review provides a granular pricing map and forward supply outlook.',
    sections: [
      {
        heading: 'Price Map Q4 2024',
        content:
          'Bag (50kg) of urea: Kano Open Market ₦32,500 vs Lagos Port Clearing ₦28,200. NPK 15-15-15: Kaduna ₦29,800 vs Maiduguri ₦38,400 — reflecting distance-from-supply and logistics premium. Dangote Fertiliser ex-gate prices for bulk offtakers: urea at ₦24,000/bag (31% below open-market), creating significant arbitrage dynamics.',
      },
      {
        heading: 'Dangote Fertiliser Impact',
        content:
          'The 3.0 million MT/year Dangote urea plant operating at 70%+ utilisation is reshaping the northern fertiliser market. Pre-2023, >80% of Nigeria\'s urea was imported. In Q4 2024, estimated domestic production share reached 52%. This structural shift redirects FX demand: each tonne of domestic urea produced saves approximately $320 in import FX requirements.',
      },
      {
        heading: 'Distribution Bottlenecks',
        content:
          'The Presidential Fertiliser Initiative (PFI) distribution channels remain inefficient — 2024 saw only 62% of allocated bags reach intended smallholder farmers based on CBN-verified receipts. Babban Gona\'s last-mile model, which achieves 94%+ receipt verification, demonstrates the scalability gap between state-managed and private distribution.',
      },
      {
        heading: 'Planting Season Outlook',
        content:
          'For the Q1–Q2 2025 wet season planting, input availability looks constructive — estimated 15% better than the same period in 2024. The key risk is distribution logistics rather than production: if urea cannot reach Northern farmers by mid-March, the critical maize planting window closes with below-optimal input adoption.',
      },
    ],
    author: 'Cogent Research',
    readTimeMinutes: 6,
    isSaved: false,
  },
  {
    id: 'lib-008',
    title: 'Telecommunications Sector: 5G Rollout Feasibility Analysis',
    subtitle: 'MTN, Airtel, Glo — spectrum, infrastructure, and readiness',
    domain: 'Technology',
    type: 'deep-analysis',
    publishedAt: '2025-01-14T11:30:00Z',
    relativeDate: 'Jan 14, 2025',
    confidence: 76,
    tags: ['#Technology', '#5G', '#Telecoms', '#MTN', '#Infrastructure'],
    summary:
      'Nigeria\'s 5G rollout faces a structural paradox: sufficient spectrum allocation and demonstrated operator appetite, yet a hostile right-of-way (ROW) permitting environment, power infrastructure deficits, and capital cost headwinds from naira depreciation. This analysis models feasibility timelines for MTN, Airtel, and Glo across urban, peri-urban, and rural deployment scenarios.',
    sections: [
      {
        heading: 'Spectrum Allocation Status',
        content:
          'The Nigerian Communications Commission (NCC) awarded 5G spectrum to MTN, Airtel, and Mafab in December 2021 in the 3.5 GHz band. MTN and Airtel each hold 100 MHz in the 3.5GHz band; Mafab holds an equal allocation but has not yet commenced commercial deployment. The NCC has indicated willingness to award additional spectrum in the mmWave band (26 GHz) for dense urban use cases.',
      },
      {
        heading: 'Right-of-Way Barriers',
        content:
          'ROW permitting — controlled by 36 state governments and the FCT — is the primary deployment bottleneck. MTN disclosed that 23% of planned North-West tower sites are held pending state-level ROW approval, with resolution timelines ranging from 6 to 18 months. The Federal Government\'s harmonised ROW framework, passed in 2022, has not been universally adopted at state level.',
      },
      {
        heading: 'Power Infrastructure Constraint',
        content:
          'Each 5G base station requires approximately 5–7 kW of reliable power — 3× the requirement of a 4G LTE site. Nigeria\'s average grid uptime for commercial enterprises is 4–6 hours/day in most states outside Lagos. This mandates hybrid power (grid + solar + battery) at every 5G site, adding approximately $35,000–47,000 per site in capex and $8,000/year in incremental opex.',
      },
      {
        heading: 'Urban Deployment Outlook',
        content:
          'Lagos, Abuja, and Port Harcourt are the credible first-phase 5G markets. MTN\'s 5G commercial service in Lagos (launched July 2022) covers approximately 15% of the metropolitan area. Full Lagos metro coverage is projected for Q2 2026 at current rollout pace. Abuja coverage is tracking faster — CBN and government precinct density justifies higher ROI per site.',
      },
    ],
    author: 'AI Generated',
    readTimeMinutes: 7,
    isSaved: false,
  },
  {
    id: 'lib-009',
    title: 'Weekly Intelligence Report — W4 January 2025',
    subtitle: 'Nigeria Market Intelligence · 11 signals synthesised',
    domain: 'Cross-Sector',
    type: 'weekly-report',
    publishedAt: '2025-01-26T07:00:00Z',
    relativeDate: 'Jan 26, 2025',
    confidence: 88,
    tags: ['#Weekly', '#Macro', '#NBS', '#CPI'],
    summary:
      'The final week of January delivered the NBS CPI print (33.09% in December), Zenith Bank\'s full-year 2024 results, and a key pronouncement from the Ondo State Agricultural Investment Summit. Price stability signals are constructive, while banking sector profitability remains robust under the high-rate environment.',
    sections: [
      {
        heading: 'Executive Summary',
        content:
          'W4 January confirms the disinflation trend with the December CPI at 33.09%. Zenith Bank posted FY 2024 PAT of ₦863B (+127% YoY), primarily on NIM expansion under the high-rate regime. The Ondo State summit announced ₦18B in foreign agri-investments. Two tech IPOs are in active preparation for H2 2025.',
      },
      {
        heading: 'Key Signals',
        content:
          'NBS CPI December 2024: 33.09% (prev: 34.80%) — disinflation confirmed. Zenith Bank FY 2024 PAT: ₦863B (+127% YoY). Ondo Agricultural Investment Summit: ₦18B commitment from four investors. Access Bank raises $1.5B Eurobond at 9.125% — oversubscribed 3.2×. PalmPay announces 35M registered users, targeting 50M by Q4 2025.',
      },
    ],
    author: 'Cogent Research',
    readTimeMinutes: 5,
    isSaved: false,
  },
  {
    id: 'lib-010',
    title: 'Port Harcourt: Downstream Energy & Logistics Investment Thesis',
    subtitle: 'Refinery commercialisation and e-commerce basket growth dynamics',
    domain: 'Energy',
    type: 'ai-brief',
    publishedAt: '2025-01-18T10:00:00Z',
    relativeDate: 'Jan 18, 2025',
    confidence: 83,
    tags: ['#Energy', '#PortHarcourt', '#Logistics', '#Investment'],
    summary:
      'Port Harcourt\'s economic landscape is shifting materially as Dangote Refinery\'s commercial operation reduces logistics cost premiums previously embedded in the oil-producing South-South economy. Combined with growing e-commerce basket volume and downstream energy services demand, PH is emerging as a high-conviction logistics and digital commerce hub.',
    sections: [
      {
        heading: 'Dangote Refinery Proximity Effect',
        content:
          'Port Harcourt sits 278 km from the Dangote Lekki complex — shorter than the Kano (824 km) or Maiduguri (1,212 km) supply corridors. Logistics operators in PH access Dangote PMS at depot prices, reducing average fleet fuel costs by 28% versus the pre-Dangote import-parity baseline. E-commerce last-mile cost per delivery in PH fell from $3.20 to $2.87 in Q4 2024.',
      },
      {
        heading: 'E-Commerce Basket Growth',
        content:
          'Jumia PH order volumes grew 41% YoY in Q4 2024 — outpacing the Lagos metropolitan 29% growth rate. Average order value (AOV) in PH grew 18% to $34.20, driven by electronics, consumer goods, and health/beauty. This AOV trajectory makes PH an increasingly attractive market for premium category expansion.',
      },
      {
        heading: 'Downstream Energy Services',
        content:
          'The planned NLNG Train 7 construction restart creates a secondary services market: accommodation logistics, catering, specialised equipment transport, and safety services. Combined estimated direct-procurement spend over a 4-year construction cycle: $1.4B. Local content requirements mandate at least 45% domestic procurement — creating a $630M+ addressable market.',
      },
    ],
    author: 'AI Generated',
    readTimeMinutes: 5,
    isSaved: false,
  },
  {
    id: 'lib-011',
    title: 'Healthcare Sector: Private Investment & Infrastructure Gaps',
    subtitle: 'Analysis of capital flows and underserved population density',
    domain: 'Healthcare',
    type: 'sector-review',
    publishedAt: '2025-01-05T09:00:00Z',
    relativeDate: 'Jan 5, 2025',
    confidence: 73,
    tags: ['#Healthcare', '#Infrastructure', '#PrivateCapital', '#Nigeria'],
    summary:
      'Nigeria\'s healthcare sector is experiencing a bifurcation: premium private facilities serving the top 5% of earners (and diaspora medical tourism reversals) are well-capitalised, while secondary and tertiary public healthcare infrastructure suffers from a ₦2.1T annual funding deficit. This analysis maps investment gaps and identifies high-yield entry points for private capital.',
    sections: [
      {
        heading: 'Sector Investment Gap',
        content:
          'Nigeria\'s public healthcare expenditure of 3.8% of GDP is below the WHO Abuja Declaration target of 15%. The ₦2.1T financing gap is most acute in diagnostics (CT/MRI coverage), emergency trauma care, and reproductive health. The World Bank\'s Nigeria HOPE-II facility ($750M) targets precisely these tertiary care gaps, with disbursement expected through 2027.',
      },
      {
        heading: 'Private Investment Momentum',
        content:
          'Helios Investment Partners\' stake in HealthPlus pharmacy chain and Verod Capital\'s investment in Lifestores Healthcare reflect growing private equity confidence. The Nigerian Sovereign Investment Authority (NSIA) has committed ₦30B to the NSIA Hospital portfolio — a PPP model building 1,000-bed flagship facilities in Lagos, Abuja, and Kano.',
      },
      {
        heading: 'Pharmaceutical Manufacturing',
        content:
          'Emzor Pharmaceutical, Fidson Healthcare, and May & Baker are all in capacity expansion phases — benefiting from naira depreciation making imports less competitive and the Government\'s 2024 import substitution directive for essential medicines. Nigeria currently imports 70% of pharmaceutical inputs; the government target is 40% domestic sourcing by 2030.',
      },
    ],
    author: 'Cogent Research',
    readTimeMinutes: 6,
    isSaved: true,
  },
  {
    id: 'lib-012',
    title: 'Consumer Goods: Pricing Power & Brand Resilience Analysis',
    subtitle: 'FMCG sector response to cost-push inflation — Q3/Q4 2024',
    domain: 'Consumer',
    type: 'deep-analysis',
    publishedAt: '2024-12-28T08:00:00Z',
    relativeDate: 'Dec 28, 2024',
    confidence: 85,
    tags: ['#Consumer', '#FMCG', '#Pricing', '#Inflation'],
    summary:
      'Nigeria\'s FMCG sector demonstrated selective pricing power in H2 2024, with category divergence emerging between necessity goods (strong pass-through) and discretionary consumer products (volume sacrifice for margin preservation). This analysis examines 12 listed and unlisted consumer companies\' pricing strategies and equity implications.',
    sections: [
      {
        heading: 'Pricing Power by Category',
        content:
          'Necessity goods (cooking oil, flour, noodles) successfully passed through 45–62% of input cost inflation. Discretionary goods (carbonated drinks, snacks, premium toiletries) sacrificed 8–15% volume to avoid full pass-through. Unilever Nigeria\'s home care segment passed 58% of cost, while its personal care segment held price and absorbed a 12% volume decline.',
      },
      {
        heading: 'Sachet Economy Dynamics',
        content:
          'Nigeria\'s sachet economy — the disaggregation of products into ₦50–₦200 individual-use units — provided a critical demand maintenance mechanism. Consumer brands that introduced sub-₦100 SKUs in Q3 2024 maintained volume at the expense of GMV per transaction. Indomie launched a ₦100 "Gidi Pack" targeting daily wage consumers — it contributed 12% of Q4 unit sales.',
      },
      {
        heading: 'Equity Implications',
        content:
          'Nestle Nigeria (NESF), Unilever Nigeria (UNILEVER), and PZ Cussons Nigeria (PZ) reflect different strategic postures. NESF prioritised FX loss provisioning, impairing 2024 EPS but cleaning the balance sheet. UNILEVER repatriated significant naira balances following NAFEM reform — recording a one-time FX gain. PZ\'s parent company announced a potential divestiture from West African operations — a significant sector signal.',
      },
    ],
    author: 'AI Generated',
    readTimeMinutes: 6,
    isSaved: false,
  },
]

const SAVED_BRIEFS_STORAGE_KEY = 'cogent-library-saved-briefs'
// ── Map backend brief to frontend LibraryBrief type ─────────────────────────

function buildSectionsFromBody(body: Record<string, unknown>): LibrarySection[] {
  const brief = normalizeIntelligenceBrief(body)
  const sections: LibrarySection[] = []

  const executiveLines = [
    brief.executive_summary.bottom_line,
    brief.executive_summary.why_it_matters,
    ...brief.executive_summary.insights.map((insight) => {
      const refs = insight.signal_refs.length > 0 ? ` [${insight.signal_refs.join(', ')}]` : ''
      return `${insight.text}${refs}`
    }),
  ].filter((line): line is string => Boolean(line))

  if (executiveLines.length > 0) {
    sections.push({ heading: 'Executive Summary', content: executiveLines.join('\n\n') })
  }

  const questionLines = [
    brief.key_intelligence_questions.what_is_happening ? `What is happening: ${brief.key_intelligence_questions.what_is_happening}` : null,
    brief.key_intelligence_questions.why_is_it_happening ? `Why it is happening: ${brief.key_intelligence_questions.why_is_it_happening}` : null,
    brief.key_intelligence_questions.what_will_happen_next ? `What happens next: ${brief.key_intelligence_questions.what_will_happen_next}` : null,
    brief.key_intelligence_questions.impact_on_organization ? `Impact: ${brief.key_intelligence_questions.impact_on_organization}` : null,
  ].filter((line): line is string => Boolean(line))

  if (questionLines.length > 0) {
    sections.push({ heading: 'Key Intelligence Questions', content: questionLines.join('\n\n') })
  }

  if (brief.situation_overview.overview) {
    sections.push({ heading: 'Situation Overview', content: brief.situation_overview.overview })
  }

  const evidenceLines = brief.signals_and_indicators.signal_evidence.map((item) => (
    `${item.signal_ref}: ${item.signal_title}\n${item.contribution}`
  ))
  if (evidenceLines.length > 0) {
    sections.push({ heading: 'Signal Evidence', content: evidenceLines.join('\n\n') })
  }

  if (brief.analysis.patterns_detected.length > 0) {
    sections.push({ heading: 'Analysis', content: brief.analysis.patterns_detected.join('\n\n') })
  }

  const actionLines = [
    ...brief.recommended_actions.immediate.map((action, index) => `Immediate ${index + 1}: ${action}`),
    ...brief.recommended_actions.strategic.map((action, index) => `Strategic ${index + 1}: ${action}`),
  ]
  if (actionLines.length > 0) {
    sections.push({ heading: 'Recommended Actions', content: actionLines.join('\n') })
  }

  if (brief.outlook) {
    sections.push({ heading: 'Outlook', content: brief.outlook })
  }

  if (brief.limitations.length > 0) {
    sections.push({ heading: 'Limitations', content: brief.limitations.join('\n') })
  }

  return sections
}

function mapBackendBrief(raw: BriefResponse): LibraryBrief {
  const body = raw.body_json ?? {}
  const normalizedBrief = normalizeIntelligenceBrief(body, {
    headline: raw.title,
    summary: raw.bluf,
    domain: typeof body.domain === 'string' ? body.domain : null,
    outlook: raw.outlook,
    decisionLens: raw.decision_lens,
  })
  const sections = buildSectionsFromBody(body)
  const tags = normalizedBrief.tags.length > 0
    ? normalizedBrief.tags
    : raw.brief_type ? [`#${raw.brief_type}`] : []

  return {
    id: raw.id,
    title: raw.title,
    subtitle: normalizedBrief.situation_overview.topic ?? undefined,
    domain: mapBriefDomain(normalizedBrief.domain ?? undefined),
    type: mapBriefType(raw.brief_type),
    publishedAt: raw.created_at,
    relativeDate: new Date(raw.created_at).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }),
    confidence: normalizedBrief.metadata.confidence_level === 'Verified'
      ? 95
      : normalizedBrief.metadata.confidence_level === 'High'
        ? 85
        : normalizedBrief.metadata.confidence_level === 'Medium'
          ? 72
          : 58,
    tags,
    summary: normalizedBrief.executive_summary.bottom_line ?? raw.bluf ?? '',
    sections,
    author: (normalizedBrief.author as LibraryBrief['author']) ?? 'AI Generated',
    readTimeMinutes: normalizedBrief.read_time,
    isSaved: false,
  }
}

function mapBriefDomain(d: string | undefined): LibraryBriefDomain {
  const valid: LibraryBriefDomain[] = [
    'Agriculture', 'Finance', 'Energy', 'Technology',
    'Consumer', 'Healthcare', 'Cross-Sector', 'Macro',
  ]
  if (d && valid.includes(d as LibraryBriefDomain)) return d as LibraryBriefDomain
  return 'Cross-Sector'
}

function mapBriefType(t: string | undefined): LibraryBriefType {
  const valid: LibraryBriefType[] = ['ai-brief', 'weekly-report', 'deep-analysis', 'sector-review']
  if (t && valid.includes(t as LibraryBriefType)) return t as LibraryBriefType
  return 'ai-brief'
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useLibrary() {
  const [baseBriefs, setBaseBriefs] = useState<LibraryBrief[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [filterDomain, setFilterDomain] = useState<LibraryFilterDomain>('All')
  const [filterType, setFilterType] = useState<LibraryFilterType>('All')
  const [sortKey, setSortKey] = useState<LibrarySortKey>('date')
  const [savedBriefs, setSavedBriefs] = useState<Set<string>>(
    () => {
      if (typeof window === 'undefined') {
        return new Set()
      }

      try {
        const raw = window.localStorage.getItem(SAVED_BRIEFS_STORAGE_KEY)
        if (!raw) {
          return new Set()
        }
        const ids = JSON.parse(raw)
        return Array.isArray(ids) ? new Set<string>(ids.filter((value): value is string => typeof value === 'string')) : new Set()
      } catch {
        return new Set()
      }
    }
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // Pagination
  const PAGE_SIZE = 20
  const [skip, setSkip]   = useState(0)
  const [total, setTotal] = useState(0)
  const [isLoadingMore, setIsLoadingMore] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    try {
      window.localStorage.setItem(SAVED_BRIEFS_STORAGE_KEY, JSON.stringify(Array.from(savedBriefs)))
    } catch {
      // Ignore persistence failures and keep the in-memory state.
    }
  }, [savedBriefs])

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await fetchBriefsList({ limit: PAGE_SIZE, skip: 0 })
      if (data?.items?.length) {
        setBaseBriefs(data.items.map(mapBackendBrief))
        setTotal(data.total ?? data.items.length)
        setSkip(data.items.length)
      } else {
        setBaseBriefs([])
        setTotal(0)
        setSkip(0)
      }
    } catch (err) {
      setBaseBriefs([])
      setTotal(0)
      setSkip(0)
      setError(friendlyErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [PAGE_SIZE])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const loadMore = useCallback(async () => {
    if (isLoadingMore || skip >= total) return
    setIsLoadingMore(true)
    try {
      const data = await fetchBriefsList({ limit: PAGE_SIZE, skip })
      if (data?.items?.length) {
        setBaseBriefs(prev => [...prev, ...data.items.map(mapBackendBrief)])
        setSkip(prev => prev + data.items.length)
        setTotal(data.total ?? total)
      }
    } catch (err) {
      setError(friendlyErrorMessage(err))
    } finally {
      setIsLoadingMore(false)
    }
  }, [PAGE_SIZE, isLoadingMore, skip, total])

  const loadBriefDetail = useCallback(async (briefId: string) => {
    const detail = await getBrief(briefId)
    return mapBackendBrief(detail)
  }, [])

  const toggleSave = (id: string) => {
    setSavedBriefs(prev => {
      const next = new Set(prev)
      if (next.has(id)) { next.delete(id) } else { next.add(id) }
      return next
    })
  }

  const filtered = useMemo(() => {
    let list = baseBriefs.map(b => ({ ...b, isSaved: savedBriefs.has(b.id) }))

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      list = list.filter(
        b =>
          b.title.toLowerCase().includes(q) ||
          b.summary.toLowerCase().includes(q) ||
          b.tags.some(t => t.toLowerCase().includes(q))
      )
    }

    if (filterDomain !== 'All') {
      list = list.filter(b => b.domain === filterDomain)
    }

    if (filterType !== 'All') {
      list = list.filter(b => b.type === filterType)
    }

    switch (sortKey) {
      case 'date':
        list = list.sort((a, b) => b.publishedAt.localeCompare(a.publishedAt))
        break
      case 'confidence':
        list = list.sort((a, b) => b.confidence - a.confidence)
        break
      case 'readTime':
        list = list.sort((a, b) => a.readTimeMinutes - b.readTimeMinutes)
        break
      case 'title':
        list = list.sort((a, b) => a.title.localeCompare(b.title))
        break
    }

    return list
  }, [searchQuery, filterDomain, filterType, sortKey, savedBriefs, baseBriefs])

  const weeklyReports = useMemo(() =>
    filtered.filter(b => b.type === 'weekly-report'), [filtered])

  const allDomains: LibraryFilterDomain[] = [
    'All', 'Agriculture', 'Finance', 'Energy', 'Technology',
    'Consumer', 'Healthcare', 'Cross-Sector', 'Macro',
  ]
  const allTypes: LibraryFilterType[] = [
    'All', 'ai-brief', 'weekly-report', 'deep-analysis', 'sector-review',
  ]

  const totalSaved = savedBriefs.size

  return {
    briefs: filtered,
    weeklyReports,
    loading,
    error,
    refresh,
    searchQuery,
    setSearchQuery,
    filterDomain,
    setFilterDomain,
    filterType,
    setFilterType,
    sortKey,
    setSortKey,
    toggleSave,
    totalSaved,
    allDomains,
    allTypes,
    totalCount: baseBriefs.length,
    // Pagination
    total,
    hasMore: skip < total,
    isLoadingMore,
    loadMore,
    loadBriefDetail,
  }
}
