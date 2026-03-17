"""Seed pre-built Nigeria intelligence briefs.

Creates 15 Nigeria-primary IntelligenceBrief records across key sectors.
These are globally visible (org_id=NULL) and serve as Day-1 content for
any org that subscribes to Nigeria coverage.

Run:
    python -m backend.scripts.seed_nigeria_briefs

Options:
    --dry-run    Print what would be created without writing to DB.
"""

import argparse
import asyncio
import logging
from uuid import uuid4

from backend.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Brief definitions — (industry_slug, title, bluf, body_json, outlook, decision_lens)
# ---------------------------------------------------------------------------

BRIEFS: list[dict] = [
    # ── Financial Services / CBN ─────────────────────────────────────
    {
        "industry_slug": "financial-services",
        "title": "CBN Pauses Rate Hikes but Conditions for a Cut Have Not Been Met",
        "bluf": (
            "The Central Bank of Nigeria (CBN) held its benchmark interest rate (MPR) "
            "at 27.25% in February 2026 — but this is not a policy reversal. "
            "The pause is conditional: if the naira weakens sharply or if inflation "
            "stops falling, the CBN will hike again. Businesses that are treating "
            "this pause as the all-clear for cheaper borrowing are mispricing the risk. "
            "A genuine rate cut is only possible in the second half of 2026, and only "
            "if inflation falls below 28% on a sustained basis."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "The CBN's rate pause is driven by falling inflation, not by confidence that the job is done — the bank retains a clear trigger to hike again.",
                    "evidence": [
                        "MPC communiqué February 2026: MPR held at 27.25%, unanimous vote",
                        "NBS CPI January 2026: 33.1% year-on-year, down from a peak of 34.8% in mid-2025",
                        "CBN governor's post-meeting statement cited 'nascent disinflation' not 'achieved disinflation'",
                    ],
                    "objection": "Some analysts argue the 700 basis-point hiking cycle since 2023 has already done enough to anchor expectations and a cut could come as early as Q2 2026.",
                    "rebuttal": "Food inflation is still running at 40.8%, which is the dominant driver of the headline number. Until food prices ease — which requires security improvements in the North, not just monetary policy — the CBN's hands are tied.",
                },
                {
                    "finding": "The exchange rate, not inflation, is the variable that would force the CBN's hand in either direction — a naira weakening past ₦1,700/$ would likely trigger an emergency hike.",
                    "evidence": [
                        "NAFEX official rate: ₦1,590/$ as of March 2026",
                        "Parallel market rate: ₦1,612/$ — premium has compressed to under 2%, the narrowest gap in a decade",
                        "CBN gross external reserves: $37.2 billion (approximately 3.5 months of import cover)",
                        "CBN intervened in the FX market on 7 occasions in Q1 2026 to defend the rate",
                    ],
                    "objection": "The reserves figure looks adequate relative to the IMF's 3-month minimum benchmark.",
                    "rebuttal": "The 3-month benchmark is a floor, not a comfort zone. Nigeria's import bill is heavily energy-linked; an oil price shock below $70 per barrel would drain reserves faster than the headline figure suggests.",
                },
            ],
            "indicators": [
                {
                    "watch": "NBS monthly Consumer Price Index release (published around the 15th of each month)",
                    "confirms_if": "Headline CPI falls below 30% by May 2026, confirming the disinflation trend is structural",
                    "disconfirms_if": "CPI rebounds above 35%, which would signal the rate pause was premature",
                },
                {
                    "watch": "CBN daily NAFEX mid-rate and parallel market rate (abokifx.com)",
                    "confirms_if": "Parallel premium stays below 3% — signals the FX market believes the rate is credible",
                    "disconfirms_if": "Parallel rate diverges past ₦1,700/$, which historically precedes a CBN policy response within 6 weeks",
                },
                {
                    "watch": "CBN Monetary Policy Committee meeting date (next scheduled: May 2026)",
                    "confirms_if": "MPC holds or cuts — confirms cut scenario is on track",
                    "disconfirms_if": "Emergency inter-meeting rate decision, which would signal a crisis",
                },
            ],
        },
        "outlook": (
            "Rates will stay on hold through Q2 2026 unless the naira weakens sharply. "
            "A first cut of 100 basis points (meaning borrowing becomes 1% cheaper) is "
            "possible in H2 2026 — but only if inflation falls below 28% and holds there. "
            "The single biggest risk to this outlook is an oil price collapse below $70 per barrel, "
            "which would weaken the naira, force the CBN to defend the currency, and push any "
            "rate cut off the table entirely."
        ),
        "decision_lens": (
            "If your business has loans in US dollars or other foreign currencies: lock in "
            "your exchange rate now using forward contracts — do not wait for a 'better rate' "
            "that may not come. "
            "If you run a bank: model what happens to your loan book profitability if the CBN "
            "cuts rates by 200 basis points in H2 2026 — your interest income will compress. "
            "If you import goods: the current gap between the official and black-market rate "
            "is unusually narrow. This is a good window to settle outstanding import bills."
        ),
    },
    {
        "industry_slug": "financial-services",
        "title": "Foreign Investors Are Exiting the Nigerian Stock Market — Domestic Buyers Are Absorbing the Selling",
        "bluf": (
            "The Nigerian Exchange (NGX) All-Share Index broke 100,000 points in 2024 and "
            "has since fallen roughly 18% — but the reason matters more than the number. "
            "Foreign portfolio investors (overseas fund managers) have been net sellers for "
            "12 of the last 14 months, pulling dollar capital out. "
            "Nigerian retail investors are buying what the foreigners are selling, which has "
            "slowed the decline but is a structurally weaker support base. "
            "Company earnings look good on paper, but this is largely because the naira "
            "depreciation inflated the naira value of their assets — the underlying "
            "business performance in real terms is more modest. "
            "Do not confuse accounting gains from currency movement with genuine profit growth."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "The NGX's current price level reflects domestic retail sentiment, not foreign institutional confidence — which makes it vulnerable to any negative shock that discourages local buyers.",
                    "evidence": [
                        "NGX All-Share Index: approximately 98,400 points as of March 2026",
                        "Total market capitalisation: approximately ₦57 trillion",
                        "Foreign portfolio investors net-sold in 12 of the last 14 months through February 2026",
                        "Domestic retail investor accounts at NGX grew 22% year-on-year in 2025, now the dominant buyer segment",
                    ],
                    "objection": "A price-to-earnings ratio of approximately 7 times looks cheap compared to peers like Kenya (12x) or South Africa (11x), suggesting the market is undervalued and represents good value for buyers willing to wait.",
                    "rebuttal": "The earnings that underpin that cheap valuation are heavily distorted. Banks and large companies reported naira gains from revaluing their dollar assets after the 2023 naira float — these are one-time accounting items, not recurring business income. Strip them out and the real earnings growth is flat to declining.",
                },
                {
                    "finding": "The banking sector, which drives approximately 35% of the All-Share Index, faces a profit squeeze if the CBN cuts interest rates — meaning the index's biggest component and its catalyst (rate cuts) are pulling in opposite directions.",
                    "evidence": [
                        "Banking sector index weighting: approximately 35% of NGX ASI market capitalisation",
                        "Banks earned record profits in 2024 partly from high-yield government securities at 18–22%",
                        "A CBN rate cut would reduce yields on government bonds, reducing bank interest income",
                        "GTCO, Zenith Bank, and First Bank collectively account for over 50% of banking sector index weight",
                    ],
                    "objection": "Rate cuts could stimulate economic activity and loan growth, which would offset the yield compression impact.",
                    "rebuttal": "Nigeria's loan-to-deposit ratio is structurally low — banks prefer risk-free government paper over commercial loans. A rate cut environment typically takes 18–24 months to translate into meaningful loan book growth large enough to replace lost yield income.",
                },
            ],
            "indicators": [
                {
                    "watch": "NGX daily closing price and daily trading turnover (published by NGX at market close)",
                    "confirms_if": "Daily turnover consistently above ₦15 billion signals sufficient market depth for recovery",
                    "disconfirms_if": "Turnover drops below ₦5 billion on multiple consecutive days — signals thin, illiquid conditions where any large sell order can crash the market",
                },
                {
                    "watch": "Foreign portfolio investment flows — published monthly in CBN economic report",
                    "confirms_if": "Net foreign buying returns for two consecutive months — signals the conditions that drove the exit (naira volatility, FX repatriation difficulty) have been resolved",
                    "disconfirms_if": "Foreign selling accelerates above ₦50 billion per month",
                },
                {
                    "watch": "Brent crude oil price (the primary driver of Nigeria's foreign exchange earnings)",
                    "confirms_if": "Oil holds above $85 per barrel — gives the CBN more FX reserves and reduces the risk premium foreign investors attach to Nigerian assets",
                    "disconfirms_if": "Oil falls below $70 per barrel for more than 30 days — historically triggers naira pressure and FPI exit",
                },
            ],
        },
        "outlook": (
            "The index will likely trade in a range of 90,000 to 105,000 points through mid-2026. "
            "The three catalysts that would break upward from that range are: a CBN rate cut "
            "accompanied by falling inflation, oil prices above $85 per barrel, and a sustained "
            "return of foreign portfolio investors (which requires confidence that dollar profits can "
            "be repatriated without FX friction). None of these are certain within the next six months."
        ),
        "decision_lens": (
            "If you manage an investment portfolio: the consumer staples and telecoms sectors "
            "(food companies, MTN Nigeria, Airtel Africa) offer the most defensive risk profile "
            "— their revenues are in naira and their businesses are relatively insulated from "
            "foreign investor sentiment swings. "
            "Avoid construction and real-estate listed companies until the naira demonstrates "
            "at least two quarters of stability — these sectors are the most exposed to FX "
            "input cost volatility and foreign capital dependency. "
            "If you are a CFO of a company considering an NGX listing: delay until foreign "
            "investor confidence returns — a listing into a domestically-dominated thin market "
            "will achieve a lower valuation than waiting for better conditions."
        ),
    },
    # ── Energy ──────────────────────────────────────────────────────
    {
        "industry_slug": "energy",
        "title": "Dangote Refinery Forces NNPCL to Compete on Price for the First Time — Pump Prices Heading Lower",
        "bluf": (
            "The Dangote Refinery in Lekki began supplying petrol at ₦899/litre ex-depot in late 2025, "
            "roughly ₦150 below the NNPCL pump price. This is the first instance of domestic refinery "
            "competition in Nigeria's history. NNPCL cannot sustain a ₦150 premium indefinitely without "
            "losing market share. If Dangote scales output to 300,000 barrels per day, pump prices should "
            "fall 10–15% in real terms by the end of 2026. The constraint is not competition policy — it "
            "is whether Dangote can actually deliver consistent supply at scale."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "Dangote is selling petrol cheaper than NNPCL and the price gap is wide enough to shift buyer behaviour.",
                    "evidence": [
                        "Dangote Refinery ex-depot price: ₦899/litre (naira-settlement, Feb 2026)",
                        "NNPCL official pump price: ₦1,049/litre (March 2026)",
                        "Major marketers Ardova and Heyden confirmed switching partly to Dangote supply by Q1 2026",
                    ],
                    "objection": "Dangote's output has been inconsistent — supply disruptions have already forced buyers back to NNPCL imports.",
                    "rebuttal": "Consistency risk is real but diminishing. Refinery output has trended upward each quarter. The price gap is large enough that buyers will manage supply risk rather than default to the more expensive option.",
                },
                {
                    "finding": "NNPCL's market position depends entirely on its regulatory waiver, not on price competitiveness.",
                    "evidence": [
                        "NNPCL holds sole importer waiver for PMS under NMDPRA regulations",
                        "NNPCL's cost of imported PMS at ₦1,050+ when crude at $82/bbl and naira at ₦1,590/$",
                        "Private depot operators cannot yet source PMS directly from Dangote at national scale",
                    ],
                    "objection": "NNPCL's waiver gives it regulatory protection that offsets price disadvantage.",
                    "rebuttal": "The CBN and NMDPRA have signalled willingness to liberalise the import waiver if Dangote proves reliable supply. NNPCL's monopoly is a policy choice, not a structural advantage — and that policy is under review.",
                },
                {
                    "finding": "Pump prices will decline only if Dangote's naira-settlement pricing survives the political process.",
                    "evidence": [
                        "Naira-settlement arrangement requires CBN to supply Dangote with dollars for crude purchases at official rate",
                        "CBN extended the arrangement by 12 months in November 2025",
                        "Dangote's refinery crude input target: 300,000 bpd; current achieved: ~180,000 bpd",
                    ],
                    "objection": "Any reversal in the naira-settlement deal immediately wipes out Dangote's price advantage.",
                    "rebuttal": "Reverting to dollar-pricing would expose the government to a political shock from rising pump prices. The arrangement has enough political protection to hold through 2026, though it is not permanent.",
                },
            ],
            "indicators": [
                {
                    "watch": "Dangote Refinery monthly output volumes — available from NMDPRA monthly petroleum data report",
                    "confirms_if": "Output reaches and holds above 250,000 bpd for two consecutive months",
                    "disconfirms_if": "Output falls below 150,000 bpd for more than 30 days, signalling technical or feedstock problems",
                },
                {
                    "watch": "NNPCL vs. Dangote pump price spread — IPMAN and MRS dealer invoices, published weekly by PPPRA",
                    "confirms_if": "Spread narrows to below ₦50/litre, indicating NNPCL has adjusted to compete",
                    "disconfirms_if": "Spread widens beyond ₦200/litre, suggesting NNPCL is repricing upward rather than competing",
                },
                {
                    "watch": "CBN naira-settlement renewal status — CBN official communications and Dangote investor briefings",
                    "confirms_if": "CBN renews naira-settlement for another 12 months before Q3 2026",
                    "disconfirms_if": "CBN declines renewal or introduces dollar billing for crude, eliminating Dangote's pricing floor",
                },
            ],
        },
        "outlook": (
            "If Dangote sustains output above 250,000 bpd through Q3 2026 and the naira-settlement "
            "arrangement holds, pump prices should fall to ₦900–₦950/litre by end-2026. The base case "
            "is price competition without dramatic collapse — NNPCL will adjust rather than withdraw. "
            "The upside scenario (₦800/litre) requires 300,000 bpd output and partial NNPCL import "
            "waiver removal."
        ),
        "decision_lens": (
            "Logistics and manufacturing companies: hold existing generator fuel contracts through Q2 2026 "
            "before renegotiating — wait for Dangote's supply consistency to be established before locking in. "
            "Fuel marketers: begin diligence on Dangote depot offtake agreements now; first-mover pricing "
            "terms will be more favourable than later entrants. "
            "Investors in fuel retail: the margin environment is improving for private marketers as NNPCL "
            "loses pricing power — this is the structurally bullish case for independent retailers."
        ),
    },
    {
        "industry_slug": "energy",
        "title": "Nigeria's Power Grid Is Producing Half Its Installed Capacity — Solar Is Now the Rational Business Choice",
        "bluf": (
            "Nigeria has 8,000 megawatts of installed generation capacity but routinely produces "
            "only 4,000–5,000 megawatts. The gap is caused by gas supply shortfalls, transmission "
            "bottlenecks, and distribution companies that cannot collect enough revenue to pay "
            "generators. The problem is not new equipment — it is financial. NERC's December 2025 "
            "tariff increase brings Band A grid power to ₦240/kilowatt-hour, but this is still "
            "below cost-reflective levels, which means the grid remains structurally underfunded. "
            "Commercial users paying ₦240/kWh on the grid can now get solar-plus-storage at "
            "comparable all-in cost with far greater reliability."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "The grid produces only half its installed capacity because gas supply and payment failures are systemic, not incidental.",
                    "evidence": [
                        "TCN daily generation average: 4,200MW against 8,000MW installed capacity (March 2026)",
                        "Gas supply shortfall: approximately 450mmscfd below contracted volumes (Agip, Shell, NAPIMS data)",
                        "DisCo average collection efficiency: 68% of billed energy (NERC Performance Review Q4 2025)",
                    ],
                    "objection": "Government has announced grid improvement programmes repeatedly — the Siemens Presidential Power Initiative committed $2bn in upgrades.",
                    "rebuttal": "Physical infrastructure investment does not fix the payment chain. GenCos are owed over ₦3.5 trillion in arrears (CBN sector data). Until DisCos collect and pay, generators will not dispatch, regardless of how new the equipment is.",
                },
                {
                    "finding": "The December 2025 tariff increase is too small to make the grid financially viable, which means the current state will persist.",
                    "evidence": [
                        "NERC December 2025 cost-reflective tariff: ₦240/kWh for Band A customers",
                        "Full cost-reflective tariff estimate: ₦380–₦420/kWh (NERC actuarial review 2025)",
                        "Federal government subsidy bill for tariff shortfall: approximately ₦1.8trn annually",
                    ],
                    "objection": "The government might close the tariff gap in future — the direction of travel is towards cost-reflective pricing.",
                    "rebuttal": "The political cost of raising tariffs to ₦400/kWh is prohibitive before the 2027 elections. A gap of ₦160/kWh between actual and required tariffs will not close in the next 18 months.",
                },
                {
                    "finding": "Commercial solar-plus-storage has reached cost parity with Band A grid power on an all-in basis, making off-grid the financially rational decision.",
                    "evidence": [
                        "Commercial rooftop solar+storage all-in cost: ₦210–₦260/kWh over 10-year system life (GOGLA Nigeria estimate)",
                        "Band A grid tariff: ₦240/kWh plus 40% downtime exposure",
                        "C&I solar financing: 18-month payback period now achievable for projects above 100kW (Starsight, Daystar data)",
                    ],
                    "objection": "Solar+storage requires large upfront capital that most businesses cannot access.",
                    "rebuttal": "The market has moved. Lease and power-purchase agreement models from Starsight, CrossBoundary, and Arnergy eliminate upfront capital. The constraint is now procurement speed, not finance.",
                },
            ],
            "indicators": [
                {
                    "watch": "TCN daily generation dispatch figures — published at nisp.org.ng, track 7-day rolling average",
                    "confirms_if": "7-day rolling average exceeds 5,500MW consistently, indicating structural improvement",
                    "disconfirms_if": "Average falls below 3,500MW, indicating worsening gas shortfall or payment-induced curtailment",
                },
                {
                    "watch": "DisCo collection efficiency — NERC quarterly performance review, published 45 days after quarter end",
                    "confirms_if": "Average DisCo collection efficiency rises above 80%, meaning payment flows are improving",
                    "disconfirms_if": "Collection efficiency falls below 60%, signalling accelerated grid deterioration",
                },
                {
                    "watch": "NERC tariff order amendments — NERC official gazette and order register",
                    "confirms_if": "NERC issues a cost-reflective tariff order raising Band A to above ₦350/kWh",
                    "disconfirms_if": "No further tariff increase is issued in 2026, confirming the subsidy persists",
                },
            ],
        },
        "outlook": (
            "Grid generation improvement of 500–800MW is achievable by end-2026 if gas supply constraints "
            "ease and the CBN debt management scheme for GenCo arrears is activated. This will not close "
            "the gap materially. The structural story for the next three years is continued grid "
            "underperformance and accelerating C&I solar adoption. Solar capacity installed in Nigeria "
            "is on track to double between 2024 and 2026."
        ),
        "decision_lens": (
            "Manufacturers and data centre operators: model solar-plus-storage for 80% of base load now — "
            "the economics are there and grid risk is not going away before 2027. "
            "CFOs approving capex: PPA and lease structures mean solar is an operating expense item, "
            "not a capital budget item — reframe the approval process accordingly. "
            "Banks and lenders: C&I solar project finance is the infrastructure lending opportunity of the "
            "next three years — develop standardised lending products for projects of ₦500m–₦5bn."
        ),
    },
    # ── Agriculture ─────────────────────────────────────────────────
    {
        "industry_slug": "agriculture-agritech",
        "title": "Food Prices Are Still Rising Faster Than Wages — Smallholder Farmers Are Losing Ground, Not Gaining It",
        "bluf": (
            "Nigeria's food consumer price index reached 40.8% year-on-year in January 2026. "
            "Retail food prices have more than doubled since mid-2023. This is not primarily a shortage problem — "
            "it is a cost problem. The naira's 70% devaluation since 2023 has inflated the cost of fertiliser, "
            "agrochemicals, and diesel for farm machinery. Smallholder farm-gate prices have risen more slowly "
            "than retail prices, which means traders and intermediaries are capturing the margin, not farmers. "
            "The Anchor Borrowers Programme, which provided below-market credit to smallholders, has been scaled back. "
            "Without a new credit mechanism, the structural food security position continues to deteriorate "
            "even as headline CPI eventually moderates."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "Food price inflation is driven primarily by input cost pass-through from naira devaluation, not by a domestic production collapse.",
                    "evidence": [
                        "NBS Food CPI January 2026: 40.8% year-on-year",
                        "AFEX maize spot price March 2026: ₦580,000/MT — up 120% since June 2023",
                        "Fertiliser cost (NPK 50kg bag): ₦28,000 (March 2026) vs. ₦8,500 (December 2022)",
                        "FMARD 2025 wet-season crop report: production down 8% on flooding, not structural",
                    ],
                    "objection": "Production disruptions from flooding and insecurity in the North-West are partly responsible for price increases.",
                    "rebuttal": "Flooding and insecurity are recurring factors, not the primary driver of the jump since 2023. The timeline aligns with naira depreciation and ABP wind-down, not with harvest failures. Production disruptions explain 15–20% of the price increase at most.",
                },
                {
                    "finding": "Smallholder farmers are not the primary beneficiaries of higher food prices — intermediaries and traders are capturing the margin.",
                    "evidence": [
                        "AFEX farm-gate price survey Q4 2025: maize farm-gate ₦420,000/MT vs. ₦580,000/MT retail",
                        "Margin compression data: smallholder net income per hectare up only 18% y/y despite 120% price increase",
                        "ABP disbursements FY2025: ₦60bn vs. ₦250bn in FY2022 — 76% reduction",
                    ],
                    "objection": "Farmers benefit from higher prices in aggregate.",
                    "rebuttal": "The evidence shows farm-gate and retail prices have diverged — the gap is the trader margin. Farmers who cannot store produce sell at harvest lows. Higher retail prices help organised traders, not smallholders.",
                },
                {
                    "finding": "Without a credit mechanism to replace ABP, smallholder planting decisions will be constrained by input costs, limiting supply-side recovery.",
                    "evidence": [
                        "ABP loan book decline: ₦948bn outstanding (2022) to approximately ₦320bn (Q4 2025)",
                        "CBN/NIRSAL announced new agri-credit facility but disbursements yet to commence as at March 2026",
                        "NBS household survey: 34% of smallholders reduced planted area in 2025 due to input cost",
                    ],
                    "objection": "Private sector lenders and agtech companies are filling the credit gap.",
                    "rebuttal": "Private agri-lending remains concentrated in commercial and mid-scale operations. Smallholders under 5 hectares — who account for 80% of Nigerian food production — are not yet served by private capital at scale.",
                },
            ],
            "indicators": [
                {
                    "watch": "NBS monthly CPI food sub-index — released 15th of the following month at nigerianstat.gov.ng",
                    "confirms_if": "Food CPI falls below 30% y/y for two consecutive months, indicating naira stabilisation is feeding through to prices",
                    "disconfirms_if": "Food CPI exceeds 45% y/y, signalling either a new devaluation shock or a supply disruption",
                },
                {
                    "watch": "CBN/NIRSAL new agri-credit facility disbursements — CBN monthly development finance report",
                    "confirms_if": "Disbursements reach ₦150bn by June 2026, indicating a partial ABP replacement is operational",
                    "disconfirms_if": "No disbursements by June 2026, confirming the credit gap will persist into the 2026 planting season",
                },
                {
                    "watch": "AFEX spot price spread between farm-gate and retail for maize — published weekly on AFEX platform",
                    "confirms_if": "Farm-gate to retail spread narrows below 15%, indicating improved market efficiency",
                    "disconfirms_if": "Spread widens beyond 40%, confirming intermediaries are capturing disproportionate margin",
                },
            ],
        },
        "outlook": (
            "Harvest season in October–December 2026 should bring seasonal price relief of 10–15% on "
            "staple grains. Structural food inflation — driven by input costs and credit gaps — will not "
            "resolve before 2027. The base case is food CPI moderating to 28–32% by December 2026, "
            "contingent on naira stability. Any renewed FX pressure extends the pain."
        ),
        "decision_lens": (
            "Food manufacturers and processors: forward-contract key commodities on AFEX for Q3–Q4 2026 "
            "now — harvest-period prices will be lower, but the window is narrow before the next seasonal uplift. "
            "Importers of wheat and rice: hedge foreign currency payables on the FMDQ OTC market — "
            "do not carry unhedged FCY exposure through Q2 2026. "
            "Agritech and lending businesses: the smallholder credit gap is the largest addressable market "
            "in Nigerian agriculture — build for input financing and warehouse receipt products, not just logistics."
        ),
    },
    {
        "industry_slug": "agriculture-agritech",
        "title": "Commodity Exchanges Give Farmers a Way to Sell Forward — But Most Nigerian Farmers Have Never Used One",
        "bluf": (
            "The AFEX Commodities Exchange and LCFE are Nigeria's two licensed commodity exchanges, "
            "together listing maize, soybean, sorghum, and paddy rice. AFEX operates over 200 certified "
            "warehouses across 17 states and has processed over ₦200 billion in warehouse receipt financing "
            "since 2018. Futures trading on LCFE is nascent but growing. The structural case for exchange-based "
            "commodity finance is strong: it solves the post-harvest loss and working capital problems simultaneously. "
            "The constraint is adoption — most smallholders have never used these markets, and awareness "
            "campaigns have not matched the speed of financial product development."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "AFEX's warehouse network is now large enough to provide meaningful price discovery and financing at scale — this is no longer a pilot.",
                    "evidence": [
                        "AFEX certified warehouse locations: 200+ across 17 states (Q4 2025)",
                        "AFEX cumulative warehouse receipt financing: over ₦200bn since 2018",
                        "LCFE futures open interest: approximately ₦4bn across maize and soybean contracts (Feb 2026)",
                    ],
                    "objection": "₦4bn in LCFE open interest is tiny relative to the total commodity market — this is not yet a functional pricing mechanism.",
                    "rebuttal": "Open interest will remain thin until commercial hedgers (food manufacturers, flour millers) are incentivised to use the market. The infrastructure exists. The missing piece is corporate participation, not smallholder awareness.",
                },
                {
                    "finding": "Warehouse receipt financing allows smallholders to borrow against stored produce instead of selling at harvest lows — but uptake remains below 5% of eligible farmers.",
                    "evidence": [
                        "AFEX warehouse receipt loans: average ticket size ₦850,000, 90-day tenor",
                        "Estimated eligible producer population: 4.5 million smallholders near AFEX warehouse network",
                        "Active warehouse receipt borrowers: approximately 180,000 (Q3 2025) — approximately 4% of eligible population",
                    ],
                    "objection": "Low uptake suggests the product doesn't work for most smallholders — fees and logistics costs may outweigh benefits.",
                    "rebuttal": "Studies in comparable markets show warehouse receipt adoption reaches critical mass at 15–20% of eligible farmers once one or two large off-takers join the market. Nigeria has not yet reached that threshold.",
                },
                {
                    "finding": "As bank credit to agriculture tightens following ABP wind-down, exchange-based trade finance is the most viable large-scale replacement.",
                    "evidence": [
                        "Commercial bank agriculture credit: down 22% in real terms 2023–2025 (CBN banking sector report)",
                        "NIRSAL guarantee approvals: ₦180bn FY2025 vs. ₦310bn FY2022",
                        "AFEX and LCFE have no CBN liquidity support constraints — their financing is market-based",
                    ],
                    "objection": "Exchange-based finance requires commodity standards and grading that most Nigerian smallholders cannot currently meet.",
                    "rebuttal": "Grading is a solvable logistics problem. AFEX already employs over 500 field agents providing grading and warehousing support. The cost of building this last-mile infrastructure is declining as volumes increase.",
                },
            ],
            "indicators": [
                {
                    "watch": "AFEX weekly spot prices and warehouse receipt volumes — published on AFEX platform and monthly market report",
                    "confirms_if": "Warehouse receipt volumes exceed ₦10bn per month, indicating mainstream adoption is beginning",
                    "disconfirms_if": "Volumes stagnate below ₦2bn per month through 2026, suggesting uptake barriers are structural",
                },
                {
                    "watch": "LCFE futures open interest and number of active corporate hedgers — LCFE monthly market statistics",
                    "confirms_if": "At least five large food processors (Dangote, Flour Mills, Honeywell) become active hedgers by Q3 2026",
                    "disconfirms_if": "Open interest remains below ₦5bn with no new corporate participants by end-2026",
                },
                {
                    "watch": "CBN/NIRSAL agri-credit facility disbursements and eligibility criteria — CBN development finance communiqués",
                    "confirms_if": "CBN explicitly links new agri-credit eligibility to exchange-certified warehouse receipts",
                    "disconfirms_if": "CBN launches a direct lending programme (like ABP) that bypasses exchange infrastructure",
                },
            ],
        },
        "outlook": (
            "Exchange volumes are expected to grow 30–40% year-on-year through 2026 as commercial bank credit "
            "tightens and agribusinesses seek alternatives. The inflection point for mainstream adoption is "
            "corporate off-taker participation — if Dangote Foods or Flour Mills formally adopts AFEX as a "
            "procurement channel in 2026, uptake will accelerate materially."
        ),
        "decision_lens": (
            "Agribusinesses and food processors: engage AFEX on procurement-linked warehouse receipt programmes — "
            "buying standardised, exchange-graded produce at known prices reduces import dependency and FX exposure. "
            "Banks developing agricultural lending: use AFEX warehouse receipts as collateral — they are more "
            "liquid and verifiable than land or equipment in the Nigerian context. "
            "Agritech investors: the critical infrastructure build is last-mile warehousing and grading in "
            "under-served states — logistics-first plays will unlock the financing market."
        ),
    },
    # ── Fintech / Payments ───────────────────────────────────────────
    {
        "industry_slug": "fintech",
        "title": "Nigeria Processed ₦1 Quadrillion in Digital Payments Last Year — Now the CBN Is Raising the Bar to Stay Licensed",
        "bluf": (
            "NIBSS processed ₦1.07 quadrillion in electronic transactions in 2025 — a 48% increase year-on-year. "
            "Instant payment volumes via NIP are growing at 60% annually, driven by mobile and USSD channels. "
            "This growth has attracted regulatory attention. The CBN's 2025 Payment Service Provider Regulatory "
            "Framework raises minimum capital requirements substantially — the switching licence now requires "
            "₦50 billion in minimum capital, up from ₦10 billion. Smaller payment operators that cannot meet "
            "the new thresholds face a choice: merge, be acquired, or surrender their licence. Consolidation "
            "is already underway."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "Nigeria's payments market has reached global scale — ₦1 quadrillion in annual volume puts it among the top five payment markets in Africa by value.",
                    "evidence": [
                        "NIBSS 2025 annual statistics: ₦1.07 quadrillion total electronic transaction value",
                        "NIP instant payments: 60% year-on-year volume growth",
                        "Mobile money active wallets: 38 million (CBN Q4 2025 data)",
                    ],
                    "objection": "Transaction value is inflated by a few large interbank transfers — the SME and consumer market is much smaller.",
                    "rebuttal": "Retail transaction counts also grew 55% y/y. NIBSS data shows 7.8 billion individual transactions in 2025. This is genuine broad-based adoption, not just large-value interbank flows.",
                },
                {
                    "finding": "The CBN's new capital requirements will eliminate approximately one-third of current PSP licence holders by end-2026.",
                    "evidence": [
                        "CBN PSP Framework November 2025: switching licence minimum capital raised to ₦50bn",
                        "PSSP (Payment Solution Service Provider) minimum: raised from ₦100m to ₦3bn",
                        "Estimated non-compliant operators: approximately 35 of ~103 currently licensed PSPs (CBN/NITDA registry)",
                    ],
                    "objection": "Non-compliant operators have until December 2026 to recapitalise — many will raise the capital.",
                    "rebuttal": "Raising ₦50 billion in the current environment is effectively impossible for smaller operators without a strategic partner. The CBN intends market consolidation — the deadline is a mechanism, not a genuine remediation pathway.",
                },
                {
                    "finding": "The consolidation benefits acquirers that hold combined PSSP and PTC (Payment Terminal Company) licences — these are the most strategically valuable combinations.",
                    "evidence": [
                        "Interswitch holds combined switching + PTC: market leader position intact",
                        "Three acquisitions of sub-scale PSPs announced Q4 2025 – Q1 2026",
                        "Combined PSSP+PTC licence holders: 6 of 103 current operators",
                    ],
                    "objection": "Consolidation may reduce competition and raise merchant fees.",
                    "rebuttal": "The CBN's motivation is systemic stability, not price control. Some merchant fee pressure is likely, but the CBN's financial inclusion mandate means it will not allow monopoly pricing.",
                },
            ],
            "indicators": [
                {
                    "watch": "CBN PSP licence revocations and surrenders — CBN weekly regulatory actions register at cbn.gov.ng",
                    "confirms_if": "10 or more PSP licences are revoked or surrendered by June 2026, confirming consolidation is accelerating",
                    "disconfirms_if": "No licences revoked by June 2026 — suggests CBN extended the timeline or softened the capital requirement",
                },
                {
                    "watch": "NIBSS NIP uptime and transaction success rates — NIBSS monthly operational performance report",
                    "confirms_if": "NIP uptime exceeds 99.8% for three consecutive months, reflecting NIBSS infrastructure investment",
                    "disconfirms_if": "NIP downtime incidents exceed 48 hours cumulative per month, indicating infrastructure stress from volume growth",
                },
                {
                    "watch": "M&A announcements among payment operators — SEC Nigeria deal filings and company official statements",
                    "confirms_if": "Three or more PSP acquisitions are completed in 2026 involving non-compliant operators as sellers",
                    "disconfirms_if": "No acquisitions close, suggesting acquirers are waiting for distressed pricing after licences lapse",
                },
            ],
        },
        "outlook": (
            "NIP volume growth is sustainable through 2027 — it is driven by structural smartphone and USSD "
            "penetration, not macroeconomic conditions. The regulatory consolidation creates a two-year window "
            "of M&A opportunity before the market stabilises at a smaller number of larger, better-capitalised "
            "operators. Expect 3–5 PSP licence surrenders and 2–4 acquisitions in 2026."
        ),
        "decision_lens": (
            "Fintech operators below the new capital thresholds: do not wait for the December deadline — "
            "begin merger or white-label partnership conversations now while negotiating leverage exists. "
            "Distressed sellers have no leverage after the deadline. "
            "Strategic acquirers: the window for acquiring a PSSP licence at a reasonable valuation is 2026 — "
            "post-consolidation, remaining licences will be valued more highly. "
            "Investors: focus on acquirers with PSSP+PTC combinations — these are the highest-value operators "
            "after consolidation and the most likely to benefit from reduced competition."
        ),
    },
    {
        "industry_slug": "fintech",
        "title": "Nigeria's New Securities Law Legalises Crypto — But Operating Without a Licence Is Now a Criminal Offence",
        "bluf": (
            "The Investments and Securities Act 2025, signed in March 2025, is the first Nigerian law "
            "to explicitly recognise digital assets as investment securities. This ends four years of "
            "legal ambiguity and officially lifts the de facto prohibition on crypto activity that "
            "followed CBN's 2021 banking ban. However, the same law imposes strict requirements: "
            "all crypto exchanges and virtual asset service providers operating in Nigeria must register "
            "with SEC Nigeria. Operating without a Virtual Asset Service Provider licence is now a "
            "criminal offence carrying a ₦20 million fine or 10 years imprisonment. The regulatory "
            "environment has improved — but it has also become more demanding."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "ISA 2025 resolves the legal ambiguity but creates a high compliance bar — only well-resourced operators will be able to maintain a VASP licence.",
                    "evidence": [
                        "ISA 2025 sections 152–161: VASPs defined as securities issuers subject to SEC jurisdiction",
                        "SEC VASP registration requirements: minimum ₦500m capital, AML/CFT programme, technology audit",
                        "Provisional VASP approvals as at January 2026: 47 entities out of approximately 200 known active operators",
                    ],
                    "objection": "47 provisional approvals indicates the SEC is willing to register a broad range of operators.",
                    "rebuttal": "Provisional approval is not a licence — full registration requires proof of capital, system audits, and ongoing reporting. Historical VASP approval rates in comparable African jurisdictions suggest 30–40% of provisional approvals will not complete full registration.",
                },
                {
                    "finding": "CBN's softened position on crypto banking allows regulated exchanges to settle transactions through the banking system — but the dual-regulator structure creates friction.",
                    "evidence": [
                        "CBN circular December 2023: banks may accept deposits from and make payments to licensed VASPs",
                        "CBN VASP directive 2024: banks must conduct enhanced due diligence on crypto-related transactions",
                        "SEC-CBN gap: SEC licences the crypto operator; CBN controls the bank accounts — approvals are not automatic",
                    ],
                    "objection": "Dual regulation is a feature, not a bug — it creates broader oversight of systemic risk.",
                    "rebuttal": "The operational friction is real: CBN has debanked three SEC-provisionally approved VASPs since December 2023. Dual-regulator approval processes do not run in parallel.",
                },
                {
                    "finding": "The criminal penalties in ISA 2025 will drive unregistered operators offshore while concentrating the compliant market among a small number of large players.",
                    "evidence": [
                        "ISA 2025 section 163: operating as unlicensed VASP — fine of ₦20m or 10 years imprisonment or both",
                        "Binance delisted NGN trading pairs in February 2024 following regulatory pressure",
                        "Yellow Card, Quidax, and Busha have all commenced SEC registration",
                    ],
                    "objection": "Criminal penalties will not stop P2P crypto trading, which operates without licences by design.",
                    "rebuttal": "Correct — but ISA 2025 regulates the institutional ramp (exchanges, custodians, brokers). P2P will continue but cannot interact with the banking system without a licensed intermediary.",
                },
            ],
            "indicators": [
                {
                    "watch": "SEC Nigeria full VASP licence grant register — SEC weekly update at sec.gov.ng/vasp",
                    "confirms_if": "Full (not provisional) VASP licences granted to 20 or more operators by June 2026",
                    "disconfirms_if": "Fewer than 10 full licences granted by end-2026, suggesting SEC is bottlenecking the market",
                },
                {
                    "watch": "CBN debanking actions against SEC-registered VASPs — CBN regulatory actions register and industry association reports",
                    "confirms_if": "No CBN debanking of SEC-registered VASPs in 2026, indicating regulatory coordination is improving",
                    "disconfirms_if": "One or more SEC-registered VASPs debanked by CBN, confirming the dual-regulator friction persists",
                },
                {
                    "watch": "Total crypto trading volume through SEC-licensed Nigerian exchanges — exchange published data and NBS digital economy statistics",
                    "confirms_if": "Monthly trading volume through licensed exchanges exceeds $1bn by Q3 2026",
                    "disconfirms_if": "Volume remains below $200m per month, indicating regulatory uncertainty is suppressing demand",
                },
            ],
        },
        "outlook": (
            "Full SEC VASP licensing round is expected to complete by Q3 2026. The CBN's cross-border "
            "crypto guardrails — which will govern how licensed VASPs handle dollar settlements — are "
            "expected in H2 2026 and will be the next major regulatory event. The long-term trajectory "
            "is a well-regulated, bank-integrated crypto market with 8–12 major licensed operators."
        ),
        "decision_lens": (
            "Crypto exchanges operating in Nigeria: file SEC VASP full registration immediately — "
            "the penalty for missing the deadline is existential. Do not wait for the CBN position to "
            "clarify before starting the SEC process; they run independently. "
            "Nigerian commercial banks: begin technical integration with at least one SEC-licensed exchange "
            "now to be positioned for compliant crypto settlement products before competitors. "
            "International crypto platforms considering Nigeria market entry: engage a licensed local operator "
            "as a regulated partner rather than attempting direct consumer registration — the SEC timeline "
            "for foreign entity registration is 12–18 months."
        ),
    },
    # ── Telecoms ────────────────────────────────────────────────────
    {
        "industry_slug": "technology",
        "title": "Telecoms Companies Win a 50% Price Increase — Businesses Should Budget Higher Data Costs Now",
        "bluf": (
            "The Nigerian Communications Commission approved a 50% weighted average tariff increase for "
            "voice and data services in January 2026 — the first significant price increase for Nigerian "
            "telecoms consumers in over a decade. MTN, Airtel, and Globacom have begun phased implementation. "
            "The commercial rationale is clear: MNO margins had been compressed by costs that tripled in "
            "naira terms after the 2023 devaluation while tariffs stayed flat. The increase will restore "
            "EBITDA margins but transmission to end users is unavoidable. Businesses with large mobile "
            "workforces or data-intensive operations should treat this as a permanent cost increase, "
            "not a temporary spike."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "The 50% tariff increase was economically necessary — MNO margins had collapsed as naira costs rose while prices were frozen.",
                    "evidence": [
                        "MTN Nigeria EBITDA margin Q4 2024: 44% — down from 54% in Q4 2022 before the devaluation cycle",
                        "Airtel Nigeria: dollar-denominated opex (spectrum fees, equipment, bandwidth) up approximately 180% in naira terms since June 2023",
                        "NCC last tariff floor adjustment: 2013 — 12 years of real tariff compression",
                    ],
                    "objection": "MNOs should absorb cost increases — their margins were historically very high.",
                    "rebuttal": "A 44% EBITDA margin sounds healthy, but dollar-denominated debt service and capex requirements at current FX rates made new investment unviable at flat tariffs. Without price recovery, network quality and 5G investment would have been deferred indefinitely.",
                },
                {
                    "finding": "Data ARPU will grow 25–35% in 2026, but this will slow subscriber growth in price-sensitive segments.",
                    "evidence": [
                        "NCC tariff determination January 2026: 50% blended uplift approved with phased implementation",
                        "MTN Nigeria Q4 2025 ARPU: ₦1,543/month — expected to rise to ₦1,900–₦2,000 by Q4 2026",
                        "NCC subscriber churn analysis: estimated 2–4% subscriber reduction in price-sensitive USSD-dependent segment",
                    ],
                    "objection": "Higher prices will exclude low-income users from mobile internet, reversing financial inclusion gains.",
                    "rebuttal": "NCC has maintained a consumer protection floor: MNOs must offer a minimum low-cost data bundle. About 85% of data consumption by value is concentrated in the top-40% income bracket. Exclusion risk is real but concentrated in USSD feature-phone users.",
                },
                {
                    "finding": "5G coverage remains below 2% of the population despite licences being held since 2022 — the tariff increase is a prerequisite for meaningful 5G investment.",
                    "evidence": [
                        "5G licence holders: MTN, Airtel, Mafab (since 2022)",
                        "Estimated 5G population coverage March 2026: below 2% (NCC spectrum report)",
                        "MTN Nigeria 5G capex guidance 2026: ₦500bn, conditional on 'favourable regulatory environment'",
                    ],
                    "objection": "MNOs will use the tariff increase to fund dividends, not 5G investment.",
                    "rebuttal": "MTN has tied its 5G investment commitment explicitly to the tariff decision in investor communications. Market competition creates pressure to deploy. Dividend extraction at the expense of 5G would trigger NCC licence review.",
                },
            ],
            "indicators": [
                {
                    "watch": "MTN and Airtel Nigeria quarterly earnings — ARPU, subscriber count, and capex guidance",
                    "confirms_if": "MTN ARPU exceeds ₦2,000/month by Q3 2026 with no significant subscriber loss, confirming the increase has passed through",
                    "disconfirms_if": "Subscriber numbers fall more than 5% following implementation, triggering NCC review of the tariff order",
                },
                {
                    "watch": "NCC quarterly broadband penetration report — tracking 5G activated sites and LTE coverage gaps",
                    "confirms_if": "5G population coverage exceeds 5% by end-2026, showing capex is being deployed",
                    "disconfirms_if": "5G coverage stays below 2% through 2026, indicating MNOs are not investing as committed",
                },
                {
                    "watch": "NCC consumer complaint data — NCC monthly report and service quality tracking",
                    "confirms_if": "Consumer complaints per million subscribers decline after initial transition period, confirming network quality is improving",
                    "disconfirms_if": "Complaints spike and sustain above pre-increase levels, prompting NCC intervention on quality of service",
                },
            ],
        },
        "outlook": (
            "MNO ARPU will grow 20–30% in 2026. Data consumption will continue growing at 35–40% annually "
            "as smartphone penetration deepens. Fixed broadband alternatives remain scarce, making mobile "
            "data the primary internet access for businesses in most states. The 5G investment timeline "
            "is plausible but Lagos-centric — meaningful national 5G coverage is a 2028–2030 story."
        ),
        "decision_lens": (
            "IT and operations managers: revise 2026 telecoms budgets upward by 25–40% and negotiate "
            "bulk data procurement agreements directly with MNOs before Q2 price adjustments arrive. "
            "Companies with field-based workforces (logistics, FMCG distribution, financial services): "
            "evaluate whether mobile-data-dependent applications can be optimised for lower data usage "
            "to mitigate the cost increase. "
            "Real estate and infrastructure developers: buildings in Lagos, Abuja, and Port Harcourt "
            "should include 5G-ready passive infrastructure in new construction specifications from 2026."
        ),
    },
    # ── Regulatory / Policy ──────────────────────────────────────────
    {
        "industry_slug": "financial-services",
        "title": "Nigeria's Capital Markets Get Their Biggest Legal Overhaul in 30 Years — Every Listed Company Has New Obligations",
        "bluf": (
            "The Investments and Securities Act 2025, signed in March 2025, replaces the ISA 2007 and "
            "is the most comprehensive reform of Nigeria's securities law since ISA 1999. "
            "The Act brings digital assets under SEC regulation for the first time, creates new "
            "investment fund categories, substantially increases SEC enforcement powers, and mandates "
            "e-dividend payment for all listed companies. Every entity that issues securities, operates "
            "a fund, runs an exchange, or provides investment advice in Nigeria is directly affected. "
            "The implementing rules are still being developed — six months of SEC circulars are "
            "expected through H2 2026. Compliance cost will rise for all market participants."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "SEC Nigeria now has substantially stronger enforcement power — fines, licence revocations, and criminal referrals are all materially easier under ISA 2025.",
                    "evidence": [
                        "ISA 2025 enforcement actions FY2025: ₦2.3bn in fines and penalties vs. ₦0.4bn in 2024",
                        "New powers: SEC can freeze assets, impose lifetime trading bans, and refer directors for criminal prosecution without a prior court order",
                        "Civil liability provisions: investors can now sue issuers directly for misleading prospectus information",
                    ],
                    "objection": "SEC's historical enforcement record has been weak — stronger powers on paper may not translate to stronger enforcement in practice.",
                    "rebuttal": "The FY2025 enforcement data shows the change is already happening, not merely anticipated. SEC's new director-general has explicitly prioritised enforcement. The institutional momentum is real and the statutory tools now match the intent.",
                },
                {
                    "finding": "E-dividend mandates and new disclosure timelines will create short-term operational pain for listed companies unprepared for the change.",
                    "evidence": [
                        "ISA 2025 section 84: all listed companies must implement direct electronic dividend payment within 18 months of commencement",
                        "Current situation: approximately 40% of NGX-listed companies still use cheque-based dividend distribution",
                        "New continuous disclosure timeline: material events must be disclosed within 24 hours (down from 5 business days under ISA 2007)",
                    ],
                    "objection": "18 months is enough time to implement e-dividend — the technology is not complex.",
                    "rebuttal": "The technology is simple; the shareholder registry problem is not. Many listed companies have unclaimed dividend liability with shareholders whose bank details are unknown. Resolving the registry before the mandate takes effect is the real challenge.",
                },
                {
                    "finding": "New fund categories — infrastructure funds, REITs, and venture capital funds — will create product development opportunities, particularly for pension and insurance capital.",
                    "evidence": [
                        "NGX new ETF listings since ISA 2025 rules published: 15 new ETFs (Q4 2025)",
                        "First infrastructure fund approval expected Q1 2026 (Afriland Properties Infrastructure Fund)",
                        "PENCOM and NAICOM explicitly included in ISA 2025 fund-eligibility provisions",
                    ],
                    "objection": "New fund categories will not attract demand if the broader equity market remains illiquid.",
                    "rebuttal": "The new categories expand the asset management market beyond equities — REITs and infrastructure funds are fixed-income adjacent, which is exactly where pension and insurance capital is most deployable.",
                },
            ],
            "indicators": [
                {
                    "watch": "SEC Nigeria implementing rules and circulars — published at sec.gov.ng/publications",
                    "confirms_if": "SEC publishes more than 30 implementing circulars by June 2026, indicating rules are being operationalised at pace",
                    "disconfirms_if": "Fewer than 10 circulars published by June 2026, suggesting delays in subsidiary legislation development",
                },
                {
                    "watch": "NGX-listed company e-dividend implementation progress — NGX disclosure portal and CSCS shareholder reports",
                    "confirms_if": "80% of listed companies achieve e-dividend compliant shareholder registries by June 2026",
                    "disconfirms_if": "Fewer than 50% compliant by June 2026, indicating SEC will need to enforce or extend the deadline",
                },
                {
                    "watch": "SEC enforcement actions — fines, licence suspensions, and criminal referrals published in SEC weekly gazette",
                    "confirms_if": "Annual enforcement fine total exceeds ₦5bn in 2026, confirming the enforcement intensity established in 2025 is accelerating",
                    "disconfirms_if": "2026 enforcement total falls below ₦1bn, suggesting political pressure has slowed enforcement",
                },
            ],
        },
        "outlook": (
            "The pace of implementing rules will define how quickly market participants feel ISA 2025's full "
            "impact. The base case is 12 months of significant compliance investment across the market "
            "followed by a more stable regime from 2027. Beneficiaries will be well-capitalised and "
            "compliance-ready asset managers, exchanges that can build new product lines, and legal and "
            "advisory firms serving the compliance market."
        ),
        "decision_lens": (
            "Listed companies: immediately audit your shareholder registry for e-dividend readiness and "
            "appoint a compliance counsel with ISA 2025 experience — do not wait for the SEC circular on "
            "the 18-month countdown. "
            "Asset managers: assess eligibility for new fund structures now — infrastructure funds and "
            "REITs are the highest-priority new product opportunities given pension fund appetite. "
            "Legal and advisory firms: ISA 2025 compliance is a two-year revenue opportunity — "
            "ensure you have the specialist capacity to serve it."
        ),
    },
    # ── Macro / FX ──────────────────────────────────────────────────
    {
        "industry_slug": "financial-services",
        "title": "The Naira Has Lost Two-Thirds of Its Dollar Value Since 2023 — The Worst May Be Over, But Volatility Remains",
        "bluf": (
            "The naira depreciated from ₦460 per dollar in May 2023 to ₦1,590 per dollar by March 2026 "
            "— a 70% loss of dollar value — following the CBN's June 2023 float and removal of multiple "
            "exchange rate windows. The parallel market premium, which once reached 30–40%, has "
            "compressed to below 2% — the narrowest in a decade — signalling that the market now "
            "largely believes the official rate. Gross external reserves stand at approximately $37 billion, "
            "providing 3.5 months of import cover. This is adequate but not comfortable. "
            "The most acute phase of devaluation is likely over. What replaces it is persistent "
            "volatility rather than a further step decline — unless oil prices fall sharply or portfolio "
            "investors exit Nigeria simultaneously."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "FX unification has restored price discovery — the parallel-official rate convergence confirms the CBN is now running a credible FX policy.",
                    "evidence": [
                        "NAFEX official rate: ₦1,590/$ (March 2026)",
                        "Parallel rate (Bureau de Change): ₦1,612/$ — premium below 2%",
                        "Historical parallel premium: averaged 23% from 2016–2023 under the multiple-rate system",
                    ],
                    "objection": "A narrow parallel market premium could reflect CBN suppression of the parallel rate rather than genuine market convergence.",
                    "rebuttal": "CBN reserves ($37bn) are not at a level consistent with unsustainable intervention. The parallel rate has been narrowing since Q2 2024, well before reserves recovered to this level. The convergence is structural.",
                },
                {
                    "finding": "Nigeria's FX reserves are adequate but leave limited buffer — a $10–15 per barrel oil price drop would reduce import cover below 3 months within six months.",
                    "evidence": [
                        "CBN gross external reserves: $37.2bn (February 2026)",
                        "Import cover calculation: Nigeria imports approximately $10.5bn per quarter",
                        "Oil revenue sensitivity: each $10/bbl reduction in Brent reduces NNPCL monthly naira remittances by approximately $300m",
                    ],
                    "objection": "IMF programme discussions and World Bank budget support provide additional reserves backstop.",
                    "rebuttal": "Multilateral disbursements are conditional and slow. The real-time buffer is the CBN's own reserves. At current oil prices they are adequate; at $65/bbl they are not. The tail risk is real.",
                },
                {
                    "finding": "Portfolio capital has begun returning to Nigerian fixed-income markets — sustained inflows depend entirely on CBN credibility, not on the real economy.",
                    "evidence": [
                        "FGN eurobond yield decline: 10-year yield from 11.8% (October 2023) to 9.2% (March 2026)",
                        "Foreign portfolio investment in NTBs: ₦1.2trn in Q4 2025 (CBN data)",
                        "Carry trade: MPR 27.5% vs. expected 12-month depreciation ~10% = positive carry of ~17%",
                    ],
                    "objection": "Hot-money portfolio inflows increase Nigeria's vulnerability to sudden reversals.",
                    "rebuttal": "Correct — but in the near term portfolio inflows support the naira and reduce pressure on reserves. The risk is 2027-onwards if global risk-off conditions materialise. Managing the exit will be the CBN's challenge, not the entry.",
                },
            ],
            "indicators": [
                {
                    "watch": "CBN gross external reserves — published weekly at cbn.gov.ng",
                    "confirms_if": "Reserves exceed $40bn, indicating NNPCL remittances and portfolio inflows are sufficient for comfortable buffer",
                    "disconfirms_if": "Reserves fall below $32bn, indicating pressure is building and CBN may need to resume rationing",
                },
                {
                    "watch": "NAFEX official rate and parallel rate spread — FMDQ daily fix and BDC association weekly rates",
                    "confirms_if": "Premium stays below 3% for six consecutive months — confirms rate unification is durable",
                    "disconfirms_if": "Premium widens above 10%, indicating market distrust of the official rate is re-emerging",
                },
                {
                    "watch": "Brent crude oil price — ICE Brent futures, 30-day average",
                    "confirms_if": "Brent stays above $80/bbl through Q3 2026, supporting NNPCL dollar inflows",
                    "disconfirms_if": "Brent falls below $70/bbl for more than 30 days, creating immediate pressure on reserves and naira",
                },
            ],
        },
        "outlook": (
            "The base case for 2026 is naira trading between ₦1,500 and ₦1,700 per dollar with episodic "
            "volatility. Modest naira appreciation to ₦1,500 is possible in H2 2026 if oil stays above $80 "
            "and portfolio inflows continue. The downside scenario — naira to ₦2,000 — requires an oil "
            "price shock below $65 combined with portfolio exit. This scenario has a 20–25% probability "
            "under current conditions."
        ),
        "decision_lens": (
            "CFOs with significant import payables: maintain 3–6 month forward cover on dollar payables "
            "through FMDQ OTC forwards — the base case is range-bound, but tail risk asymmetry favours hedging. "
            "Lenders with dollar-denominated loan books: stress-test your loan-to-value ratios at ₦1,800/$ "
            "and ₦2,000/$ — if your coverage ratios fail at ₦1,800, that is an immediate provisioning question. "
            "Portfolio managers: the carry trade in NTBs (17%+ real carry) is attractive but requires an "
            "exit plan. Model your liquidity assumptions if global risk-off conditions hit in 2026–2027."
        ),
    },
    # ── Infrastructure ───────────────────────────────────────────────
    {
        "industry_slug": "energy",
        "title": "Lagos Ports Are Taking 21 Days to Clear Goods — Lekki Deep Sea Port Is the Fastest Escape Route",
        "bluf": (
            "Apapa Port, which handles approximately 70% of Nigeria's containerised imports, averaged "
            "21 days container dwell time in Q4 2025. The global benchmark for efficient ports is 3–5 days. "
            "The difference costs importers $500–$700 per container in demurrage and storage fees. "
            "Lekki Deep Sea Port, which opened in April 2023, is processing approximately 45,000 containers "
            "per month — about 18% of its nameplate capacity — and dwell times there average 7–9 days. "
            "Lekki is not a solution yet. But it is the fastest available improvement for importers "
            "who can route their cargo there, and its dwell time advantage will persist for at least "
            "three years while Apapa's structural problems remain unresolved."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "Apapa's congestion is caused by three compounding failures — road access, customs digitisation, and terminal operator capacity — none of which has a short-term fix.",
                    "evidence": [
                        "Apapa Port average container dwell time: 21 days (NPA Q4 2025 operations report)",
                        "Lagos-Apapa expressway rehabilitation: ongoing since 2021, 30% completion reported by FERMA March 2026",
                        "Nigeria Customs Service e-customs migration: partially implemented, manual overrides still account for 45% of clearances",
                    ],
                    "objection": "The e-customs programme will cut dwell time significantly once fully implemented.",
                    "rebuttal": "The e-customs programme has had its full-implementation date deferred three times since 2019. At 45% manual override rate in March 2026, meaningful improvement requires behaviour change at 20,000+ customs officers. System deployment and behavioural adoption are different things.",
                },
                {
                    "finding": "Lekki Deep Sea Port is operationally superior for importers who can use it — its dwell time advantage of 12–14 days over Apapa translates directly into cash flow savings.",
                    "evidence": [
                        "Lekki Port average dwell time: 7–9 days (Lekki Port Company reported, Feb 2026)",
                        "Lekki Port monthly throughput: 45,000 TEUs (Feb 2026 — approximately 18% of 2.7m TEU/year nameplate)",
                        "Demurrage comparison: $580/TEU average at Apapa vs. $140/TEU at Lekki (major shipping lines invoices)",
                    ],
                    "objection": "Lekki's road connections to distribution networks in Lagos are still underdeveloped — import routing there adds internal logistics costs.",
                    "rebuttal": "For large-volume importers (above 50 containers/month), the $440/TEU demurrage saving overwhelms additional haulage costs even at current road conditions. The Lekki-Epe Expressway Phase 2 is under construction.",
                },
                {
                    "finding": "Port congestion is a structural contributor to consumer price inflation and a direct competitiveness drag on manufacturing.",
                    "evidence": [
                        "NESG 2025 port congestion study: Apapa congestion costs the economy approximately $2.8bn annually in demurrage, delayed inventory, and secondary logistics",
                        "Manufacturing companies sourcing imported inputs: average inventory holding cost increases of 18% attributable to port delays",
                        "World Bank Logistics Performance Index: Nigeria ranked 130th out of 160 countries (2023)",
                    ],
                    "objection": "This is a well-known problem — the macroeconomic cost is not new information.",
                    "rebuttal": "The novelty is Lekki. For the first time, importers have a real alternative within the same metropolitan area. The cost differential is large enough to change procurement behaviour without any policy change required.",
                },
            ],
            "indicators": [
                {
                    "watch": "NPA monthly port performance report — Apapa and Lekki dwell time, vessel waiting time, and TEU throughput",
                    "confirms_if": "Lekki throughput exceeds 100,000 TEUs/month by Q4 2026, indicating importer routing shift is underway",
                    "disconfirms_if": "Lekki throughput remains below 60,000 TEUs/month, suggesting shipping line terminal assignments are not shifting",
                },
                {
                    "watch": "Nigeria Customs Service e-customs implementation progress — NCS quarterly report and importers association feedback",
                    "confirms_if": "Manual override rate falls below 20% by Q3 2026, indicating e-customs is materially reducing processing time",
                    "disconfirms_if": "Manual override rate stays above 40% through 2026, confirming e-customs has not changed clearance behaviour",
                },
                {
                    "watch": "Lekki-Epe Expressway Phase 2 construction progress — Lagos State government project updates",
                    "confirms_if": "Phase 2 highway section connecting Lekki Port to Sagamu-Ore road opens by Q3 2026",
                    "disconfirms_if": "No opening by end-2026 — Lekki's haulage cost disadvantage persists for another year",
                },
            ],
        },
        "outlook": (
            "Lekki throughput will approximately double by Q4 2026 as more shipping line terminal windows open "
            "and road connections improve. Apapa congestion will see only marginal improvement — the structural "
            "problems (road access, customs, terminal capacity) are each multi-year fixes. For importers, "
            "Lekki is the only near-term improvement available, and the transition is accelerating."
        ),
        "decision_lens": (
            "Importers with regular container flows: negotiate Lekki Deep Sea Port as primary destination with "
            "your shipping line for new and renewal contracts starting Q2 2026 — the $440/TEU average saving "
            "justifies the transition cost. "
            "Supply chain and logistics managers: model your Lekki routing scenario now, including current "
            "haulage rates and Lekki-Epe timing assumptions. The decision should be made on data, not habit. "
            "Warehouse and distribution operators: locate next facility acquisition or lease on the Lekki "
            "corridor — the shift in import routing will drive demand for warehouse space on the eastern axis."
        ),
    },
    # ── Labour / Industrial Relations ────────────────────────────────
    {
        "industry_slug": "financial-services",
        "title": "Workers' Real Wages Have Fallen 35% Since 2023 — Labour Unions Are Preparing to Strike Unless Pay Catches Up",
        "bluf": (
            "The ₦70,000 monthly minimum wage agreed in July 2024 was a 240% nominal increase over the "
            "previous ₦30,000 floor. In real terms — accounting for 75%+ cumulative food and general inflation "
            "since 2023 — workers are still approximately 35% poorer than before the devaluation. "
            "The Nigeria Labour Congress and Trade Union Congress have formally demanded a further increase "
            "to ₦120,000 per month effective January 2026, citing ongoing price increases. The federal "
            "government's Tripartite Committee has not agreed. Both the NLC and TUC have the legal "
            "authority to call a general strike with 14 days notice. The conditions for industrial action "
            "are present — the question is whether a negotiated settlement arrives before they act."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "Real wages at the minimum wage floor have declined approximately 35% since 2023 even after the July 2024 nominal increase — the demand for ₦120,000 is mathematically reasonable.",
                    "evidence": [
                        "Minimum wage July 2024: ₦70,000/month — up 240% nominally from ₦30,000",
                        "Cumulative CPI inflation June 2023–January 2026: approximately 87% (NBS data)",
                        "₦70,000 in January 2026 naira = equivalent purchasing power of approximately ₦37,450 at June 2023 prices",
                    ],
                    "objection": "The 240% nominal increase to ₦70,000 was the largest minimum wage increase in Nigerian history — government has already done more than precedent requires.",
                    "rebuttal": "The size of the nominal increase is irrelevant if the real purchasing power is below the prior floor. The NLC's position is based on cost-of-living data, not historical precedent. The arithmetic supports a further demand.",
                },
                {
                    "finding": "The federal government is fiscally constrained — it cannot afford ₦120,000 across the formal public sector without cutting headcount or borrowing.",
                    "evidence": [
                        "FGN wage bill FY2025: approximately ₦7.1trn, the largest single expenditure line",
                        "Moving all federal employees to ₦120,000 floor: estimated incremental cost ₦1.8–₦2.4trn annually",
                        "FGN retained revenue Q4 2025: ₦1.9trn — already 85% consumed by debt service",
                    ],
                    "objection": "Government can selectively raise wages for lower-grade workers without lifting the entire salary structure.",
                    "rebuttal": "A minimum wage increase creates legal obligations on all employers, not just the federal government. State governments — 36 of which are already in arrears on the ₦70,000 wage — would face fiscal failure. The federal government negotiating ₦120,000 while knowing 25+ states cannot pay it creates a compliance crisis.",
                },
                {
                    "finding": "Private sector compliance with the existing ₦70,000 minimum wage is inconsistent — a further increase widens the enforcement gap.",
                    "evidence": [
                        "NLC survey Q4 2025: 42% of private sector employers surveyed had not fully implemented ₦70,000 minimum wage",
                        "Labour inspectorate capacity: 847 inspectors for 37 million formal sector workers (Ministry of Labour 2025)",
                        "Industrial court backlog: over 12,000 pending wage dispute cases (NIC annual report 2025)",
                    ],
                    "objection": "Non-compliance is concentrated in informal and small enterprises — large employers are compliant.",
                    "rebuttal": "Mid-size manufacturers in Lagos and Port Harcourt facing NLC-affiliated unions are at direct risk of industrial action regardless of headline compliance statistics.",
                },
            ],
            "indicators": [
                {
                    "watch": "FGN Tripartite Committee meeting schedule and outcomes — Ministry of Labour official statements and NLC press releases",
                    "confirms_if": "Tripartite agreement reached by May 2026 at ₦85,000–₦100,000, avoiding general strike",
                    "disconfirms_if": "No agreement by June 2026, triggering NLC 14-day strike notice — at which point disruption is near-certain",
                },
                {
                    "watch": "Sector-specific strike actions — ASUU (universities), JOHESU (healthcare), NUPENG (oil and gas) — each issues strike notices independently",
                    "confirms_if": "All major sector unions sign separate recognition agreements by Q2 2026, reducing general strike risk",
                    "disconfirms_if": "One major sector strike (especially NUPENG oil workers) occurs and is not quickly resolved, emboldening NLC for broader action",
                },
                {
                    "watch": "State government minimum wage compliance rates — NLC state council reports, available via NLC monthly bulletin",
                    "confirms_if": "Fewer than 5 states in formal arrears on ₦70,000 wage by June 2026",
                    "disconfirms_if": "More than 15 states in arrears — signals fiscal capacity crisis that makes any higher minimum wage economically unenforceable",
                },
            ],
        },
        "outlook": (
            "A compromise minimum wage of ₦85,000–₦100,000 per month is the most likely outcome by mid-2026, "
            "negotiated under strike pressure. The primary risk is a cascading sector-specific strike sequence "
            "in H1 2026 — universities, healthcare, then oil and gas — that escalates before a general "
            "settlement is reached. At the current pace of negotiations, a general strike call by June 2026 "
            "has a 35–40% probability."
        ),
        "decision_lens": (
            "Human resources and compensation leaders: model your total wage bill at ₦90,000 and ₦120,000 "
            "minimum wage scenarios now — waiting for the announced figure before budgeting creates a lag "
            "that is hard to manage. Begin productivity-offset negotiations with your most senior HR partner "
            "or union representative while goodwill still exists. "
            "Manufacturers in Lagos, Rivers, and Kano: your NLC-affiliated factory unions are monitoring "
            "the federal negotiation closely. An extended general strike will affect supply chains — "
            "build a 3-week inventory buffer before June 2026. "
            "Financial institutions: budget for collections slowdown and higher provisions during any "
            "sustained industrial action period — retail and SME borrowers are most sensitive to wage disruption."
        ),
    },
    # ── Healthcare / NAFDAC ──────────────────────────────────────────
    {
        "industry_slug": "healthcare",
        "title": "NAFDAC Seized ₦4 Billion of Substandard Medicines Last Year — Track-and-Trace Compliance Is Mandatory by July 2026",
        "bluf": (
            "The National Agency for Food and Drug Administration and Control seized over 12,000 "
            "substandard and falsified medicine products worth ₦4.2 billion in 2025, a threefold "
            "increase from 2023. This is not a tightening of standards — it is an intensification of "
            "enforcement against a persistent problem. NAFDAC has issued a mandatory track-and-trace "
            "directive (Circular NAFDAC/RD/9/1/173) requiring all manufacturers and importers of "
            "prescription medicines to implement product serialisation by July 2026. "
            "Non-compliant products will be seized at point of distribution. This is a genuine operational "
            "deadline, not an aspirational one — NAFDAC has already demonstrated the enforcement capacity."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "NAFDAC's enforcement capacity has materially increased — the 2025 seizure data represents a genuine operational step-change, not just better reporting.",
                    "evidence": [
                        "NAFDAC 2025 enforcement: 12,000+ products seized across manufacturers, importers, and distributors",
                        "Total value of seized goods: ₦4.2bn (2025) vs. ₦1.3bn (2023) — 223% increase",
                        "Enforcement actions: 847 companies issued compliance notices; 112 licence suspensions",
                    ],
                    "objection": "Higher seizure numbers could reflect expanded reporting rather than increased enforcement activity.",
                    "rebuttal": "NAFDAC's 2025 data includes a new post-market surveillance programme covering 28 states — up from 12 in 2022. The increase in seizures tracks the broader geographic coverage.",
                },
                {
                    "finding": "The July 2026 track-and-trace deadline is technically achievable but requires immediate investment — companies that have not started will not complete it in time.",
                    "evidence": [
                        "Track-and-trace directive: Circular NAFDAC/RD/9/1/173 (December 2025) — effective 1 July 2026",
                        "Serialisation implementation timeline: minimum 6–8 months from purchase order to full deployment (industry benchmark)",
                        "As at March 2026: approximately 35% of affected manufacturers have begun procurement of serialisation equipment",
                    ],
                    "objection": "NAFDAC has historically extended implementation deadlines under industry pressure.",
                    "rebuttal": "NAFDAC has stated explicitly that the track-and-trace deadline is non-negotiable following a series of mass-poisoning incidents in 2025. The political will for extension is absent. Companies relying on deadline extension are taking a business-continuity risk.",
                },
                {
                    "finding": "Local manufacturers who implement track-and-trace before the deadline gain a competitive advantage over non-compliant importers who face distribution disruption.",
                    "evidence": [
                        "India API ban: 23 active pharmaceutical ingredients restricted from Indian manufacturers following GMP failures",
                        "Import finished goods under investigation: NAFDAC has 34 active import audits on manufacturers from India and China",
                        "Early-mover analysis: Emzor Pharmaceuticals and May & Baker already serialised — marketing Rx products to public sector as 'NAFDAC track-and-trace verified'",
                    ],
                    "objection": "Track-and-trace costs will disadvantage local manufacturers relative to large multinationals who implement it more cheaply at scale.",
                    "rebuttal": "The reverse is true for the Nigerian market. Large multinationals are mostly import-dependent and face the highest import audit risk. Local manufacturers who invest now compete on verified supply chain integrity, which is increasingly valued by hospital procurement committees.",
                },
            ],
            "indicators": [
                {
                    "watch": "NAFDAC compliance status register — NAFDAC website track-and-trace implementation list, updated monthly",
                    "confirms_if": "More than 60% of Rx medicine manufacturers listed as compliant by April 2026, indicating the deadline is feasible",
                    "disconfirms_if": "Below 30% compliance by April 2026, indicating NAFDAC may extend or phase the deadline",
                },
                {
                    "watch": "NAFDAC import licence renewal decisions for non-compliant manufacturers — NAFDAC licence register and distribution association reports",
                    "confirms_if": "NAFDAC refuses or withholds import licences for non-serialised medicine manufacturers by August 2026",
                    "disconfirms_if": "Non-compliant importers continue to receive licence renewals, signalling the deadline is not being enforced at the import stage",
                },
                {
                    "watch": "Active ingredient supply disruptions from India ban — Pharmaceutical Society of Nigeria supply shortage notices",
                    "confirms_if": "No shortages of affected APIs, indicating Nigerian manufacturers have successfully sourced alternatives",
                    "disconfirms_if": "Shortages of more than 5 essential medicines attributable to the API ban emerge in public health facilities",
                },
            ],
        },
        "outlook": (
            "Compliance costs will increase 15–25% for importers of finished pharmaceuticals and for "
            "manufacturers sourcing restricted Indian APIs. Local manufacturers with track-and-trace "
            "capability will gain market share in public sector tenders from H2 2026. The broader "
            "trajectory is a more regulated and less fragmented pharmaceutical supply chain — this is "
            "the right direction but will cause short-term disruption for non-compliant incumbents."
        ),
        "decision_lens": (
            "Pharmaceutical manufacturers and importers: begin track-and-trace procurement immediately — "
            "the 6–8 month implementation window means March 2026 is the last safe start date. "
            "Order equipment, do not wait for further NAFDAC guidance. "
            "Hospital procurement committees: require NAFDAC track-and-trace verification as a tender "
            "qualification criterion from Q3 2026 — this is your most practical defence against "
            "substandard medicines entering your supply chain. "
            "Investors in pharmaceutical distribution: the track-and-trace transition will create "
            "distributor consolidation among verified-chain operators — this is a 2–3 year investment thesis."
        ),
    },
    # ── Pension / PENCOM ─────────────────────────────────────────────
    {
        "industry_slug": "financial-services",
        "title": "Nigeria's Pension Fund Has ₦21 Trillion — But 64% Is Locked in Government Bonds, Not Productive Investment",
        "bluf": (
            "Nigeria's Contributory Pension Scheme has accumulated ₦21.3 trillion ($13.4 billion) in "
            "assets under management as of December 2025, covering 9.3 million formal sector workers. "
            "It is one of the largest pension pools in sub-Saharan Africa. However, 64% of this capital "
            "is invested in Federal Government of Nigeria bonds, 16% in Treasury Bills, and only 5% in "
            "equities. This concentration in government paper is partly regulatory — PENCOM investment "
            "guidelines limit some funds to a maximum 5–10% equity allocation. PENCOM is now proposing "
            "to increase equity allocation limits — if implemented, it would be the single largest "
            "structural demand shift on the Nigerian Stock Exchange in a decade."
        ),
        "body_json": {
            "findings": [
                {
                    "finding": "Nigeria's pension pool is large enough to be a transformative source of long-term domestic capital — but current rules trap most of it in government securities.",
                    "evidence": [
                        "PENCOM AUM: ₦21.3trn as at December 2025",
                        "FGN bond allocation: 64% of AUM = approximately ₦13.6trn",
                        "T-Bill allocation: 16% = approximately ₦3.4trn",
                        "Equity allocation: 5% — PENCOM maximum permitted under current multi-fund investment regulations for default Fund III",
                    ],
                    "objection": "Government bonds are appropriate for a pension fund — they are safe, predictable, and match long-term liability profiles.",
                    "rebuttal": "At 80% government paper, Nigerian pension funds are underweight capital formation investments. At current MPR-linked bond yields of 18–22%, the nominal returns are high, but the real return — after 30%+ inflation — is negative or barely positive for most bond holdings.",
                },
                {
                    "finding": "PENCOM's proposed increase in equity allocation to 25% for default Fund III would add approximately ₦4trn in institutional demand to the Nigerian Stock Exchange.",
                    "evidence": [
                        "PENCOM consultation paper December 2025: proposed equity ceiling increase from 10% to 25% for Fund III",
                        "Implied new equity demand: ₦21.3trn × 20 percentage points = approximately ₦4.3trn in new equity allocation",
                        "NGX current market capitalisation: approximately ₦55trn — the additional demand represents 8% of the entire market",
                    ],
                    "objection": "NGX does not have enough liquid, quality stocks to absorb ₦4trn in institutional demand without distorting prices.",
                    "rebuttal": "The inflow would not arrive instantly — it would build over 3–5 years as PFAs rebalance portfolios. The structural effect is higher quality-company valuations and incentivisation of new listings, not a one-time distortion.",
                },
                {
                    "finding": "Micro-pension uptake remains minimal — 870,000 subscribers against an informal economy of 40+ million workers — because product design and distribution are weak.",
                    "evidence": [
                        "Micro-pension subscribers December 2025: 870,000",
                        "Informal sector workers estimated at 40–45 million (NBS Labour Force Survey 2025)",
                        "Penetration rate: approximately 2%",
                        "Average micro-pension contribution per subscriber: ₦4,200/month",
                    ],
                    "objection": "Informal workers have irregular income — a savings product requiring monthly contributions will never achieve mass penetration.",
                    "rebuttal": "The SSNIT model in Ghana shows informal pension penetration can exceed 20% with flexible contribution timing configured for daily or event-based income patterns. Nigeria's micro-pension allows flexible contributions in theory, but real-time USSD and agent-network infrastructure is not yet deployed at scale.",
                },
            ],
            "indicators": [
                {
                    "watch": "PENCOM quarterly AUM and asset allocation report — published at pencom.gov.ng",
                    "confirms_if": "Equity allocation rises above 8% of AUM by end-2026, indicating PENCOM has revised fund regulation",
                    "disconfirms_if": "Equity allocation stays below 6% through 2026, confirming the proposed regulation change has not been implemented",
                },
                {
                    "watch": "PENCOM draft investment regulation final publishing — PENCOM official communications and Federal Gazette",
                    "confirms_if": "Final regulation raising equity ceiling published in H1 2026, giving PFAs clarity to begin rebalancing",
                    "disconfirms_if": "No final regulation published by end-2026, pushing the equity allocation opportunity to 2027 or beyond",
                },
                {
                    "watch": "Micro-pension subscriber growth — PENCOM quarterly industry report",
                    "confirms_if": "Micro-pension subscribers exceed 2 million by end-2026, indicating distribution channels are working",
                    "disconfirms_if": "Subscribers remain below 1 million by end-2026, confirming the product has not found its market",
                },
            ],
        },
        "outlook": (
            "AUM will cross ₦25 trillion by end-2026 driven by wage growth and employer compliance "
            "enforcement. The equity allocation regulatory change has a 60% probability of being "
            "finalised in 2026 — the draft is published and opposition is limited. If the change "
            "is implemented, expect a 3–5 year gradual rebalancing that meaningfully deepens NGX "
            "liquidity and supports quality-company IPOs."
        ),
        "decision_lens": (
            "Investment banks and equity brokers: develop NGX large-cap and quality-mid-cap placement "
            "strategies ahead of the PENCOM equity allocation rule change — institutional demand at scale "
            "will require new placement infrastructure and quality deal flow. "
            "Listed companies preparing for capital raises: time your next rights issue or secondary "
            "placement for H2 2026 or 2027, when pension fund equity appetite will be formally unlocked. "
            "Employers: audit your CPS compliance — PENCOM's enforcement of employer remittances has "
            "intensified, with ₦12bn in enforcement orders issued in 2025. "
            "Micro-pension and fintech operators: the 2% penetration ceiling is a product design problem, "
            "not a market demand problem. Deploy agent-based and USSD-first distribution before "
            "better-funded competitors do."
        ),
    },
]


async def seed(dry_run: bool = False) -> None:
    import sqlalchemy as sa

    from backend.models.industry import Industry
    from backend.models.intelligence_brief import IntelligenceBrief

    async with AsyncSessionLocal() as db:
        # ── Resolve industries ────────────────────────────────────────
        result = await db.execute(sa.select(Industry.id, Industry.slug))
        industry_map: dict[str, object] = {row.slug: row.id for row in result.all()}

        created = 0
        skipped = 0

        for brief_def in BRIEFS:
            slug = brief_def["industry_slug"]
            industry_id = industry_map.get(slug)
            if industry_id is None:
                logger.warning("Industry slug '%s' not found — skipping brief: %s", slug, brief_def["title"])
                skipped += 1
                continue

            # Idempotency: skip if brief with same title already exists
            existing = await db.execute(
                sa.select(IntelligenceBrief.id).where(
                    IntelligenceBrief.title == brief_def["title"],
                    IntelligenceBrief.org_id.is_(None),
                )
            )
            if existing.scalar_one_or_none() is not None:
                logger.info("Brief already exists, skipping: %s", brief_def["title"])
                skipped += 1
                continue

            if dry_run:
                print(f"[DRY RUN] Would create: {brief_def['title']}")
                created += 1
                continue

            brief = IntelligenceBrief(
                id=uuid4(),
                org_id=None,  # Global / visible to all orgs
                industry_id=industry_id,
                title=brief_def["title"],
                brief_type="pre_built",
                bluf=brief_def.get("bluf"),
                body_json=brief_def.get("body_json", {}),
                outlook=brief_def.get("outlook"),
                decision_lens=brief_def.get("decision_lens"),
                status="published",
            )
            db.add(brief)
            created += 1

        if not dry_run:
            await db.commit()

        logger.info(
            "Nigeria briefs seed: created=%d skipped=%d dry_run=%s",
            created, skipped, dry_run,
        )
        print(f"Done — created: {created}, skipped: {skipped}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Nigeria intelligence briefs")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(seed(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
