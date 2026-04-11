/**
 * TypeScript types that mirror the backend Pydantic response schemas.
 *
 * These are the SOURCE OF TRUTH for all API response shapes.
 * When the backend changes a schema, update the corresponding type here.
 *
 * Convention:  every type name matches the backend class name exactly so
 *              that cross-referencing is effortless.
 */

// ── Pagination ───────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export interface UserInfo {
  id: string;
  auth0_id: string;
  email: string;
}

export interface OrgInfo {
  id: string;
  role: string;
}

export interface SubscriptionInfo {
  plan: string;
}

export interface TokenInfo {
  expires_at: string;
}

export interface CurrentUserResponse {
  user: UserInfo;
  organization: OrgInfo;
  subscription: SubscriptionInfo;
  permissions: Record<string, boolean>;
  token: TokenInfo;
}

export interface PermissionsResponse {
  user_id: string;
  org_id: string;
  role: string;
  permissions: Record<string, boolean>;
}

export interface TokenVerifyResponse {
  valid: boolean;
  user_id: string;
  org_id: string;
  expires_at: string;
}

// ── Users ────────────────────────────────────────────────────────────────────

export interface UserProfileResponse {
  id: string;
  auth0_id: string;
  email: string;
  name: string | null;
  picture_url: string | null;
  created_at: string;
  last_login_at: string | null;
}

export interface UserProfileUpdate {
  name?: string;
  picture_url?: string;
}

// ── Organizations ────────────────────────────────────────────────────────────

export interface OrganizationResponse {
  id: string;
  name: string;
  slug: string;
  created_at: string;
}

export interface OrganizationUpdate {
  name?: string;
  slug?: string;
}

export interface MemberResponse {
  user_id: string;
  role: string;
  status: string;
  joined_at: string;
}

export interface MemberListResponse {
  members: MemberResponse[];
  total: number;
  skip: number;
  limit: number;
}

export interface AddMemberRequest {
  email: string;
  role?: string;
}

export interface MemberRoleUpdate {
  role: string;
}

// ── Signals ──────────────────────────────────────────────────────────────────

export interface SignalProvenanceResponse {
  pipeline_version: string | null;
  ner_model: string | null;
  ner_tokens: number;
  country_context: string | null;
  entities_found: number;
  numeric_data_found: number;
  sources_found: number;
  score_breakdown: Record<string, number>;
  stages: Record<string, unknown>;
  refined_at: number | null;
}

export interface SignalResponse {
  id: string;
  contract_id: string;
  org_id: string | null;
  title: string | null;
  summary: string | null;
  source_url: string | null;
  signal_type: string;
  confidence: number;
  content_hash: string | null;
  fetched_at: string;
  published_at: string | null;
  expires_at: string | null;
  extracted_data: Record<string, unknown>;
  // Versioning & lineage
  version: number;
  superseded_by_id: string | null;
  amended_at: string | null;
  provenance: SignalProvenanceResponse | null;
  created_at: string;
}

export interface SignalDetailResponse extends SignalResponse {
  raw_content: string | null;
}

export interface IntelligenceSignalResponse extends SignalResponse {
  anomaly_score: number | null;
  trending_score: number | null;
  top_entities: Array<Record<string, unknown>>;
  causal_summary: string | null;
  causal_event_type: string | null;
  regulatory_flag: string | null;
  regulatory_body: string | null;
  primary_country: string | null;
  primary_region: string | null;
}

export type SignalListResponse = PaginatedResponse<SignalResponse>;

// ── Signal Marketplace ───────────────────────────────────────────────────────

export interface SignalTemplateResponse {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  short_description: string | null;
  industry_id: string;
  signal_type: string;
  primary_country: string | null;
  regions: string[];
  tags: string[];
  source_type: string;
  schedule_tier: string;
  is_official: boolean;
  is_featured: boolean;
  subscription_count: number;
  preview_signal_count: number;
  is_subscribed: boolean;
}

export interface SignalTemplateListResponse {
  items: SignalTemplateResponse[];
  total: number;
  skip: number;
  limit: number;
}

export interface SubscribeResponse {
  subscription_id: string;
  contract_id: string;
  template_id: string;
  message: string;
}

// ── Contracts ────────────────────────────────────────────────────────────────

export interface SignalContractResponse {
  id: string;
  name: string;
  description: string | null;
  industry_id: string;
  entity_id: string | null;
  source_url: string;
  source_type: string;
  refresh_cron: string;
  schedule_tier: string;
  extraction_config: Record<string, unknown>;
  is_active: boolean;
  status: string;
  failure_count: number;
  max_failures: number;
  last_fetched_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export type SignalContractListResponse =
  PaginatedResponse<SignalContractResponse>;

export interface SignalContractCreate {
  name: string;
  description?: string;
  industry_id: string;
  entity_id?: string;
  source_url: string;
  source_type: string;
  refresh_cron?: string;
  schedule_tier?: string;
  extraction_config?: Record<string, unknown>;
  is_active?: boolean;
}

export interface SignalContractUpdate {
  name?: string;
  description?: string;
  source_url?: string;
  source_type?: string;
  refresh_cron?: string;
  schedule_tier?: string;
  extraction_config?: Record<string, unknown>;
  is_active?: boolean;
}

// ── Briefs ───────────────────────────────────────────────────────────────────

export interface BriefSignalLink {
  signal_id: string;
  relevance_rank: number;
}

export interface BriefResponse {
  id: string;
  org_id: string | null;
  industry_id: string;
  title: string;
  brief_type: string;
  bluf: string | null;
  body_json: Record<string, unknown>;
  outlook: string | null;
  decision_lens: string | null;
  status: string;
  refreshed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BriefDetailResponse extends BriefResponse {
  signal_links: BriefSignalLink[];
}

export type BriefListResponse = PaginatedResponse<BriefResponse>;

export interface BriefGenerateRequest {
  industry_id?: string;
  brief_type?: string;
  signal_ids?: string[];
  focus_area?: string;
}

export interface BriefGenerateResponse {
  brief_id: string;
  title: string;
  status: string;
  signal_count: number;
}

export interface BriefRegenerateRequest {
  focus_area?: string;
}

export interface BriefStatusUpdate {
  status: string;
}

export interface BriefRefreshResponse {
  brief_id: string;
  status: string;
  signals_added: number;
}

export interface BriefRefreshBatchResponse {
  refreshed: number;
  failed: number;
  details: Array<{ brief_id: string; status: string }>;
}

// ── Search ───────────────────────────────────────────────────────────────────

export interface SearchRequest {
  query: string;
  max_results?: number;
  min_confidence?: number;
  include_synthesis?: boolean;
}

export interface SearchResultItem {
  signal_id: string | null;
  title: string | null;
  summary: string | null;
  signal_type: string | null;
  confidence: number;
  similarity: number;
  freshness_score: number;
  composite_score: number;
  source_url: string | null;
  published_at: string | null;
  is_live_web?: boolean;
  source?: string | null;
}

export interface WebSearchResultItem {
  title: string | null;
  snippet: string | null;
  url: string | null;
  source: string | null;
  position?: number | null;
  published_at?: string | null;
  relevance_score?: number | null;
  confidence?: number | null;
}

export interface SearchResponse {
  query: string;
  results: SearchResultItem[];
  web_results: WebSearchResultItem[];
  synthesis: string | null;
  total_results: number;
  web_result_count: number;
  response_time_ms: number;
  cached: boolean;
}

export interface SearchHistoryItem {
  id: string;
  query_text: string;
  source_count: number;
  response_time_ms: number | null;
  created_at: string;
}

export type SearchHistoryResponse = PaginatedResponse<SearchHistoryItem>;

// ── Synthesis ────────────────────────────────────────────────────────────────

export interface SynthesisRequest {
  query: string;
  signal_ids?: string[];
  context?: string;
  include_web_search?: boolean;
}

export interface SynthesisWebSource {
  title: string | null;
  url: string | null;
  source: string | null;
  snippet?: string | null;
}

export interface SynthesisResponse {
  synthesis: string;
  signal_count: number;
  confidence: number;
  web_sources?: SynthesisWebSource[];
}

// ── Chat ─────────────────────────────────────────────────────────────────────

export interface ChatMessageResponse {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources_json: Record<string, unknown> | null;
  token_count: number | null;
  created_at: string;
}

export interface ChatSessionResponse {
  id: string;
  user_id: string;
  org_id: string;
  industry_id: string | null;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionDetailResponse extends ChatSessionResponse {
  messages: ChatMessageResponse[];
}

export type ChatSessionListResponse = PaginatedResponse<ChatSessionResponse>;

export interface CreateSessionRequest {
  industry_slug?: string;
  title?: string;
}

export interface SendMessageRequest {
  message: string;
}

export interface ChatDeleteResponse {
  deleted: boolean;
  session_id: string;
}

// ── Pricing ──────────────────────────────────────────────────────────────────

export interface PricingSummaryResponse {
  tier: string;
  standard_price: number;
  subscription_price: number;
  overage_cost: number;
  total_monthly_cost: number;
  subscription?: BillingSubscriptionResponse | null;
}

export interface FeatureAccessResponse {
  tier: string;
  role: string;
  features: Record<string, boolean>;
}

export interface TierUpgradeRequest {
  target_tier: string;
  callback_url?: string;
}

export interface TierUpgradeResponse {
  status: string;
  requested_tier: string;
  message: string;
  reference: string;
  access_code: string | null;
  authorization_url: string | null;
  public_key?: string | null;
}

export interface VerifyTierCheckoutRequest {
  reference: string;
}

export interface VerifyTierCheckoutResponse {
  status: string;
  tier: string;
  message: string;
  reference: string;
  transaction_status: string | null;
}

export interface BillingSubscriptionResponse {
  provider: string | null;
  status: string | null;
  plan_tier: string | null;
  billing_cycle: string | null;
  currency: string | null;
  price_cents: number | null;
  latest_reference: string | null;
  current_period_start: string | null;
  current_period_end: string | null;
  canceled_at: string | null;
  provider_customer_code: string | null;
  provider_subscription_code: string | null;
  provider_plan_code: string | null;
  can_cancel: boolean;
}

export interface CancelSubscriptionResponse {
  status: string;
  message: string;
}

// ── Credits ──────────────────────────────────────────────────────────────────

export interface CreditBalanceResponse {
  allocated: number;
  consumed: number;
  remaining: number;
  overage: number;
  overage_rate: number;
  strict_prepaid_enabled?: boolean;
}

export interface CreditTransactionResponse {
  id: string;
  action_type: string;
  credits_consumed: number;
  credits_remaining: number;
  created_at: string;
  metadata?: Record<string, unknown> | null;
}

export interface CreditTransactionsResponse {
  transactions: CreditTransactionResponse[];
  total: number;
}

// ── Entities ─────────────────────────────────────────────────────────────────

export interface EntityResolveRequest {
  name: string;
  entity_type?: string;
}

export interface EntityResolveResponse {
  entity_id: string;
  name: string;
  entity_type: string;
  confidence: number;
}

export interface EntityCreateRequest {
  name: string;
  entity_type: string;
  metadata?: Record<string, unknown>;
}

export interface EntityCreateResponse {
  id: string;
  name: string;
  entity_type: string;
  created_at: string;
}

export interface EntityProfileResponse {
  id: string;
  name: string;
  entity_type: string;
  metadata: Record<string, unknown>;
  signal_count: number;
  first_seen: string;
  last_seen: string;
}

export interface EntityNetworkNode {
  id: string;
  name: string;
  entity_type: string;
}

export interface EntityNetworkEdge {
  source_id: string;
  target_id: string;
  relationship_type: string;
  weight: number;
}

export interface EntityNetworkResponse {
  entity_id: string;
  nodes: EntityNetworkNode[];
  edges: EntityNetworkEdge[];
}

// ── Entity Discovery ─────────────────────────────────────────────────────────

export interface EntityDiscoveryItem {
  id: string;
  name: string;
  entity_type: string;
  discovery_status: "active" | "pending_review" | "rejected";
  discovery_source: "seed" | "auto_extracted" | "agent" | "manual";
  created_at: string;
}

export interface EntityReviewRequest {
  action: "approve" | "reject";
}

export interface EntityReviewResponse {
  entity_id: string;
  name: string;
  discovery_status: string;
}

// ── Discovered Sources ───────────────────────────────────────────────────────

export interface DiscoveredSourceResponse {
  id: string;
  url: string;
  domain: string;
  name: string | null;
  source_type: string;
  signal_type: string | null;
  mention_count: number;
  relevance_score: number;
  status: "discovered" | "recommended" | "activated" | "dismissed";
  activated_contract_id: string | null;
  created_at: string;
  last_seen_at: string;
}

export interface DiscoveredSourceStatsResponse {
  discovered: number;
  recommended: number;
  activated: number;
  dismissed: number;
  total: number;
}

export interface ActivateSourceRequest {
  industry_id: string;
  name?: string;
  description?: string;
}

export interface ActivateSourceResponse {
  source_id: string;
  contract_id: string;
  contract_name: string;
  source_url: string;
  source_type: string;
  schedule_tier: string;
  message: string;
}

// ── Market Data ──────────────────────────────────────────────────────────────

export interface MarketDataPointResponse {
  id: string;
  metric: string;
  value: number;
  unit: string;
  currency: string | null;
  observed_at: string;
  signal_id: string | null;
  entity_id: string | null;
  country_code: string | null;
  region: string | null;
  context: string | null;
  confidence: number;
  created_at: string;
}

export type MarketDataListResponse = PaginatedResponse<MarketDataPointResponse>;

export interface MetricSummary {
  metric: string;
  count: number;
  latest_value: number | null;
  latest_observed_at: string | null;
  min_value: number | null;
  max_value: number | null;
  avg_value: number | null;
  unit: string | null;
  currency: string | null;
}

export interface MarketDataStatsResponse {
  total_points: number;
  unique_metrics: number;
  countries_covered: number;
  metrics: MetricSummary[];
}

export interface LatestValueResponse {
  metric: string;
  value: number;
  unit: string;
  currency: string | null;
  observed_at: string;
  country_code: string | null;
  signal_id: string | null;
}

// ── Recommendations ──────────────────────────────────────────────────────────

export interface RecommendationResponse {
  id: string;
  signal_id: string;
  recommendation_type: string;
  title: string;
  description: string;
  confidence: number;
  created_at: string;
}

export type RecommendationListResponse =
  PaginatedResponse<RecommendationResponse>;

export interface RecommendationBatchResponse {
  generated: number;
  failed: number;
}

// ── Causal ───────────────────────────────────────────────────────────────────

export interface CausalChainResponse {
  id: string;
  event_type: string;
  chain: Array<{ event: string; probability: number }>;
  confidence: number;
}

export interface ImpactPredictionResponse {
  event_type: string;
  predictions: Array<{
    impact: string;
    probability: number;
    timeframe: string;
  }>;
}

export interface GrangerTestRequest {
  cause_series: string;
  effect_series: string;
  max_lag?: number;
}

export interface GrangerTestResponse {
  is_causal: boolean;
  p_value: number;
  optimal_lag: number;
  f_statistic: number;
}

export interface SignalImpactResponse {
  signal_id: string;
  impact_score: number;
  affected_entities: string[];
  cascading_effects: string[];
}

// ── Feedback ─────────────────────────────────────────────────────────────────

export interface FeedbackRequest {
  feedback_type: string;
  target_type: "signal" | "brief" | "entity" | "prediction";
  target_id: string;
  comment?: string;
  context?: Record<string, unknown>;
}

export interface FeedbackResponse {
  id: string;
  feedback_type: string;
  target_type: string;
  target_id: string;
  sentiment: number;
}

export interface SignalQualityResponse {
  signal_id: string;
  quality_score: number;
  total_votes: number;
  useful_votes: number;
  not_useful_votes: number;
  saves: number;
  shares: number;
}

export interface TrendingSignalResponse {
  signal_id: string;
  title: string;
  trending_score: number;
  feedback_count: number;
}

// ── Features ─────────────────────────────────────────────────────────────────

export interface FeaturesResponse {
  features: Record<string, boolean>;
}

// ── Admin ────────────────────────────────────────────────────────────────────

export interface PricingModeResponse {
  mode: string;
}

export interface PricingModeRequest {
  mode: "standard";
}

// ── Pipeline ─────────────────────────────────────────────────────────────────

export interface PipelineStatusResponse {
  status: string;
  last_run: string | null;
  next_run: string | null;
  active_jobs: number;
}

export interface FetchTierRequest {
  tier: string;
  contract_ids?: string[];
}

// ── ML ───────────────────────────────────────────────────────────────────────

export interface SignalScoresResponse {
  signal_id: string;
  scores: Record<string, number>;
  model_version: string;
}

export interface MLStatusResponse {
  status: string;
  models_loaded: number;
  last_training: string | null;
}

export interface MLModelRunResponse {
  id: string;
  model_name: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  metrics: Record<string, number>;
}

export interface MLModelRegistryResponse {
  name: string;
  version: string;
  status: string;
  accuracy: number;
  created_at: string;
}

export interface TrainingRequest {
  model_name: string;
  parameters?: Record<string, unknown>;
}

export interface TrainingResponse {
  job_id: string;
  model_name: string;
  status: string;
}

// ── Monitoring ───────────────────────────────────────────────────────────────

export interface SLOMetricsResponse {
  uptime: number;
  latency_p50: number;
  latency_p99: number;
  error_rate: number;
}

export interface CacheMetricsResponse {
  hit_rate: number;
  miss_rate: number;
  total_keys: number;
  memory_used: number;
}

export interface CircuitBreakerResponse {
  breakers: Array<{
    name: string;
    state: string;
    failure_count: number;
    last_failure: string | null;
  }>;
}

// ── Situation Room ───────────────────────────────────────────────────────────

export interface SignalFeedItem {
  id: string;
  title: string | null;
  summary: string | null;
  signal_type: string;
  source_url: string | null;
  confidence: number;
  priority: "critical" | "high" | "medium" | "low";
  published_at: string | null;
  fetched_at: string;
  is_anomaly: boolean;
  anomaly_score: number | null;
  trending_score: number | null;
  entity_names: string[];
}

export interface SignalTypeBreakdown {
  signal_type: string;
  count: number;
  percentage: number;
}

export interface TrendPoint {
  timestamp: string;
  value: number;
}

export interface DashboardMetrics {
  total_signals: number;
  signals_last_24h: number;
  signals_last_7d: number;
  avg_confidence: number;
  anomaly_count: number;
  high_priority_count: number;
  active_briefs: number;
  type_breakdown: SignalTypeBreakdown[];
  signal_volume_trend: TrendPoint[];
  confidence_trend: TrendPoint[];
}

export interface ActiveAlert {
  signal_id: string;
  title: string | null;
  signal_type: string;
  confidence: number;
  anomaly_score: number | null;
  reason: string;
  detected_at: string;
}

export interface BriefSummary {
  id: string;
  title: string;
  bluf: string | null;
  status: string;
  refreshed_at: string | null;
  signal_count: number;
}

export interface SituationRoomDashboard {
  industry_id: string;
  industry_name: string;
  industry_slug: string;
  metrics: DashboardMetrics;
  recent_signals: SignalFeedItem[];
  active_alerts: ActiveAlert[];
  published_briefs: BriefSummary[];
  generated_at: string;
}

// ── Influence ────────────────────────────────────────────────────────────────

export interface EntityInfluenceResponse {
  entity_id: string;
  influence_score: number;
  components: Record<string, number>;
}

export interface KeyInfluencersResponse {
  influencers: Array<{
    entity_id: string;
    name: string;
    influence_score: number;
  }>;
}

export interface InfluencePathResponse {
  source_id: string;
  target_id: string;
  path: Array<{ entity_id: string; name: string }>;
  total_weight: number;
}

export interface CascadePredictionResponse {
  origin_id: string;
  affected_entities: Array<{
    entity_id: string;
    name: string;
    impact_probability: number;
    estimated_delay: string;
  }>;
}

// ── Regulatory ───────────────────────────────────────────────────────────────

export interface RegulatoryEventResponse {
  id: string;
  event_type: string;
  title: string;
  description: string;
  jurisdiction: string;
  effective_date: string | null;
  created_at: string;
}

export interface RegulatoryStatsResponse {
  total_events: number;
  total_rules: number;
  total_impacts: number;
  active_patterns: number;
}

// ── Bulk ─────────────────────────────────────────────────────────────────────

export interface BulkFetchSignalsRequest {
  signal_ids: string[];
}

export interface BulkSignalsResponse {
  signals: SignalResponse[];
  total: number;
}

export interface BulkFetchBriefsRequest {
  brief_ids: string[];
}

export interface BulkBriefsResponse {
  briefs: BriefResponse[];
  total: number;
}

export interface BulkUpdateSignalRequest {
  signal_ids: string[];
  action: string;
}

export interface BulkUpdateResponse {
  updated: number;
  failed: number;
}

// ── API Keys ─────────────────────────────────────────────────────────────────

export interface CreateAPIKeyRequest {
  name: string;
  description?: string | null;
  scopes?: string[];
  rate_limit?: number;
  expires_in_days?: number | null;
}

export interface CreateAPIKeyResponse {
  api_key: string;
  key_id: string;
  key_prefix: string;
  expires_at: string | null;
}

export interface APIKeyResponse {
  id: string;
  name: string;
  description?: string | null;
  key_prefix: string;
  scopes: string[];
  rate_limit: number;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
  revoked_at?: string | null;
  is_active?: boolean;
}

export interface MappedCreateAPIKeyResponse {
  id: string;
  key: string;
  prefix: string;
  expires_at: string | null;
}

// ── Documents ────────────────────────────────────────────────────────────────

export interface DocumentResponse {
  id: string;
  org_id: string;
  title: string;
  file_type: string;
  file_size: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentCreate {
  title: string;
  file_type: string;
  content: string;
}

export interface DocumentUpdate {
  title?: string;
  content?: string;
}

// ── Moat Metrics ─────────────────────────────────────────────────────────────

export interface SnapshotCreateResponse {
  id: string;
  created_at: string;
  metrics: Record<string, number>;
}

export interface SnapshotTrendResponse {
  snapshots: Array<{
    id: string;
    created_at: string;
    metrics: Record<string, number>;
  }>;
}

export interface BacktestChainRequest {
  chain_id: string;
  lookback_days?: number;
}

// ── Signal Alerts ─────────────────────────────────────────────────────────────

export interface AlertResponse {
  id: string;
  alert_type: "anomaly" | "threshold" | "trend_break";
  severity: "low" | "medium" | "high" | "critical";
  metric: string | null;
  country_code: string | null;
  title: string;
  description: string | null;
  current_value: number | null;
  baseline_value: number | null;
  deviation_pct: number | null;
  acknowledged: boolean;
  acknowledged_at: string | null;
  created_at: string;
}

export interface AlertListResponse {
  items: AlertResponse[];
  total: number;
  unacknowledged: number;
}

export interface AlertSummaryResponse {
  total: number;
  unacknowledged: number;
  by_severity: Record<string, number>;
  by_metric: Record<string, number>;
}

export interface AcknowledgeResponse {
  id: string;
  acknowledged: boolean;
  acknowledged_at: string;
}

// ── Synthesis Enhancement ─────────────────────────────────────────────────────

export interface CoverageCheckResult {
  total_signals: number;
  relevant_signals: number;
  coverage_score: number;
  freshest_signal_at: string | null;
  coverage_assessment: "good" | "partial" | "limited";
}

export interface ContractSuggestion {
  suggested_title: string;
  suggested_description: string;
  suggested_keywords: string[];
  inferred_industry: string | null;
}
