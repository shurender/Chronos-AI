/**
 * Stable backend API contracts (TYPES ONLY — no UI logic, no runtime code).
 *
 * This file is the source of truth the frontend integrates against. It mirrors
 * the backend Pydantic models exactly. Keep it in sync with docs/API_CONTRACT.md.
 *
 * ⚠️ Breaking API changes MUST update BOTH docs/API_CONTRACT.md and this file.
 */

// ---------------------------------------------------------------------------
// Shared unions
// ---------------------------------------------------------------------------
export type DecisionType = 'Career' | 'Startup' | 'Financial' | 'Life' | 'Relocation';
export type Horizon = '1 year' | '3 years' | '5 years' | '10 years';
export type BranchStatus = 'active' | 'archived' | 'recommended';
export type VeracityType = 'fact' | 'inference' | 'prediction';
export type MilestoneType =
  | 'decision_point'
  | 'outcome_realized'
  | 'external_event'
  | 'skill_milestone'
  | 'project_phase';
export type AssumptionType =
  | 'market'
  | 'resource'
  | 'behavior'
  | 'timing'
  | 'technical'
  | 'regulatory';

// ---------------------------------------------------------------------------
// Evidence (GET /evidence, /evidence/search, POST /evidence/upload)
// ---------------------------------------------------------------------------
export type EvidenceCategory =
  | 'market_signal'
  | 'research_signal'
  | 'job_signal'
  | 'competitor_signal'
  | 'regulatory_signal'
  | 'user_supplied';
export type SourceKind = 'demo' | 'uploaded' | 'web';

export interface EvidenceItem {
  id: string;
  domain: string;
  title: string;
  summary: string;
  source_name: string;
  source_url: string | null;
  published_at: string | null;
  evidence_type: EvidenceCategory;
  confidence: number;
  tags: string[];
  source_kind: SourceKind;
  retrieved_at: string | null;
  freshness_score: number;
  source_reliability: number;
  is_live_source: boolean;
  is_demo_source: boolean;
}

export interface EvidenceSearchResponse {
  query: string | null;
  domain: string | null;
  provider: string;
  isDemoPack: boolean;
  items: EvidenceItem[];
}

export interface EvidenceUploadRequest {
  title?: string | null;
  summary?: string | null;
  text?: string | null;
  domain?: string;
  source_name?: string;
  source_url?: string | null;
  evidence_type?: EvidenceCategory;
  confidence?: number;
  published_at?: string | null;
  tags?: string[];
}

// ---------------------------------------------------------------------------
// Agent council (embedded in SimulationResponse)
// ---------------------------------------------------------------------------
export interface AgentOutput {
  agent_id: string;
  agent_label: string;
  position: string;
  confidence: number;
  rationale: string[];
  citations: string[];
  concerns: string[];
}

export interface AgentRunTrace {
  agent_id: string;
  provider: string;
  model: string;
  prompt_hash: string;
  input_summary: string;
  output_valid: boolean;
  fallback_used: boolean;
  latency_ms: number;
}

export interface AgentCouncil {
  agents: AgentOutput[];
  recommendedBranchId: string | null;
  consensusScore: number;
  summary: string;
  mode: string; // deterministic | llm | hybrid
  isDeterministic: boolean;
  traces: AgentRunTrace[];
}

// ---------------------------------------------------------------------------
// Intake (POST /intake/analyze)
// ---------------------------------------------------------------------------
export type IntakeQuestionCategory =
  | 'decision_options'
  | 'success_metric'
  | 'time_horizon'
  | 'geography_domain'
  | 'risk_tolerance'
  | 'available_resources'
  | 'constraints'
  | 'irreversible_consequences'
  | 'evidence_gaps';

export interface ClarifyingQuestion {
  category: IntakeQuestionCategory;
  question: string;
  why_it_matters: string;
}

export interface IntakeAnalyzeRequest {
  decisionQuestion?: string;
  decisionType?: string | null;
  horizon?: string | null;
  risk?: number | null;
  goal?: string | null;
  constraints?: string | null;
  geography?: string | null;
  options?: string[];
  digitalTwinProfile?: Record<string, unknown> | null;
  evidenceCount?: number | null;
  precedentCount?: number | null;
}

export interface IntakeAnalysis {
  completenessScore: number;
  missingFields: string[];
  assumptions: string[];
  clarifyingQuestions: ClarifyingQuestion[];
  canProceed: boolean;
  confidencePenalty: number;
  reason: string;
}

// ---------------------------------------------------------------------------
// Digital Twin (POST /digital-twin/build)
// ---------------------------------------------------------------------------
export type SubjectType = 'individual' | 'team' | 'org';

export interface ProfileItem {
  label: string;
  confidence: number;
  citations: string[];
}

export interface RiskProfile {
  level: 'low' | 'moderate' | 'high' | 'unknown';
  score: number;
  rationale: string[];
}

export interface ExecutionStyle {
  style: string;
  rationale: string[];
}

export interface TeamTopology {
  size_estimate: number;
  roles: string[];
}

export interface DigitalTwinConfidenceBreakdown {
  graphCoverage: number;
  evidenceCoverage: number;
  intakeCompleteness: number;
  overallConfidence: number;
}

export interface DigitalTwinBuildRequest {
  decisionQuestion?: string | null;
  decisionType?: DecisionType | null;
  goal?: string | null;
  constraints?: string | null;
  geography?: string | null;
  options?: string[];
  useGraph?: boolean;
  useEvidence?: boolean;
}

export interface DigitalTwinProfile {
  profile_id: string;
  created_at: string;
  subject_type: SubjectType;
  inferred_skills: ProfileItem[];
  resources: ProfileItem[];
  constraints: ProfileItem[];
  goals: ProfileItem[];
  behavioral_patterns: ProfileItem[];
  decision_history_summary: string;
  risk_profile: RiskProfile;
  execution_style: ExecutionStyle;
  team_topology: TeamTopology | null;
  missing_information: string[];
  contradictions: string[];
  confidenceBreakdown: DigitalTwinConfidenceBreakdown;
  source_chunk_ids: string[];
  external_evidence_ids: string[];
  methodology: string;
}

// ---------------------------------------------------------------------------
// Simulation (POST /simulate, GET /simulations, GET /simulations/{id})
// ---------------------------------------------------------------------------
export interface DecisionOption {
  id?: string | null;
  label: string;
  description?: string | null;
  upfront_cost?: string | null;
  reversibility?: number | null;
  time_commitment?: string | null;
  expected_upside?: string | null;
  known_risks?: string[];
}

export interface SimulationRequest {
  name: string;
  type?: DecisionType;
  horizon?: Horizon;
  risk?: number;
  goal?: string;
  constraints?: string | null;
  geography?: string | null;
  /** Plain strings are coerced server-side into DecisionOption objects. */
  options?: Array<string | DecisionOption>;
}

export interface Citation {
  nodeId: string;
  label: string;
  excerpt?: string | null;
  url?: string | null;
  source_type?: string | null;
  source_name?: string | null;
  source_url?: string | null;
  timestamp?: string | null;
}

export interface GroundedDecision {
  chunk_id: string;
  snippet: string;
  distance: number;
}

export interface ConfidenceBreakdown {
  evidenceStrength: number;
  sourceReliability: number;
  modelConsensus: number;
  temporalRelevance: number;
  causalCoherence: number;
}

export interface DataCoverage {
  graphNodes: number;
  relevantPrecedents: number;
  liveEvidence: number;
  demoEvidence: number;
  connectorSources: number;
  uploadedSources: number;
  digitalTwinCompleteness: number;
  intakeCompleteness: number;
  overallCoverage: number;
  gaps: string[];
}

export interface TimelineMilestone {
  month: number;
  event: string;
  type: MilestoneType;
  veracity: VeracityType;
  citations: Citation[];
  dataSparsity: number;
}

export interface AgentDisagreement {
  agentId: string;
  agentLabel: string;
  position: string;
  confidence: number;
  rationale: string[];
}

export interface Assumption {
  id: string;
  statement: string;
  type: AssumptionType;
  confidence: number;
  evidenceIds: string[];
  riskIfWrong: string;
}

export interface TimelineBranch {
  id: string;
  title: string;
  description: string;
  probabilityScore: number;
  expectedRegret: number;
  status: BranchStatus;
  milestones: TimelineMilestone[];
  confidenceBreakdown: ConfidenceBreakdown;
  anchorNodeIds: string[];
  agentDisagreements: AgentDisagreement[];
  groundedOn: GroundedDecision[];
  externalEvidence: EvidenceItem[];
  optionId: string | null;
  assumptions: Assumption[];
  evidenceUsed: string[];
  digitalTwinFactors: string[];
  riskFactors: string[];
  upsideFactors: string[];
  failureModes: string[];
  leadingIndicators: string[];
  decisionCheckpoints: string[];
  claimIds: string[];
}

export interface SimulationMetadata {
  generatedAt: string;
  schemaVersion: string;
  query: string;
  horizonMonths: number;
}

export interface SafetyLabel {
  disclaimer: string;
  high_stakes: boolean;
  category: string;
  professional_advice_warning: string | null;
}

export interface ProvenanceSummary {
  simulationId?: string;
  totalClaims?: number;
  claimsByType?: Record<string, number>;
}

export interface SimulationResponse {
  metadata: SimulationMetadata;
  timelines: TimelineBranch[];
  recommendedTimelineId: string;
  affectedNodeIds: string[];
  externalEvidenceUsed: EvidenceItem[];
  dataCoverage: DataCoverage;
  isDemoEvidence: boolean;
  evidenceProvider: string | null;
  agentCouncil: AgentCouncil | null;
  digitalTwinProfileId: string | null;
  digitalTwinSummary: string | null;
  intakeAnalysis: IntakeAnalysis | null;
  simulationId: string | null;
  provenanceSummary: ProvenanceSummary | null;
  safety: SafetyLabel | null;
  methodology: string;
}

/** GET /simulations item (lightweight). */
export interface SimulationSummary {
  simulation_id: string;
  created_at: string;
  query: string;
  recommendedTimelineId: string | null;
}

// ---------------------------------------------------------------------------
// Future Self avatar (POST /avatar/chat)
// ---------------------------------------------------------------------------
export type GroundingLabel = 'graph_grounded' | 'evidence_grounded' | 'mixed' | 'general_opinion';

export interface AvatarCitation {
  nodeId: string;
  label: string;
  excerpt?: string | null;
  url?: string | null;
  source_type?: string | null;
  source_name?: string | null;
  source_url?: string | null;
  timestamp?: string | null;
}

export interface AvatarChatRequest {
  message: string;
  decisionQuestion?: string | null;
  selectedTimelineId?: string | null;
  simulationContext?: Record<string, unknown> | null;
  graphNodeIds?: string[] | null;
}

export interface AvatarChatResponse {
  content: string;
  referencedNodeIds: string[];
  citations: AvatarCitation[];
  groundingLabel: GroundingLabel;
  confidence: number;
  llmBacked: boolean;
  claim_id: string | null;
}

// ---------------------------------------------------------------------------
// Ingestion (POST /ingest/demo, /ingest/github, /ingest/upload)
// ---------------------------------------------------------------------------
export type IngestionSourceType = 'demo' | 'github' | 'slack' | 'notion' | 'upload';
export type IngestionStatus = 'pending' | 'running' | 'succeeded' | 'failed';

export interface IngestGithubRequest {
  repo: string;
  include_issues?: boolean;
  max_items?: number;
}

export interface GithubRepoCheckResponse {
  exists: boolean;
  repo: string;
  full_name?: string | null;
  private?: boolean | null;
  html_url?: string | null;
  default_branch?: string | null;
  updated_at?: string | null;
  stars?: number | null;
  message: string;
}

export interface IngestionRun {
  run_id: string;
  source_type: IngestionSourceType;
  status: IngestionStatus;
  started_at: string;
  completed_at: string | null;
  chunks_created: number;
  nodes_created: number;
  edges_created: number;
  files_received: number;
  files_parsed: number;
  files_failed: number;
  warnings: string[];
  errors: string[];
  source_summary: Record<string, unknown>;
}

export type ConnectorProvider = 'github' | 'slack' | 'notion';
export type ConnectorState = 'not_connected' | 'connecting' | 'connected' | 'syncing' | 'error';

export interface ConnectorStatus {
  provider: ConnectorProvider;
  status: ConnectorState;
  connected: boolean;
  last_synced: string | null;
  last_sync_at?: string | null;
  last_sync_status?: string | null;
  error: string | null;
  last_error?: string | null;
  items_ingested?: number;
  source_counts: Record<string, number>;
}

export interface ConnectorSyncResponse {
  provider: ConnectorProvider;
  status: ConnectorState;
  run: IngestionRun | null;
  last_synced: string | null;
  source_counts: Record<string, number>;
  error: string | null;
}

export interface GithubConnectorSource {
  id: string;
  name: string;
  full_name: string;
  private: boolean;
  html_url: string | null;
  updated_at: string | null;
  default_branch: string | null;
  selected: boolean;
}

export interface SlackConnectorSource {
  id: string;
  name: string;
  is_private: boolean;
  is_member: boolean;
  num_members?: number | null;
  selected: boolean;
}

export interface NotionConnectorSource {
  id: string;
  title: string;
  type: 'page' | 'database';
  url: string | null;
  last_edited_time: string | null;
  selected: boolean;
}

export type ConnectorSource = GithubConnectorSource | SlackConnectorSource | NotionConnectorSource;

export interface ConnectorSyncOptions {
  sourceIds?: string[];
  maxItems?: number;
  since?: string;
  includeThreads?: boolean;
  includeIssues?: boolean;
  includePullRequests?: boolean;
  repo?: string;
}

// ---------------------------------------------------------------------------
// Graph (GET /graph) & health (GET /health, /llm/health)
// ---------------------------------------------------------------------------
export interface GraphNode {
  id: string;
  [key: string]: unknown; // node_type, label, evidence_type, confidence, description, ...
}

export interface GraphEdge {
  id?: string;
  edge_id?: string;
  key?: string;
  source: string;
  target: string;
  source_node_id?: string;
  target_node_id?: string;
  [key: string]: unknown; // edge_type, description, confidence, ...
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export type GraphPayload = GraphResponse;

export interface HistoricalPrecedent {
  chunk_id: string;
  snippet: string;
  distance: number;
  source_type: string | null;
  timestamp: string | null;
  project: string | null;
}

export interface HealthResponse {
  status: string;
}

export interface LlmHealthResponse {
  llm_provider: string;
  embedding_provider: string;
  amd_mode: boolean;
  chat: {
    provider: string;
    model: string;
    available: boolean;
    supports_structured_output: boolean;
    supports_embeddings: boolean;
    detail: string;
  };
  embedding: { provider: string; model: string; available: boolean };
}

/** Standard FastAPI error envelope. */
export interface ApiError {
  detail: string | Record<string, unknown>;
}
