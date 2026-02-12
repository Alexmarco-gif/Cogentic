# Agriculture & Agritech Domain Implementation Plan

**Document Version:** 1.0
**Date:** February 12, 2026
**Status:** 🔵 PLANNING
**Phase:** Phase 3 Extension — Domain Addition

---

## 1. Executive Summary

This document outlines the implementation plan for adding **Agriculture & Agritech (AgriBusiness)** as the 5th industry vertical to the Enterprise Signal Intelligence Platform (ESIP). Agriculture employs a large segment of the population globally (particularly in Nigeria and emerging markets) and presents strong potential for data-driven insights across yield optimization, supply chain efficiency, and market dynamics.

### 1.1 Strategic Rationale

| Factor | Impact on ESIP |
|--------|---------------|
| **Population Impact** | Agriculture employs 35-40% of Nigeria's workforce, making it a critical economic sector |
| **Data Maturity Gap** | Fragmented, analog systems create opportunity for intelligence layer |
| **Decision Complexity** | Weather, soil, pricing, logistics variables create high signal value |
| **Regional Focus** | Aligns with ESIP's Nigeria-first, high-depth regional intelligence strategy |
| **Cross-Industry Synergy** | Overlaps with FMCG (supply chain), Fintech (agri-lending), Infrastructure (logistics) |

### 1.2 Core Signal Categories

Based on user requirements, Agriculture signals will focus on **7 core categories**:

1. **Yield Forecasting** - Crop production predictions based on historical data, weather, soil
2. **Weather Patterns** - Rainfall, temperature, drought/flood risk, seasonal shifts
3. **Soil Health** - Nutrient levels, pH, degradation, fertilizer needs
4. **Market Pricing** - Commodity prices, price trends, arbitrage opportunities
5. **Supply Chain Inefficiencies** - Logistics delays, storage losses, transport bottlenecks
6. **Price Volatility** - Commodity price fluctuations, risk prediction
7. **Supply Chain Bottlenecks** - Infrastructure gaps, border delays, processing capacity

---

## 2. Industry Taxonomy Structure

### 2.1 Root Industry

**Name:** Agriculture & Agritech
**Slug:** `agriculture-agritech`
**Description:** Signal intelligence for agricultural production, agribusiness operations, supply chain optimization, and agritech innovation across crop farming, livestock, aquaculture, and forestry.

### 2.2 Sub-Verticals (Child Industries)

| Slug | Name | Description |
|------|------|-------------|
| `crop-farming` | Crop Farming & Horticulture | Grains, vegetables, fruits, cash crops (cocoa, coffee, rubber) |
| `livestock-dairy` | Livestock & Dairy | Cattle, poultry, goat/sheep, dairy production |
| `agritech-innovation` | Agritech & Innovation | Precision agriculture, IoT, drones, satellite monitoring, fintech for farmers |
| `supply-chain-logistics` | Agricultural Supply Chain & Logistics | Post-harvest handling, cold storage, transportation, commodity trading |
| `agri-inputs` | Agricultural Inputs & Services | Seeds, fertilizers, pesticides, equipment, veterinary services |
| `aquaculture-fisheries` | Aquaculture & Fisheries | Fish farming, shrimp, tilapia, coastal fisheries |

---

## 3. Entity Model Design

### 3.1 Entity Types

Following the existing pattern (`entity_type` field), Agriculture domain will use:

| Entity Type | Examples | Description |
|-------------|----------|-------------|
| `company` | Flour Mills, Dangote Sugar, Wacot Rice, Farmcrowdy | Agricultural companies, processors, cooperatives |
| `product` | Rice (Ofada, Basmati), Cassava flour, Palm oil, Cocoa beans | Crops, commodities, processed goods |
| `person` | Agricultural ministers, farm association leaders, agritech founders | Key decision-makers, influencers |
| `brand` | Golden Penny, Mama Gold Rice, Dangote Farms | Consumer-facing agricultural brands |
| `infrastructure` | Silos, cold storage facilities, irrigation systems, farm clusters | Physical assets tracked for capacity signals |
| `cooperative` | Farmers associations, commodity boards, export cooperatives | Organizational entities |

**New entity_type values to add:** `infrastructure`, `cooperative`

### 3.2 Sample Entities (Top 20 for Seeding)

#### Companies
1. Flour Mills of Nigeria
2. Dangote Sugar Refinery
3. Olam Agri (Nigeria)
4. Wacot Rice (Argungu)
5. Presco Plc (Palm Oil)
6. Farmcrowdy (Agritech)
7. ThriveAgric (Agritech)
8. Babban Gona (Farmer network)

#### Products (Commodities)
9. Rice (local varieties: Ofada, Abakaliki)
10. Cassava (fresh & processed)
11. Palm Oil (crude & refined)
12. Cocoa Beans
13. Maize (yellow & white)
14. Yam
15. Tomatoes (fresh)
16. Poultry (broilers, layers)

#### Infrastructure
17. Anchor Borrowers' Program (ABP)
18. Lagos Commodities & Futures Exchange (LCFE)
19. Federal Ministry of Agriculture & Rural Development
20. National Agricultural Land Development Authority (NALDA)

---

## 4. Signal Contract Design (70 Contracts)

### 4.1 Contract Distribution by Source Type

Following the established pattern (api, scraper, rss, social):

| Source Type | Count | Examples |
|-------------|-------|----------|
| **API** | 15 | Weather APIs (NIMET, OpenWeather), Commodity price APIs (LCFE, CBN), Satellite (Sentinel Hub) |
| **RSS** | 20 | Agricultural news (AgricNews, BusinessDay), Government gazettes, FAO reports |
| **Scraper** | 25 | Market price boards, government portals, research publications, auction sites |
| **Social** | 10 | Twitter (farm associations, agric ministers), WhatsApp groups (via web scraping), farmer forums |

**Total:** 70 signal contracts

### 4.2 Schedule Tier Breakdown

| Tier | Interval | Count | Use Cases |
|------|----------|-------|-----------|
| **realtime** | 15 min | 10 | Weather alerts, market price updates, emergency notices |
| **standard** | 1 hour | 30 | Commodity prices, news, social sentiment |
| **slow** | 6 hours | 20 | Soil reports, yield forecasts, research publications |
| **daily** | 24 hours | 10 | Government policies, weekly market bulletins, satellite imagery |

### 4.3 Detailed Signal Contracts (Sample 20 of 70)

#### Weather Patterns (10 contracts)
| # | Contract Name | Source Type | URL/API | Schedule Tier | Signal Type |
|---|---------------|-------------|---------|---------------|-------------|
| 1 | NIMET Daily Weather Forecast | API | nimet.gov.ng/api | realtime | weather |
| 2 | NIMET Rainfall Data (Historical) | API | nimet.gov.ng/api/rainfall | daily | weather |
| 3 | OpenWeather Nigeria Agricultural Zones | API | api.openweathermap.org | standard | weather |
| 4 | Drought Risk Monitor (FAO) | scraper | fao.org/drought-monitor | slow | weather |
| 5 | Seasonal Weather Predictions (CBN Climate Desk) | scraper | cbn.gov.ng/climate | daily | weather |
| 6 | Flooding Alerts (NEMA) | rss | nema.gov.ng/alerts | realtime | weather |
| 7 | Harmattan Impact on Agriculture | social | Twitter @NIMET_ng | standard | weather |
| 8 | Sentinel-2 Satellite Vegetation Index | API | Sentinel Hub API | slow | weather |
| 9 | Temperature Extremes & Crop Stress | scraper | nigerian-meteorological.org | standard | weather |
| 10 | Irrigation Water Availability | scraper | irrigation-boards.gov.ng | slow | weather |

#### Market Pricing (10 contracts)
| # | Contract Name | Source Type | URL/API | Schedule Tier | Signal Type |
|---|---------------|-------------|---------|---------------|-------------|
| 11 | Lagos Commodity Exchange Spot Prices | API | lcfe.ng/api/prices | realtime | market |
| 12 | CBN Agricultural Commodity Price Index | scraper | cbn.gov.ng/agric-prices | standard | market |
| 13 | Open Market Rice Prices (Mile 12, Dawanau) | scraper | Mile 12 market boards | standard | market |
| 14 | Palm Oil Export Prices (FOB) | scraper | export-boards.ng | daily | market |
| 15 | Cocoa Spot Prices (Cocoa Board) | API | cocoa-board.ng/api | standard | market |
| 16 | Maize Wholesale Prices (Northern States) | scraper | State market boards | standard | market |
| 17 | Tomato Price Volatility (Kano Market) | scraper | kano-agric-market.ng | standard | market |
| 18 | Yam Festival Pricing Signals | social | Twitter, Facebook farmer groups | standard | market |
| 19 | Fertilizer Price Trends | scraper | fertilizer-distributors.ng | slow | market |
| 20 | Commodity Futures (LCFE) | API | lcfe.ng/api/futures | standard | market |

#### Yield Forecasting (10 contracts)
| # | Contract Name | Source Type | URL/API | Schedule Tier | Signal Type |
|---|---------------|-------------|---------|---------------|-------------|
| 21 | FMARD Crop Production Forecasts | scraper | fmard.gov.ng/forecasts | daily | production |
| 22 | NASC Seed Distribution Data | scraper | nasc.gov.ng/distribution | slow | production |
| 23 | Fertilizer Application Rates (ABP) | scraper | abp-nigeria.ng/fertilizer | slow | production |
| 24 | Harvest Calendar Tracker | scraper | agric-extension.gov.ng | daily | production |
| 25 | Planting Season Commencement Reports | rss | Agricultural state bulletins | slow | production |
| 26 | Rice Mill Capacity Utilization | scraper | Rice processors association | slow | production |
| 27 | NDVI Crop Health Monitoring (Satellite) | API | Sentinel Hub | slow | production |
| 28 | Pest & Disease Outbreak Reports | rss | FMARD plant health alerts | standard | production |
| 29 | Irrigation Project Completion | scraper | Water resources ministry | daily | production |
| 30 | Farm Mechanization Adoption Signals | social | Agritech Twitter, LinkedIn | standard | production |

#### Supply Chain & Logistics (10 contracts)
| # | Contract Name | Source Type | URL/API | Schedule Tier | Signal Type |
|---|---------------|-------------|---------|---------------|-------------|
| 31 | Port Congestion (Apapa, Tin Can) | scraper | ports.gov.ng/status | realtime | logistics |
| 32 | Cold Storage Availability | scraper | cold-chain-ng.com | standard | logistics |
| 33 | Border Crossing Delays (Benin, Niger) | scraper | customs.gov.ng/borders | standard | logistics |
| 34 | Trucking Rates (Farm to Market) | scraper | Truckers association | standard | logistics |
| 35 | Post-Harvest Loss Reports | rss | FMARD post-harvest | slow | logistics |
| 36 | Warehouse Receipt System Status | API | AFEX warehouse API | standard | logistics |
| 37 | Railway Freight Capacity (Agric Commodities) | scraper | nrc.gov.ng/freight | daily | logistics |
| 38 | Fuel Price Impact on Transportation | scraper | PPPRA, NNPC | standard | logistics |
| 39 | SiloCapacity & Grain Storage | scraper | Strategic Grain Reserve | slow | logistics |
| 40 | Export Documentation Delays | scraper | Export promotion council | standard | logistics |

#### Soil Health (5 contracts)
| # | Contract Name | Source Type | URL/API | Schedule Tier | Signal Type |
|---|---------------|-------------|---------|---------------|-------------|
| 41 | National Soil Survey Results | scraper | soil-survey.gov.ng | daily | environmental |
| 42 | Fertilizer Recommendations by Zone | scraper | FEPSAN.ng | slow | environmental |
| 43 | Soil Degradation Risk Maps | scraper | FAO soil portal | slow | environmental |
| 44 | pH & Nutrient Testing Services | scraper | Agric extension services | slow | environmental |
| 45 | Organic Matter Content Trends | rss | Research institutions | daily | environmental |

#### Regulatory & Policy (10 contracts)
| # | Contract Name | Source Type | URL/API | Schedule Tier | Signal Type |
|---|---------------|-------------|---------|---------------|-------------|
| 46 | Agricultural Policy Updates (FMARD) | rss | fmard.gov.ng/policies | daily | regulatory |
| 47 | Import/Export Ban Announcements | scraper | Federal Gazette | realtime | regulatory |
| 48 | Anchor Borrowers' Program Updates | scraper | cbn.gov.ng/abp | slow | regulatory |
| 49 | Land Tenure & Allocation Policies | scraper | Land use ministry | daily | regulatory |
| 50 | Subsidy Program Announcements | rss | FMARD bulletins | standard | regulatory |
| 51 | Agricultural Credit Schemes (BOA, BOI) | scraper | Development banks | slow | regulatory |
| 52 | Export Incentive Programs | scraper | NEPC.gov.ng | slow | regulatory |
| 53 | Seed Certification Standards (NASC) | scraper | nasc.gov.ng/standards | daily | regulatory |
| 54 | Pesticide/Herbicide Approvals | scraper | NAFDAC agric portal | slow | regulatory |
| 55 | State Agricultural Budgets | scraper | State budget offices | daily | regulatory |

#### Agritech & Innovation (10 contracts)
| # | Contract Name | Source Type | URL/API | Schedule Tier | Signal Type |
|---|---------------|-------------|---------|---------------|-------------|
| 56 | Agritech Startup Funding Announcements | social | Twitter, TechCabal | standard | technology |
| 57 | Precision Agriculture Tool Adoption | scraper | Agritech company blogs | standard | technology |
| 58 | Drone Usage in Nigerian Farms | social | LinkedIn agritech groups | standard | technology |
| 59 | IoT Sensor Deployments | scraper | Agritech case studies | slow | technology |
| 60 | Mobile USSD Agric Services Usage | scraper | Telco reports | slow | technology |
| 61 | Farmer Digital Literacy Programs | rss | NGO bulletins | slow | technology |
| 62 | Satellite Monitoring Service Launches | rss | Space agency, agritech | standard | technology |
| 63 | Blockchain for Supply Chain (Pilots) | scraper | Tech news, case studies | slow | technology |
| 64 | Agri-Fintech Loan Performance | scraper | Farmcrowdy, ThriveAgric reports | slow | technology |
| 65 | Weather Insurance Product Launches | rss | Insurance companies | standard | technology |

#### Social & Market Sentiment (5 contracts)
| # | Contract Name | Source Type | URL/API | Schedule Tier | Signal Type |
|---|---------------|-------------|---------|---------------|-------------|
| 66 | Farmer Association Social Sentiment | social | Twitter @FarmersNigeria | standard | social |
| 67 | Food Security Discussions (Twitter) | social | #FoodSecurity hashtag | standard | social |
| 68 | Market Women Associations (Facebook) | social | Facebook groups | standard | social |
| 69 | Commodity Trader WhatsApp Groups | scraper | Public WhatsApp web | standard | social |
| 70 | University Agricultural Research (Twitter) | social | @IAR_ABU, @UIAgric | standard | social |

---

## 5. Signal Type Taxonomy

### 5.1 New Signal Types for Agriculture

Following the existing `signal_type` field pattern:

| Signal Type | Description | Examples |
|-------------|-------------|----------|
| `weather` | Weather patterns, forecasts, alerts | Rainfall data, drought risk, temperature extremes |
| `market` | Commodity pricing, market dynamics | Spot prices, futures, price volatility |
| `production` | Yield forecasting, crop health | Harvest predictions, NDVI, planting calendars |
| `logistics` | Supply chain, transportation | Port delays, trucking rates, storage capacity |
| `environmental` | Soil health, sustainability | pH levels, nutrient status, degradation risk |
| `regulatory` | Policies, subsidies, trade rules | Import bans, ABP updates, credit schemes |
| `technology` | Agritech adoption, innovation | Precision ag, IoT sensors, fintech |
| `social` | Farmer sentiment, market buzz | Social media mentions, association discussions |

**Note:** Existing signal types may also apply:
- `news` - Agricultural news articles
- `financial` - Agri-lending, investment rounds

---

## 6. Intelligence Briefs (5 Pre-Built)

### 6.1 Brief Catalog

| # | Brief Title | Problem Solved | Confidence | Key Signals |
|---|-------------|----------------|------------|-------------|
| 1 | **Yield Optimization & Weather Risk Monitor** | What's threatening my harvest this season? When should I plant/harvest? | 🟢 Very High | Weather patterns, rainfall forecasts, soil moisture, planting calendar |
| 2 | **Commodity Price Intelligence & Market Timing** | Should I sell now or wait? What's driving price volatility? | 🟢 Very High | Market pricing, futures, supply-demand, export trends |
| 3 | **Supply Chain Efficiency & Bottleneck Detection** | Where is my produce stuck? What's causing post-harvest losses? | 🟢 High | Logistics delays, storage capacity, transportation costs, port congestion |
| 4 | **Agricultural Policy & Subsidy Opportunity Tracker** | What programs can I access? What policy changes affect my operations? | 🟢 Very High | Regulatory updates, subsidy announcements, credit schemes, import/export policies |
| 5 | **Agritech Innovation & Adoption Signals** | What new technologies should I consider? Who's succeeding with precision agriculture? | 🟡 High | Technology adoption, startup funding, pilot programs, case studies |

### 6.2 Brief Structure Example: "Commodity Price Intelligence & Market Timing"

**BLUF (Bottom Line Up Front):**
> Rice prices at Mile 12 market are up 18% week-over-week due to border closure enforcement and harvest delays in Kebbi State. Short-term volatility expected for 2-3 weeks, but prices likely to stabilize as Kano harvest completes.

**Argument + Evidence:**
- **Signal 1:** LCFE spot price for rice +18% (confidence: 0.92) [source: Lagos Commodity Exchange API]
- **Signal 2:** Border closure enforcement at Seme (confidence: 0.88) [source: Nigeria Customs scraper]
- **Signal 3:** Kebbi State flooding delayed harvest by 2 weeks (confidence: 0.85) [source: NIMET weather alerts + farmer association social]
- **Signal 4:** Kano harvest 70% complete, normal timeline (confidence: 0.90) [source: FMARD production forecast]

**Outlook:**
> Expect continued price pressure for 10-14 days. As Kano harvest completes and border smuggling resumes, prices should moderate by 8-12%. Monitor NIMET forecasts for additional flooding in Kebbi.

**Decision Lens:**
- **For Farmers:** Hold inventory if storage permits; sell at peak if cash-flow constrained
- **For Processors:** Secure 30-day forward contracts now; hedge with LCFE futures
- **For Retailers:** Stock 2-week buffer; communicate price increases to customers proactively

---

## 7. Data Model Extensions

### 7.1 Existing Tables (No Changes Required)

All existing tables support Agriculture domain:
- ✅ `industries` - Add Agriculture as 5th root + 6 sub-verticals
- ✅ `entities` - Use existing entity_type field (add `infrastructure`, `cooperative` values)
- ✅ `signal_contracts` - 70 new contracts linking to Agriculture industry_id
- ✅ `signals` - All new agricultural signals use existing schema
- ✅ `intelligence_briefs` - 5 new briefs linking to Agriculture industry_id

### 7.2 Configuration Extensions

**File:** `backend/config.py`

No changes required. Existing ML settings apply to agriculture signals.

**File:** `backend/models/entity.py`

Update `entity_type` validation if strictly enforced:
```python
# Current types: company, product, person, brand
# Add: infrastructure, cooperative
```

**File:** `backend/models/signal.py`

Update `signal_type` validation if strictly enforced:
```python
# Add: weather, market, production, logistics, environmental
```

---

## 8. ML Model Adaptations

### 8.1 Anomaly Detection

**Agriculture-specific features:**
- Seasonal patterns (planting, harvest, rain seasons)
- Price volatility thresholds adjusted for commodity markets
- Weather event clustering (drought, flood, harmattan)

**Implementation:**
- Retrain `anomaly_detector` model with agricultural data
- Add feature: `days_to_harvest`, `rainfall_deviation`, `price_volatility_30d`

### 8.2 Trending Scorer

**Agriculture adaptations:**
- Weight seasonal signals lower (expected annual peaks)
- Boost signals related to policy changes (high impact)
- Consider inter-commodity correlations (rice ↔ maize, cassava ↔ yam)

### 8.3 Confidence Calibrator

**Agriculture signal confidence factors:**
- Government sources: High base confidence (0.85+)
- Market price data: Medium-high (0.80+)
- Social sentiment: Lower base (0.65+), requires corroboration
- Weather forecasts: Confidence decays with time horizon

---

## 9. Entity Resolution Enhancements

### 9.1 Agricultural Entity Aliases

**Example:**
- Entity: "Flour Mills of Nigeria"
  - Aliases: ["FMN", "Flour Mills", "Golden Penny (parent company)"]

- Entity: "Rice (Ofada)"
  - Aliases: ["Ofada rice", "Ofada", "Local rice (brown)", "Abakaliki rice"]

- Entity: "Anchor Borrowers' Program"
  - Aliases: ["ABP", "CBN ABP", "Anchor Borrowers"]

### 9.2 Commodity Standardization

Use industry-standard commodity codes where applicable:
- ISO 4217 for international pricing
- National commodity board codes for local markets

---

## 10. API Endpoint Extensions

### 10.1 New Endpoints (Optional)

Following existing patterns in `backend/api/v1/`:

**Signals by Commodity:**
```python
GET /api/v1/signals/commodity/{commodity_name}
# Returns signals mentioning specific commodity (rice, cocoa, etc.)
```

**Weather Alerts:**
```python
GET /api/v1/signals/weather/alerts
# Returns high-confidence weather signals flagged as critical
```

**Price Volatility Feed:**
```python
GET /api/v1/signals/market/volatility
# Returns signals with high price_volatility scores
```

### 10.2 Existing Endpoints (Work As-Is)

- ✅ `GET /api/v1/signals` - Filter by `signal_type=weather` or `signal_type=market`
- ✅ `GET /api/v1/signals/feed` - Filter by `industry_id` for Agriculture
- ✅ `GET /api/v1/contracts` - List agricultural signal contracts
- ✅ `GET /api/v1/signals/entity/{entity_id}` - Get signals for specific farm, commodity, etc.

---

## 11. Deep Search Enhancements

### 11.1 Agriculture-Specific Query Expansion

**User Query:** "What's affecting rice prices?"

**Expanded Semantically:**
- Rice pricing signals
- Related entities: Flour Mills, Wacot Rice, Mile 12 Market
- Weather signals (rainfall in rice-growing states)
- Logistics signals (border closures, port delays)
- Regulatory signals (import policies, subsidy programs)

### 11.2 Search Result Ranking Adjustments

**Boost factors for Agriculture:**
- Government sources: +20% relevance
- Recent signals (< 7 days): +15% relevance for weather, market
- Multi-source corroboration: +25% relevance

---

## 12. Intelligence Brief Generation

### 12.1 Agriculture Brief System Prompts

**Example for "Commodity Price Intelligence":**

```
You are an agricultural commodity market analyst with deep knowledge of Nigerian agriculture.

Context:
- User wants to understand current price dynamics for [COMMODITY]
- You have access to spot prices, futures, weather forecasts, supply chain signals

Generate a brief that:
1. Identifies primary price drivers (supply, demand, policy, logistics)
2. Quantifies price movements with confidence scores
3. Provides short-term outlook (2-4 weeks)
4. Gives actionable recommendations for farmers, traders, processors

Evidence Requirements:
- Minimum 3 signals with confidence ≥ 0.85
- At least 2 different source types (e.g., API + scraper)
- Recent data (< 7 days old for prices, < 14 days for production forecasts)

Decision Lens:
- Target 3 stakeholder types: Farmers, Processors, Retailers
- Each gets 1-2 specific, actionable recommendations
```

---

## 13. Seeding Data Requirements

### 13.1 Industries Table

**SQL Insert:**
```sql
-- Root industry
INSERT INTO industries (id, name, slug, parent_id, description, metadata)
VALUES (
  gen_random_uuid(),
  'Agriculture & Agritech',
  'agriculture-agritech',
  NULL,
  'Signal intelligence for agricultural production, agribusiness operations, supply chain optimization, and agritech innovation.',
  '{}'
);

-- Sub-verticals (6 total)
-- Example:
INSERT INTO industries (id, name, slug, parent_id, description)
VALUES (
  gen_random_uuid(),
  'Crop Farming & Horticulture',
  'crop-farming',
  (SELECT id FROM industries WHERE slug = 'agriculture-agritech'),
  'Grains, vegetables, fruits, cash crops (cocoa, coffee, rubber)'
);
-- ... repeat for 5 other sub-verticals
```

### 13.2 Entities Table (Top 20)

**Sample SQL:**
```sql
INSERT INTO entities (id, name, entity_type, industry_id, aliases, description)
VALUES
  (gen_random_uuid(), 'Flour Mills of Nigeria', 'company', 
   (SELECT id FROM industries WHERE slug = 'agriculture-agritech'),
   '["FMN", "Flour Mills", "Golden Penny"]',
   'Nigerian food and agro-allied conglomerate'),
  
  (gen_random_uuid(), 'Rice (Ofada)', 'product',
   (SELECT id FROM industries WHERE slug = 'crop-farming'),
   '["Ofada rice", "Ofada", "Local rice"]',
   'Nigerian indigenous short-grain rice variety'),
  
  -- ... repeat for 18 more entities
```

### 13.3 Signal Contracts (70 Contracts)

**Batch Insert Script:**
```python
# backend/scripts/seed_agriculture_contracts.py

contracts = [
    {
        "name": "NIMET Daily Weather Forecast",
        "industry_slug": "agriculture-agritech",
        "source_url": "https://nimet.gov.ng/api/forecast",
        "source_type": "api",
        "schedule_tier": "realtime",
        "refresh_cron": "*/15 * * * *",  # Every 15 min
        "extraction_config": {
            "api_key_env": "NIMET_API_KEY",
            "json_path": "$.data.forecast",
            "fields": ["location", "temperature", "rainfall", "forecast_date"]
        }
    },
    # ... 69 more contracts
]

# Execute via Alembic migration or standalone seed script
```

### 13.4 Intelligence Briefs (5 Briefs)

**SQL Insert:**
```sql
INSERT INTO intelligence_briefs (id, org_id, industry_id, title, brief_type, bluf, body_json, status)
VALUES (
  gen_random_uuid(),
  NULL,  -- Global brief
  (SELECT id FROM industries WHERE slug = 'agriculture-agritech'),
  'Commodity Price Intelligence & Market Timing',
  'pre_built',
  'Track real-time commodity price movements and identify optimal buying/selling windows.',
  '{
    "argument": "Price volatility in agricultural commodities stems from supply shocks, policy changes, and logistics disruptions.",
    "evidence_signals": [],
    "methodology": "Multi-source price aggregation with ML-based volatility prediction"
  }',
  'published'
);
-- ... 4 more briefs
```

---

## 14. Testing Strategy

### 14.1 Signal Acquisition Tests

**Test Coverage:**
- ✅ Weather API fetcher (NIMET, OpenWeather)
- ✅ Market price scraper (LCFE, Mile 12)
- ✅ RSS feed parser (agricultural news)
- ✅ Social mention extractor (Twitter farmer sentiment)

**Test Cases:**
1. Fetch NIMET weather forecast → parse JSON → create Signal with `signal_type=weather`
2. Scrape commodity prices → SHA-256 dedup → confidence scoring
3. Parse RSS feed → extract publication date → set `expires_at` to 90 days
4. Social mention → entity resolution → link to Flour Mills entity

### 14.2 Refinement Pipeline Tests

**Test Coverage:**
- ✅ Embedding generation for agricultural content
- ✅ Entity resolution (commodity names, company names)
- ✅ ML scoring with seasonal patterns
- ✅ Semantic dedup for similar price signals

### 14.3 Brief Generation Tests

**Test Coverage:**
- ✅ Generate "Commodity Price Intelligence" brief with 5 signals
- ✅ Validate BLUF is ≤ 2 sentences
- ✅ Ensure 3+ high-confidence signals (≥ 0.85)
- ✅ Decision Lens has recommendations for 3 stakeholder types

### 14.4 Search Tests

**Test Queries:**
1. "What's happening with rice prices in Nigeria?"
   - Expected: Market signals + weather signals + logistics signals
2. "Cocoa export trends"
   - Expected: Regulatory signals + market signals + price signals
3. "Best time to plant maize this season"
   - Expected: Weather signals + production signals + planting calendar

---

## 15. Implementation Phases

### 15.1 Phase A: Foundation (Week 1)

**Tasks:**
1. Add Agriculture industry to `industries` table (1 root + 6 sub-verticals)
2. Seed 20 core entities (companies, commodities, infrastructure)
3. Create Alembic migration for entity_type enum extension
4. Update documentation (this document + PRDs)

**Deliverable:** Agriculture domain schema ready

### 15.2 Phase B: Signal Contracts (Week 2-3)

**Tasks:**
1. Implement 10 API-based weather contracts (NIMET, OpenWeather)
2. Implement 20 scraper-based market price contracts
3. Implement 10 RSS contracts (news, government bulletins)
4. Configure extraction configs for each contract
5. Test acquisition pipeline with 5 sample contracts

**Deliverable:** 40 of 70 contracts operational

### 15.3 Phase C: Remaining Contracts & Refinement (Week 4)

**Tasks:**
1. Implement remaining 30 contracts (social, logistics, regulatory)
2. Test refinement pipeline with agricultural signals
3. Validate entity resolution for commodities and companies
4. Tune ML scoring for seasonal patterns

**Deliverable:** All 70 contracts live, refinement working

### 15.4 Phase D: Intelligence Briefs (Week 5)

**Tasks:**
1. Generate 5 pre-built brief templates
2. Test brief generation with live signals
3. Validate BLUF, Argument, Decision Lens structure
4. Create refresh schedules for briefs (daily for price, weekly for policy)

**Deliverable:** 5 agricultural briefs published

### 15.5 Phase E: Search & UX Integration (Week 6)

**Tasks:**
1. Test deep search with agricultural queries
2. Add agricultural signal filters to frontend
3. Create industry landing page for Agriculture
4. Add sample queries to onboarding

**Deliverable:** Agriculture domain live in production

---

## 16. Risk Assessment

### 16.1 Data Source Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| NIMET API reliability | Medium | High | Fallback to OpenWeather; cache forecasts |
| Market price data gaps | High | High | Multi-source aggregation (LCFE + scrapers) |
| Government portal downtime | High | Medium | Daily scraping + retry logic |
| Social signal noise | High | Low | Strict confidence thresholds (≥ 0.70) |

### 16.2 Domain-Specific Challenges

| Challenge | Mitigation |
|-----------|------------|
| **Seasonal data patterns** | Train ML models on multi-year agricultural data; flag seasonal anomalies separately |
| **Regional price variations** | Track prices by market location (Mile 12, Dawanau, Kano); entity resolution for markets |
| **Informal market data** | Blend formal (LCFE) + informal (scrapers) sources; weight by confidence |
| **Weather forecast uncertainty** | Confidence decay function: 0.90 (1-day), 0.80 (3-day), 0.70 (7-day) |

---

## 17. Success Metrics

### 17.1 MVP Success Criteria (Post-Launch)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Signal Contracts Live** | 70 of 70 | Count in `signal_contracts` table where `is_active=true` |
| **Signals Acquired (30 days)** | ≥ 5,000 | Count in `signals` table with `industry_id=agriculture` |
| **Average Signal Confidence** | ≥ 0.75 | AVG(confidence) for agricultural signals |
| **Intelligence Briefs Published** | 5 of 5 | Count in `intelligence_briefs` table |
| **Entity Resolution Accuracy** | ≥ 85% | Manual validation of 100 signal-entity links |
| **Search Query Success Rate** | ≥ 80% | Users find relevant results for agricultural queries |

### 17.2 User Adoption Metrics (90 days)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Agricultural Briefs Viewed** | ≥ 500 views | PostHog event tracking |
| **Agricultural Searches** | ≥ 300 searches | Count in `search_queries` table |
| **Signal Detail Views** | ≥ 1,000 views | API endpoint analytics |
| **Return Users (Agriculture)** | ≥ 30% | Users with 2+ visits to agriculture signals |

---

## 18. Next Steps

### 18.1 Pre-Implementation Checklist

- [ ] Review this plan with stakeholders
- [ ] Approve 70 signal contracts list
- [ ] Confirm data source access (NIMET API, LCFE API, etc.)
- [ ] Update PRD (Product Requirements Document)
- [ ] Update Technical Specification Definition
- [ ] Update Implementation Planning WBS
- [ ] Create GitHub issues for 5 implementation phases

### 18.2 Documentation Updates Required

1. **PRD (ESIP).md**
   - Add Agriculture as 5th industry
   - Update signal catalog (280 → 350 signals)
   - Update brief catalog (20 → 25 briefs)

2. **Technical_Specification_Definition.md**
   - Update data models section (entity_type, signal_type enums)
   - Add agricultural signal examples

3. **Implementation_Planning_WBS.md**
   - Add work package: WP-3.X — Agriculture Domain Implementation
   - Break down into 5 phases (A-E)

4. **Phase_0_Exit_Criteria.md**
   - Update to reflect 5 industries (was 4)

---

## 19. Appendix: Sample Data

### 19.1 Sample Weather Signal (JSON)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "contract_id": "NIMET_DAILY_FORECAST_CONTRACT_ID",
  "org_id": null,
  "title": "Heavy Rainfall Warning - Kebbi State",
  "summary": "NIMET forecasts 80-120mm rainfall in Kebbi over next 48 hours. Flooding risk for low-lying rice farms.",
  "raw_content": "{\"location\": \"Kebbi\", \"rainfall_mm\": 100, \"confidence\": 0.88, \"period\": \"48h\"}",
  "extracted_data": {
    "location": "Kebbi State",
    "rainfall_mm": 100,
    "risk_level": "high",
    "affected_crops": ["rice", "maize"]
  },
  "source_url": "https://nimet.gov.ng/api/forecast/2026-02-12",
  "signal_type": "weather",
  "confidence": 0.88,
  "content_hash": "a1b2c3d4e5f6...",
  "fetched_at": "2026-02-12T08:00:00Z",
  "published_at": "2026-02-12T06:00:00Z",
  "expires_at": "2026-05-12T06:00:00Z",
  "embedding": [0.012, -0.034, 0.056, ...],  // 1536 dimensions
  "created_at": "2026-02-12T08:05:00Z",
  "updated_at": "2026-02-12T08:05:00Z"
}
```

### 19.2 Sample Market Signal (JSON)

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "contract_id": "LCFE_RICE_SPOT_PRICE_CONTRACT_ID",
  "org_id": null,
  "title": "Rice Spot Price +18% (Mile 12 Market)",
  "summary": "Local rice prices surged 18% week-over-week due to border enforcement and Kebbi harvest delays.",
  "raw_content": "<html>Rice: ₦45,000/bag (50kg)...</html>",
  "extracted_data": {
    "commodity": "rice",
    "variety": "local",
    "price_ngn": 45000,
    "unit": "50kg bag",
    "market": "Mile 12, Lagos",
    "change_pct": 18,
    "change_period": "week-over-week"
  },
  "source_url": "https://lcfe.ng/prices/rice/2026-02-12",
  "signal_type": "market",
  "confidence": 0.92,
  "content_hash": "b2c3d4e5f6g7...",
  "fetched_at": "2026-02-12T10:00:00Z",
  "published_at": "2026-02-12T09:30:00Z",
  "expires_at": "2026-05-12T09:30:00Z",
  "embedding": [0.023, -0.045, 0.067, ...],
  "created_at": "2026-02-12T10:05:00Z",
  "updated_at": "2026-02-12T10:05:00Z"
}
```

---

**END OF AGRICULTURE DOMAIN IMPLEMENTATION PLAN**

**Next Action:** Await approval to update PRDs and begin Phase A implementation.
