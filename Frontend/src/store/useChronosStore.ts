import { create } from 'zustand';

import { mockGraphPayload } from '../mocks/graph.mock';
import { mockSimulationPayload } from '../mocks/timeline.mock';
import type { ChatMessage } from '../types/avatar';
import type { Citation } from '../types/graph';
import type { GraphPayload } from '../types/graph';
import type {
  ConfidenceBreakdown,
  MilestoneType,
  SimulationPayload,
  Timeline,
  TimelineMilestone,
} from '../types/timeline';

// ---------------------------------------------------------------------------
// Structured decision intake (mirrors backend SimulationRequest literals)
// ---------------------------------------------------------------------------

export type DecisionType = 'Career' | 'Startup' | 'Financial' | 'Life' | 'Relocation';
export type Horizon = '1 year' | '3 years' | '5 years' | '10 years';

// ---------------------------------------------------------------------------
// Historical precedents (GET /query/similar)
// ---------------------------------------------------------------------------

export interface HistoricalPrecedent {
  chunk_id: string;
  snippet: string;
  distance: number;
  source_type: string | null;
  timestamp: string | null;
  project: string | null;
}

// ---------------------------------------------------------------------------
// External demo evidence (returned inside POST /simulate)
// ---------------------------------------------------------------------------

export interface ExternalEvidenceItem {
  id: string;
  domain: string;
  title: string;
  summary: string;
  source_name: string;
  source_url: string | null;
  published_at: string | null;
  evidence_type: string;
  confidence: number;
  tags: string[];
}

// ---------------------------------------------------------------------------
// Multi-agent council (returned inside POST /simulate)
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

export interface AgentCouncil {
  agents: AgentOutput[];
  recommendedBranchId: string | null;
  consensusScore: number;
  summary: string;
  isDeterministic: boolean;
}

// ---------------------------------------------------------------------------
// Backend response shapes (POST /forecast/decision)
// ---------------------------------------------------------------------------

interface DecisionForecastRequest {
  name: string;
  type: string;
  horizon: string;
  risk: number;
  goal: string;
}

interface ProbabilityOutcome {
  outcome: string;
  value: number;
}

interface ForecastPoint {
  month: string; // e.g. "M0", "M12"
  value: number;
}

interface RiskHeatmapItem {
  label: string;
  level: number;
}

interface RegretAnalysis {
  regretScore: number;
  inactionRegretScore: number;
  summary: string;
}

interface GroundedDecision {
  chunk_id: string;
  snippet: string;
  distance: number;
}

interface DecisionForecast {
  id: string;
  createdAt: string;
  request: DecisionForecastRequest;
  probabilityDistribution: ProbabilityOutcome[];
  successForecast: ForecastPoint[];
  riskHeatmap: RiskHeatmapItem[];
  regretAnalysis: RegretAnalysis;
  groundedOn: GroundedDecision[];
  methodology: string;
}

// ---------------------------------------------------------------------------
// Adapter: backend DecisionForecast -> frontend SimulationPayload
// ---------------------------------------------------------------------------

function parseHorizonMonths(horizon: string): number {
  const match = /(\d+)/.exec(horizon);
  const amount = match ? Number(match[1]) : 1;
  return horizon.toLowerCase().includes('year') ? amount * 12 : amount;
}

function parseMilestoneMonth(month: string): number {
  const match = /(\d+)/.exec(month);
  return match ? Number(match[1]) : 0;
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function deriveCitations(groundedOn: GroundedDecision[]): Citation[] {
  return groundedOn.map((g) => ({
    nodeId: g.chunk_id,
    label: g.snippet.slice(0, 80) || g.chunk_id,
    excerpt: g.snippet,
  }));
}

function deriveConfidenceBreakdown(
  forecastData: DecisionForecast,
  horizonMonths: number
): ConfidenceBreakdown {
  const { groundedOn, riskHeatmap, probabilityDistribution } = forecastData;

  const evidenceStrength = clamp01(groundedOn.length / 3);

  const avgGroundedDistance =
    groundedOn.length > 0
      ? groundedOn.reduce((sum, g) => sum + g.distance, 0) / groundedOn.length
      : undefined;
  const sourceReliability =
    avgGroundedDistance !== undefined ? clamp01(1 - avgGroundedDistance) : 0.5;

  const strongestOutcomeShare =
    probabilityDistribution.length > 0
      ? Math.max(...probabilityDistribution.map((o) => o.value)) / 100
      : 0.5;
  const modelConsensus = clamp01(strongestOutcomeShare);

  // Nearer-term horizons are inherently more predictable than far-out ones.
  const temporalRelevance = clamp01(1 - horizonMonths / 120);

  const avgRiskLevel =
    riskHeatmap.length > 0
      ? riskHeatmap.reduce((sum, r) => sum + r.level, 0) / riskHeatmap.length
      : 50;
  const causalCoherence = clamp01(1 - avgRiskLevel / 100);

  return {
    evidenceStrength,
    sourceReliability,
    modelConsensus,
    temporalRelevance,
    causalCoherence,
  };
}

function deriveProbabilityScore(distribution: ProbabilityOutcome[]): number {
  const failure = distribution.find((o) => o.outcome === 'Failure')?.value ?? 0;
  const strongestPositive = Math.max(
    0,
    ...distribution.filter((o) => o.outcome !== 'Failure').map((o) => o.value)
  );
  // Blend "overall non-failure probability" with the strongest single positive
  // outcome so a decisive winner still moves the needle.
  const nonFailure = 100 - failure;
  return clamp01((nonFailure + strongestPositive) / 200);
}

function deriveMilestones(
  forecastData: DecisionForecast,
  citations: Citation[]
): TimelineMilestone[] {
  const points = forecastData.successForecast;

  return points.map((point, index) => {
    const month = parseMilestoneMonth(point.month);
    const type: MilestoneType = index === 0 ? 'decision_point' : 'outcome_realized';

    return {
      month,
      event: `Projected trajectory for "${forecastData.request.name}" at month ${month}: ${point.value.toFixed(1)}% success likelihood`,
      type,
      veracity: 'prediction',
      citations,
      dataSparsity: citations.length > 0 ? 0.35 : 0.75,
    };
  });
}

function adaptForecastToSimulationPayload(
  forecastData: DecisionForecast,
  decisionQuestion: string
): SimulationPayload {
  const horizonMonths = parseHorizonMonths(forecastData.request.horizon);
  const citations = deriveCitations(forecastData.groundedOn);
  const milestones = deriveMilestones(forecastData, citations);
  const probabilityScore = deriveProbabilityScore(forecastData.probabilityDistribution);
  const expectedRegret = clamp01(forecastData.regretAnalysis.regretScore / 100);
  const confidenceBreakdown = deriveConfidenceBreakdown(forecastData, horizonMonths);

  const timeline: Timeline = {
    id: forecastData.id,
    title: forecastData.request.name,
    description: `${forecastData.regretAnalysis.summary} ${forecastData.methodology}`,
    probabilityScore,
    expectedRegret,
    status: 'recommended',
    milestones,
    confidenceBreakdown,
    anchorNodeIds: [],
    agentDisagreements: [],
  };

  return {
    metadata: {
      generatedAt: forecastData.createdAt,
      schemaVersion: '1.0.0',
      query: decisionQuestion,
      horizonMonths,
    },
    timelines: [timeline],
    recommendedTimelineId: timeline.id,
    affectedNodeIds: [],
  };
}

export interface ChronosStoreState {
  currentStep: number;
  decisionQuestion: string;
  decisionType: DecisionType;
  horizon: Horizon;
  risk: number;
  goal: string;
  constraints: string;
  geography: string;
  optionA: string;
  optionB: string;
  optionC: string;
  graphData: GraphPayload | null;
  simulationData: SimulationPayload | null;
  historicalPrecedents: HistoricalPrecedent[];
  externalEvidence: ExternalEvidenceItem[];
  agentCouncil: AgentCouncil | null;
  chatHistory: ChatMessage[];
  isLoading: boolean;
}

export interface ChronosStoreActions {
  setStep: (step: number) => void;
  setDecisionQuestion: (question: string) => void;
  setDecisionType: (type: DecisionType) => void;
  setHorizon: (horizon: Horizon) => void;
  setRisk: (risk: number) => void;
  setGoal: (goal: string) => void;
  setConstraints: (constraints: string) => void;
  setGeography: (geography: string) => void;
  setOptionA: (value: string) => void;
  setOptionB: (value: string) => void;
  setOptionC: (value: string) => void;
  addChatMessage: (msg: ChatMessage) => void;
  runSimulation: () => Promise<void>;
}

export type ChronosStore = ChronosStoreState & ChronosStoreActions;

export const useChronosStore = create<ChronosStore>((set, get) => ({
  currentStep: 0,
  decisionQuestion: '',
  decisionType: 'Startup',
  horizon: '3 years',
  risk: 50,
  goal: '',
  constraints: '',
  geography: '',
  optionA: '',
  optionB: '',
  optionC: '',
  graphData: null,
  simulationData: null,
  historicalPrecedents: [],
  externalEvidence: [],
  agentCouncil: null,
  chatHistory: [],
  isLoading: false,

  setStep: (step) => set({ currentStep: step }),
  setDecisionQuestion: (question) => set({ decisionQuestion: question }),
  setDecisionType: (decisionType) => set({ decisionType }),
  setHorizon: (horizon) => set({ horizon }),
  setRisk: (risk) => set({ risk }),
  setGoal: (goal) => set({ goal }),
  setConstraints: (constraints) => set({ constraints }),
  setGeography: (geography) => set({ geography }),
  setOptionA: (optionA) => set({ optionA }),
  setOptionB: (optionB) => set({ optionB }),
  setOptionC: (optionC) => set({ optionC }),
  addChatMessage: (msg) =>
    set((state) => ({ chatHistory: [...state.chatHistory, msg] })),

  runSimulation: async () => {
    set({ isLoading: true });

    try {
      // 1. Fetch LIVE Graph Data from Backend
      const graphRes = await fetch('http://localhost:8000/graph');
      if (!graphRes.ok) throw new Error("Backend not reachable");
      const graphJson = await graphRes.json();

      // Adapt backend Python dictionary keys to frontend TypeScript interfaces
      const actualGraphData: GraphPayload = {
        metadata: {
          generatedAt: new Date().toISOString(),
          schemaVersion: '1.0.0',
          query: get().decisionQuestion
        },
        // @ts-ignore - Mapping dynamic backend response
        nodes: graphJson.nodes.map((n) => ({
          id: n.id,
          type: n.node_type || 'decision',
          label: n.label || 'Unknown',
          veracity: n.evidence_type || 'inference',
          confidence: n.confidence || 0.5,
          source: 'agent_inference',
          citations: [],
          hasGap: false,
          hasContradiction: false,
          summaryText: n.description || ''
        })),
        // @ts-ignore - Mapping dynamic backend response
        edges: graphJson.edges.map((e) => ({
          id: e.key || Math.random().toString(),
          source: e.source,
          target: e.target,
          type: e.edge_type || 'causal',
          confidence: e.confidence || 0.5,
          veracity: e.evidence_type || 'inference',
          label: e.description || ''
        }))
      };

      // 2. Best-effort historical precedent lookup (never blocks the simulation)
      let historicalPrecedents: HistoricalPrecedent[] = [];
      try {
        const precedentsRes = await fetch(
          `http://localhost:8000/query/similar?q=${encodeURIComponent(get().decisionQuestion)}&k=5`
        );
        if (precedentsRes.ok) {
          const precedentsJson = await precedentsRes.json();
          historicalPrecedents = precedentsJson.items ?? [];
        }
      } catch (precedentsErr) {
        console.warn("Historical precedent lookup failed.", precedentsErr);
      }

      // 3. Build the shared decision request payload from the structured intake
      const state = get();
      const options = [state.optionA, state.optionB, state.optionC]
        .map((o) => o.trim())
        .filter((o) => o.length > 0);

      const decisionRequest = {
        name: state.decisionQuestion,
        type: state.decisionType,
        horizon: state.horizon,
        risk: state.risk,
        goal: state.goal.trim() || undefined,
        constraints: state.constraints.trim() || undefined,
        geography: state.geography.trim() || undefined,
        options,
      };

      // Prefer the multi-branch /simulate endpoint. Fall back to the
      // single-shape /forecast/decision endpoint only if /simulate is
      // unavailable, and to mock data only if both backend calls fail.
      let simulationData: SimulationPayload | null = null;
      let externalEvidence: ExternalEvidenceItem[] = [];
      let agentCouncil: AgentCouncil | null = null;

      try {
        const simRes = await fetch('http://localhost:8000/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(decisionRequest),
        });
        if (simRes.ok) {
          const sim = (await simRes.json()) as SimulationPayload & {
            externalEvidenceUsed?: ExternalEvidenceItem[];
            agentCouncil?: AgentCouncil | null;
          };
          console.log("Backend Simulation Received:", sim);
          externalEvidence = sim.externalEvidenceUsed ?? [];
          agentCouncil = sim.agentCouncil ?? null;
          simulationData = {
            ...sim,
            metadata: { ...sim.metadata, query: get().decisionQuestion },
          };
        }
      } catch (simErr) {
        console.warn("/simulate unavailable, falling back to /forecast/decision.", simErr);
      }

      if (!simulationData) {
        const forecastRes = await fetch('http://localhost:8000/forecast/decision', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(decisionRequest),
        });
        if (!forecastRes.ok) throw new Error("Forecast request failed");
        const forecastData: DecisionForecast = await forecastRes.json();
        console.log("Backend Forecast Received:", forecastData);
        simulationData = adaptForecastToSimulationPayload(forecastData, get().decisionQuestion);
      }

      // No corroborating precedent in the graph -> nudge displayed evidence
      // confidence down slightly rather than silently overstating it.
      if (historicalPrecedents.length === 0) {
        simulationData = {
          ...simulationData,
          timelines: simulationData.timelines.map((t) => ({
            ...t,
            confidenceBreakdown: {
              ...t.confidenceBreakdown,
              evidenceStrength: clamp01(t.confidenceBreakdown.evidenceStrength * 0.7),
            },
          })),
        };
      }

      set({
        graphData: actualGraphData, // Powered by your LIVE Python Backend!
        simulationData,
        historicalPrecedents,
        externalEvidence,
        agentCouncil,
        isLoading: false,
        currentStep: 3,
      });

    } catch (error) {
      console.warn("Backend not running or failed. Falling back to mock data.", error);
      // Fallback to mocks if backend isn't running so the UI doesn't break during demos
      set({
        graphData: mockGraphPayload,
        simulationData: mockSimulationPayload,
        historicalPrecedents: [],
        externalEvidence: [],
        agentCouncil: null,
        isLoading: false,
        currentStep: 3,
      });
    }
  },
}));