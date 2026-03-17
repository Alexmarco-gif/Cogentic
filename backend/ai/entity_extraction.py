"""LLM-based entity and structured data extraction (NER).

Uses GPT-4o structured output to extract entities, numeric data,
geographic mentions, and source references from signal text.

This is the core intelligence upgrade that enables dynamic entity discovery:
- Organizations, companies, people, products, regulators, commodities
- Structured numeric data (prices, percentages, volumes, rates)
- Geographic context (country, state, city, region)
- Source URLs referenced in signal text (for source discovery)

Nigeria/Africa-first: NGA is the primary depth market. All prompting biases
toward Nigerian/African market structures, regulators, informal actors, and
FX realities. Other markets are fully supported as secondary contexts.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Singleton OpenAI client
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        import httpx

        _client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            http_client=httpx.AsyncClient(timeout=60.0),
        )
    return _client


# ── Data Classes ─────────────────────────────────────────────────────


@dataclass
class EntityMention:
    """An entity mention extracted from signal text by NER."""

    name: str
    entity_type: str  # company, person, product, regulator, commodity, infrastructure, financial_institution
    confidence: float  # 0.0 to 1.0
    context: str  # Brief surrounding context
    aliases: list[str] = field(default_factory=list)


@dataclass
class NumericDataPoint:
    """A structured numeric data point extracted from signal text."""

    value: float
    unit: str  # currency, percentage, volume, count, rate, index
    metric: str  # What this number represents (e.g., "rice price per bag")
    currency: str | None = None  # ISO 4217 if applicable (NGN, USD, etc.)
    context: str = ""


@dataclass
class GeographicMention:
    """A geographic location mentioned in signal text."""

    name: str
    geo_type: str  # country, state, city, region, market
    country_code: str | None = None  # ISO 3166-1 alpha-3 (e.g., NGA)
    parent_region: str | None = None  # e.g., "West Africa" for Nigeria


@dataclass
class SourceReference:
    """A URL or data source referenced in signal text."""

    url: str
    name: str | None = None  # Inferred source name
    source_type: str | None = None  # news, api, government, social, research


@dataclass
class ExtractionResult:
    """Complete extraction result from a single signal."""

    entities: list[EntityMention] = field(default_factory=list)
    numeric_data: list[NumericDataPoint] = field(default_factory=list)
    geographic: list[GeographicMention] = field(default_factory=list)
    sources: list[SourceReference] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)
    extraction_model: str = "gpt-4o"
    tokens_used: int = 0


# ── Extraction Prompt ────────────────────────────────────────────────

# ── Regional context blocks — each keyed by ISO 3166-1 alpha-3 ──────────────
# Nigeria (NGA) is the PRIMARY depth market. Its context block is the most
# detailed and is the default fallback for unrecognised African markets.
REGIONAL_CONTEXT: dict[str, str] = {
    "NGA": """PRIMARY MARKET — Nigeria: Apply maximum depth and precision.

REGULATORY BODIES (extract full name + acronym):
- CBN = Central Bank of Nigeria (monetary policy, FX, bank licensing, CRR, MPR, LDR)
- SEC = Securities and Exchange Commission (capital markets, IPOs, bonds)
- NCC = Nigerian Communications Commission (telecoms, spectrum, tariffs)
- NERC = Nigerian Electricity Regulatory Commission (power sector, GenCos, DisCos)
- NAFDAC = National Agency for Food and Drug Administration and Control
- FIRS = Federal Inland Revenue Service (corporate tax, VAT, WHT)
- CAC = Corporate Affairs Commission (business registration)
- SON = Standards Organisation of Nigeria (product standards)
- NAICOM = National Insurance Commission
- PENCOM = National Pension Commission (PFAs, RSA)
- BPE = Bureau of Public Enterprises (privatisation, concessions)
- FMARD = Federal Ministry of Agriculture and Rural Development
- NIPC = Nigerian Investment Promotion Commission
- EFCC = Economic and Financial Crimes Commission (enforcement)
- NDIC = Nigeria Deposit Insurance Corporation
- DMO = Debt Management Office (FGN bonds, Eurobonds, Sukuk)
- CBN MPC = Monetary Policy Committee

FINANCIAL INSTITUTIONS (tier 1 and key tier 2):
- Tier 1 banks: Access Bank, GTBank (Guaranty Trust), Zenith Bank, First Bank of Nigeria, UBA (United Bank for Africa)
- Tier 2: Stanbic IBTC, FCMB, Union Bank, Wema Bank, Fidelity Bank, Sterling Bank, Polaris Bank
- Fintech: Flutterwave, Paystack, Moniepoint (formerly TeamApt), OPay, PalmPay, Carbon, FairMoney, Piggyvest/Rise, Kuda Bank
- Investment banks: Chapel Hill Denham, Stanbic IBTC Stockbrokers, ARM Securities, Vetiva Capital
- Microfinance: LAPO, Accion, AB Microfinance, AB Microfinance Bank

CONGLOMERATES & MAJOR COMPANIES:
- Dangote Group: Dangote Cement, BUA Cement, Dangote Sugar, Dangote Fertiliser, NLNG partner
- BUA Group: BUA Foods, BUA Cement, Flour Mills of Nigeria
- Flour Mills of Nigeria, Nestle Nigeria, Nigerian Breweries (Heineken), Guinness Nigeria
- MTN Nigeria, Airtel Africa, Glo (Globacom), 9mobile
- Seplat Energy (E&P), NNPC/NNPCL (now Nigerian National Petroleum Corporation Limited), Oando Energy
- Chicken Republic, Shoprite Nigeria, SPAR Nigeria, Jumia Nigeria, Konga
- Innoson Vehicle Manufacturing (IVM), Zinox Technologies

COMMODITY MARKETS & SUPPLY CHAINS:
- Mile 12 International Market (Lagos — vegetables, tomatoes, onions)
- Dawanau Grain Market (Kano — grains, particularly groundnuts)
- Bodija Market (Ibadan — livestock, yam)
- Shasha Market (Lagos — raw commodities)
- Computer Village Ikeja (electronics)
- Aba Market (Aba — leather, textiles, manufactured goods)
- LCFE = Lagos Commodity & Futures Exchange
- AFEX = African Farmer Exchange (grains, rice, maize, soybean warehouse receipts)
- FMARD anchor borrowers programme (rice, wheat, maize, cassava, soybeans, palm oil)
- Key crops: rice, maize, cassava, sorghum, millet, cocoa, sesame, palm oil, cashew

CURRENCY & FX (critical for Nigerian signals):
- NGN = Nigerian Naira. Always flag BOTH official NAFEX/I&E rate AND parallel/black market rates.
- Common metrics: USD/NGN official rate, USD/NGN parallel rate, NGN/USD rate, spread between official and parallel
- Common units: ₦ per bag (wheat, rice), ₦ per litre (fuel, diesel, kerosene), ₦ per tonne (cement, fertiliser)
- FX policy terms: NAFEX window, I&E FX window, CBN intervention, BDC (Bureau De Change), aboki FX

ENERGY & INFRASTRUCTURE:
- NNPCL (formerly NNPC), Nigerian Agip Oil Company, Shell Petroleum Development Company (SPDC), TotalEnergies Nigeria, Chevron Nigeria
- GenCos: Geregu, Transcorp Ughelli, Azura-Edo (AEP), Egbin, Kainji/Jebba hydro, Afam (SPDC)
- DisCos: EKEDC (Eko), IKEDC (Ikeja), BEDC (Benin), PHEDC (Port Harcourt), AEDC (Abuja), KEDCO (Kano), JEDC (Jos), YEDC (Yola), KAEDCO (Kaduna), CHEDC (Enugu)
- Pipelines: Trans-Niger Pipeline, Escravos-Lagos Pipeline, AKK Gas Pipeline
- Lekki Deep Sea Port, Apapa Port (Lagos), Tin Can Island Port, Onne Port (Rivers)

GEOGRAPHIC PRECISION (state-level is critical):
- Southwest: Lagos (FCT equivalent commercially), Ogun, Oyo, Osun, Ekiti, Ondo
- Southeast: Anambra, Imo, Abia, Enugu, Ebonyi
- South-South: Rivers (Port Harcourt), Delta, Edo, Bayelsa, Cross River, Akwa Ibom
- North-Central: Abuja (FCT), Kogi, Niger, Benue, Plateau, Kwara, Nasarawa
- Northwest: Kano, Kaduna, Zamfara, Kebbi, Sokoto, Jigawa, Katsina
- Northeast: Borno, Adamawa, Taraba, Bauchi, Gombe, Yobe

INFORMAL ECONOMY ACTORS (valid entities for Nigerian signals):
- Okada riders, Keke NAPEP (tricycle) unions, market associations (e.g. Amalgamated Union of Foodstuff Sellers)
- Alaba electronics market traders, Idumota, Balogun (textiles)
- Petroleum tanker drivers, NUPENG (petroleum workers), PENGASSAN
- Open market cobblers, tailors, artisan cooperatives (Aba)

ABBREVIATIONS MOST COMMONLY CONFUSED:
- CBN = Central Bank of Nigeria (NOT Columbus, Nebraska)
- SEC = Securities and Exchange Commission Nigeria (NOT US SEC unless context is global)
- CAC = Corporate Affairs Commission (NOT CAC 40)
- NGN = Nigerian Naira currency
- FCT = Federal Capital Territory (Abuja)
- ASUU = Academic Staff Union of Universities (recurring strike actor)
- NLC = Nigeria Labour Congress (nationwide strikes)
- TUC = Trade Union Congress Nigeria""",
    "KEN": """Important context for Kenyan entity recognition:
- Kenyan regulators: CBK (Central Bank of Kenya), CMA, CA, EPRA, KEBS, KRA, NEMA, NTSA, HELB
- Major Kenyan companies: Safaricom, Equity Group, KCB Group, East African Breweries, Bamburi Cement, BAT Kenya, Kenya Airways
- Kenyan counties: Nairobi, Mombasa, Kisumu, Nakuru, Kiambu, Machakos, Kajiado, etc.
- Markets: NSE (Nairobi Securities Exchange), KACE (Kenya Agri Commodity Exchange)
- Currency: KES (Kenya Shilling). M-Pesa is critical financial infrastructure.
- Abbreviations: "CBK" = Central Bank of Kenya, "CMA" = Capital Markets Authority""",
    "GHA": """Important context for Ghanaian entity recognition:
- Ghanaian regulators: BoG (Bank of Ghana), SEC, NCA, PURC, NPA, GRA, FDA, GSA, GIPC
- Major Ghanaian companies: MTN Ghana, Newmont Ghana, Gold Fields, AGA (AngloGold Ashanti), Tullow Oil, CalBank, GCB Bank, Ecobank Ghana
- Ghanaian regions: Greater Accra, Ashanti, Western, Northern, Eastern, Central, etc.
- Markets: GSE (Ghana Stock Exchange), GCX (Ghana Commodity Exchange)
- Currency: GHS (Ghana Cedi). Cocoa Board (COCOBOD) is major commodity regulator.
- Abbreviations: "BoG" = Bank of Ghana, "COCOBOD" = Ghana Cocoa Board""",
    "ZAF": """Important context for South African entity recognition:
- SA regulators: SARB (South African Reserve Bank), FSCA, ICASA, NERSA, CompCom, CIPC, SARS, DTIC
- Major SA companies: Naspers/Prosus, Anglo American, Sasol, MTN Group, Shoprite, Standard Bank, FirstRand, Absa, Discovery, Vodacom
- SA provinces: Gauteng, Western Cape, KwaZulu-Natal, Eastern Cape, Limpopo, Mpumalanga, etc.
- Markets: JSE (Johannesburg Stock Exchange), SAFEX
- Currency: ZAR (Rand). Load-shedding and Eskom are recurring economic factors.
- Abbreviations: "SARB" = SA Reserve Bank, "JSE" = Johannesburg Stock Exchange""",
    "EGY": """Important context for Egyptian entity recognition:
- Egyptian regulators: CBE (Central Bank of Egypt), FRA, NTRA, EgyptERA, GAFI, ETA, CAPMAS
- Major Egyptian companies: CIB (Commercial International Bank), EFG Hermes, Orascom, Elsewedy Electric, Talaat Moustafa, Orange Egypt, Telecom Egypt
- Egyptian governorates: Cairo, Alexandria, Giza, Qalyubia, Sharqia, Dakahlia, etc.
- Markets: EGX (Egyptian Exchange), Alexandria Cotton Exchange
- Currency: EGP (Egyptian Pound). Suez Canal revenue is key economic indicator.
- Abbreviations: "CBE" = Central Bank of Egypt, "EGX" = Egyptian Exchange""",
    "TZA": """Important context for Tanzanian entity recognition:
- Tanzanian regulators: BoT (Bank of Tanzania), CMSA, TCRA, EWURA, TRA, TBS, TFDA, BRELA
- Major Tanzanian companies: CRDB Bank, NMB Bank, Tanzania Breweries (TBL), Vodacom Tanzania, Tigo Tanzania, Twiga Cement, Tanzania Cigarette Company
- Tanzanian regions: Dar es Salaam, Dodoma, Arusha, Mwanza, Mbeya, Morogoro, Zanzibar, etc.
- Markets: DSE (Dar es Salaam Stock Exchange), TMRC (Tanzania Mercantile Exchange)
- Currency: TZS (Tanzanian Shilling). Mining sector (gold, tanzanite) and agriculture (cashew, sisal, coffee) are dominant.
- Abbreviations: "BoT" = Bank of Tanzania, "DSE" = Dar es Salaam Stock Exchange""",
    "ETH": """Important context for Ethiopian entity recognition:
- Ethiopian regulators: NBE (National Bank of Ethiopia), ECA (Ethiopian Capital Market Authority), ETA, ERA, ECSA
- Major Ethiopian companies: Ethiopian Airlines, Ethio Telecom, Commercial Bank of Ethiopia (CBE), Awash Bank, Dashen Bank, BGI Ethiopia, MIDROC
- Ethiopian regions: Addis Ababa, Oromia, Amhara, SNNPR, Tigray, Somali, Dire Dawa, etc.
- Markets: ESX (Ethiopian Securities Exchange, newly launched), ECX (Ethiopian Commodity Exchange — sesame, coffee)
- Currency: ETB (Ethiopian Birr). Grand Ethiopian Renaissance Dam (GERD) and telecom liberalization are major economic themes.
- Abbreviations: "NBE" = National Bank of Ethiopia, "ECX" = Ethiopian Commodity Exchange""",
    "CIV": """Important context for Ivorian entity recognition:
- Ivorian regulators: BCEAO (shared with WAEMU), CREPMF (WAEMU regional securities regulator), ARTCI, ANRMP, DGI
- Major Ivorian companies: Orange Côte d'Ivoire, MTN CI, Société Ivoirienne de Banque (SIB), SODECI, CIE, Bolloré Africa Logistics, SIFCA Group
- Ivorian districts: Abidjan, Yamoussoukro, Bouaké, San-Pédro, Daloa, Korhogo, etc.
- Markets: BRVM (Bourse Régionale des Valeurs Mobilières — regional WAEMU exchange based in Abidjan)
- Currency: XOF (CFA Franc — shared WAEMU zone). World's largest cocoa producer.
- Abbreviations: "BRVM" = regional WAEMU stock exchange, "BCEAO" = Central Bank of West African States""",
    "MAR": """Important context for Moroccan entity recognition:
- Moroccan regulators: BAM (Bank Al-Maghrib), AMMC, ANRT, ANRE, DGI, OMPIC, MASEN
- Major Moroccan companies: OCP Group (phosphates), Maroc Telecom (IAM), Attijariwafa Bank, BMCE/Bank of Africa, CDG, Managem, ONCF, Royal Air Maroc
- Moroccan regions: Casablanca-Settat, Rabat-Salé-Kénitra, Marrakech-Safi, Fès-Meknès, Tanger-Tétouan-Al Hoceïma, etc.
- Markets: Casablanca Stock Exchange (CSE/BVC), MAS Commodities
- Currency: MAD (Moroccan Dirham). OCP and phosphate exports, automotive/aeronautics FDI zones (Tanger Med) are key economic drivers.
- Abbreviations: "BAM" = Bank Al-Maghrib, "OCP" = Office Chérifien des Phosphates""",
    "RWA": """Important context for Rwandan entity recognition:
- Rwandan regulators: BNR (National Bank of Rwanda), CMA, RURA, RRA, RISA, RICA
- Major Rwandan companies: MTN Rwanda, Bank of Kigali (BK), I&M Bank Rwanda, Bralirwa (Heineken), Rwanda Energy Group (REG), RwandAir
- Rwandan provinces: Kigali, Eastern, Western, Northern, Southern
- Markets: RSE (Rwanda Stock Exchange), NAEB (National Agricultural Export Development Board — coffee/tea)
- Currency: RWF (Rwandan Franc). ICT/fintech hub ambitions, Kigali International Financial Centre (KIFC).
- Abbreviations: "BNR" = National Bank of Rwanda, "KIFC" = Kigali International Financial Centre""",
}

# Default (pan-African) context when country is not specified or not in REGIONAL_CONTEXT
DEFAULT_REGIONAL_CONTEXT = """Important context for African entity recognition:
- Pan-African institutions: AfDB (African Development Bank), AU (African Union), AfCFTA, Afreximbank, AFC
- Regional bodies: ECOWAS, EAC, SADC, COMESA, AMU/UMA
- Major pan-African companies: MTN Group, Dangote Group, Safaricom, Naspers, Equity Group, Standard Bank, Ecobank
- Commodity exchanges: AFEX, LCFE, GCX, KACE, SAFEX, EGX
- Key currencies: NGN, KES, GHS, ZAR, EGP, XOF (CFA Franc)
- Cross-border infrastructure: Lekki Deep Sea Port, SGR, Trans-Sahara Pipeline, Grand Ethiopian Renaissance Dam
- Abbreviations vary by country — extract full name when possible"""


def _build_system_prompt(country: str | None = None) -> str:
    """Build the NER system prompt with the right regional context."""
    regional = REGIONAL_CONTEXT.get(country or "", DEFAULT_REGIONAL_CONTEXT)
    return f"""You are an expert intelligence analyst specializing in African markets.
Your job is to extract structured intelligence from signal text.

You MUST extract:
1. ENTITIES: Organizations, companies, people, products, regulatory bodies, commodities, infrastructure
2. NUMERIC_DATA: Prices, percentages, volumes, rates, amounts with their context
3. GEOGRAPHIC: Countries, states/regions, cities, markets mentioned
4. SOURCES: URLs, data sources, publications referenced in the text

{regional}

For confidence scoring:
- 1.0: Explicit, unambiguous mention with full name
- 0.9: Clear mention, possibly abbreviated but obvious in context
- 0.8: Strong contextual inference
- 0.7: Likely entity but some ambiguity
- 0.6: Possible entity, context-dependent
- Below 0.6: Don't include

Return valid JSON only. No markdown, no explanation."""


EXTRACTION_USER_TEMPLATE = """Extract structured intelligence from this signal:

TITLE: {title}

CONTENT:
{content}

Return JSON with this exact structure:
{{
  "entities": [
    {{
      "name": "Full entity name",
      "entity_type": "company|person|product|regulator|commodity|infrastructure|financial_institution|cooperative",
      "confidence": 0.0-1.0,
      "context": "Brief context of how entity is mentioned",
      "aliases": ["Optional", "alternative", "names"]
    }}
  ],
  "numeric_data": [
    {{
      "value": 123.45,
      "unit": "currency|percentage|volume|count|rate|index|weight",
      "metric": "What this number represents",
      "currency": "NGN|USD|null",
      "context": "Brief context"
    }}
  ],
  "geographic": [
    {{
      "name": "Place name",
      "geo_type": "country|state|city|region|market",
      "country_code": "NGA|null",
      "parent_region": "West Africa|null"
    }}
  ],
  "sources": [
    {{
      "url": "https://...",
      "name": "Source name if identifiable",
      "source_type": "news|api|government|social|research"
    }}
  ]
}}"""


# ── Entity Extraction Service ────────────────────────────────────────


class EntityExtractionService:
    """LLM-based entity and structured data extraction.

    Uses GPT-4o to extract entities, numeric data, geographic mentions,
    and source references from signal text. Africa/Nigeria-aware.

    Usage:
        service = EntityExtractionService()
        result = await service.extract(signal)
    """

    def __init__(self, model: str = "gpt-4o", country: str | None = None):
        self.model = model
        self.country = country  # ISO 3166-1 alpha-3 (e.g., 'NGA')
        self.client = _get_client()

    async def extract(
        self,
        *,
        title: str | None = None,
        content: str | None = None,
        country: str | None = None,
        feedback: str | None = None,
        max_content_length: int = 4000,
    ) -> ExtractionResult:
        """Extract entities and structured data from signal text.

        Args:
            title: Signal title.
            content: Signal body text (summary + raw_content).
            country: ISO 3166-1 alpha-3 override (defaults to self.country).
            feedback: Optional feedback block from reviewed entities.
            max_content_length: Max content chars to send to LLM.

        Returns:
            ExtractionResult with entities, numeric data, geographic, sources.
        """
        if not title and not content:
            return ExtractionResult()

        # Truncate content to control token usage
        text_content = (content or "")[:max_content_length]
        text_title = title or ""

        # Skip very short content (unlikely to contain meaningful entities)
        if len(text_title) + len(text_content) < 20:
            return ExtractionResult()

        user_prompt = EXTRACTION_USER_TEMPLATE.format(
            title=text_title,
            content=text_content,
        )

        # Build region-aware system prompt + optional feedback
        effective_country = country or self.country
        system_prompt = _build_system_prompt(effective_country)
        if feedback:
            system_prompt += feedback

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for extraction accuracy
                max_tokens=2000,
            )

            raw_text = response.choices[0].message.content or "{}"
            tokens_used = response.usage.total_tokens if response.usage else 0

            return self._parse_response(raw_text, tokens_used)

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return ExtractionResult()

    async def extract_from_signal(self, signal: Any) -> ExtractionResult:
        """Extract from a Signal ORM instance.

        Convenience wrapper that pulls title/summary/raw_content from signal.
        """
        parts = []
        if signal.summary:
            parts.append(signal.summary)
        if signal.raw_content:
            parts.append(signal.raw_content)
        content = "\n\n".join(parts) if parts else None

        # Infer country from signal's contract if available
        signal_country = None
        if hasattr(signal, "extracted_data") and signal.extracted_data:
            signal_country = signal.extracted_data.get("country_code")

        return await self.extract(
            title=signal.title,
            content=content,
            country=signal_country,
        )

    def _parse_response(self, raw_text: str, tokens_used: int) -> ExtractionResult:
        """Parse the LLM JSON response into typed dataclasses."""
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error("Entity extraction returned invalid JSON")
            return ExtractionResult()

        result = ExtractionResult(
            raw_response=data,
            extraction_model=self.model,
            tokens_used=tokens_used,
        )

        # Parse entities
        for e in data.get("entities", []):
            try:
                if not e.get("name") or len(e["name"]) < 2:
                    continue
                confidence = float(e.get("confidence", 0.7))
                if confidence < 0.6:
                    continue  # Filter low-confidence noise
                result.entities.append(
                    EntityMention(
                        name=e["name"].strip(),
                        entity_type=e.get("entity_type", "company"),
                        confidence=confidence,
                        context=e.get("context", "")[:300],
                        aliases=e.get("aliases", []),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.debug(f"Skipping malformed entity: {exc}")

        # Parse numeric data
        for n in data.get("numeric_data", []):
            try:
                result.numeric_data.append(
                    NumericDataPoint(
                        value=float(n["value"]),
                        unit=n.get("unit", "unknown"),
                        metric=n.get("metric", ""),
                        currency=n.get("currency"),
                        context=n.get("context", "")[:300],
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.debug(f"Skipping malformed numeric data: {exc}")

        # Parse geographic mentions
        for g in data.get("geographic", []):
            try:
                if not g.get("name"):
                    continue
                result.geographic.append(
                    GeographicMention(
                        name=g["name"].strip(),
                        geo_type=g.get("geo_type", "region"),
                        country_code=g.get("country_code"),
                        parent_region=g.get("parent_region"),
                    )
                )
            except (KeyError, TypeError) as exc:
                logger.debug(f"Skipping malformed geographic: {exc}")

        # Parse source references
        for s in data.get("sources", []):
            try:
                url = s.get("url", "").strip()
                if not url or not url.startswith("http"):
                    continue
                result.sources.append(
                    SourceReference(
                        url=url,
                        name=s.get("name"),
                        source_type=s.get("source_type"),
                    )
                )
            except (KeyError, TypeError) as exc:
                logger.debug(f"Skipping malformed source: {exc}")

        logger.info(
            f"Extracted {len(result.entities)} entities, "
            f"{len(result.numeric_data)} numeric points, "
            f"{len(result.geographic)} locations, "
            f"{len(result.sources)} sources "
            f"({tokens_used} tokens)"
        )
        return result

    @staticmethod
    async def get_feedback_examples(db: Any, *, limit: int = 10) -> str:
        """Build a feedback block from recently reviewed entities.

        When admins approve or reject auto-extracted entities, we can use
        those decisions as few-shot examples to improve future extraction.

        Returns an empty string if no reviewed entities exist yet.
        """
        from sqlalchemy import or_, select

        from backend.models.entity import Entity

        result = await db.execute(
            select(Entity.name, Entity.entity_type, Entity.discovery_status)
            .where(
                Entity.discovery_source == "auto_extracted",
                or_(
                    Entity.discovery_status == "active",  # approved
                    Entity.discovery_status == "rejected",
                ),
            )
            .order_by(Entity.updated_at.desc())
            .limit(limit)
        )
        rows = result.all()
        if not rows:
            return ""

        approved = [r for r in rows if r.discovery_status == "active"]
        rejected = [r for r in rows if r.discovery_status == "rejected"]

        lines = ["\n\nFeedback from human reviewers (use to calibrate):"]
        if approved:
            lines.append("CORRECTLY extracted (keep extracting these):")
            for r in approved[:5]:
                lines.append(f"  ✓ {r.name} ({r.entity_type})")
        if rejected:
            lines.append("INCORRECTLY extracted (avoid these patterns):")
            for r in rejected[:5]:
                lines.append(f"  ✗ {r.name} ({r.entity_type})")

        return "\n".join(lines)
