import { create } from 'zustand';

import { mockGraphPayload } from '../mocks/graph.mock';
import { mockSimulationPayload } from '../mocks/timeline.mock';
import type { ChatMessage } from '../types/avatar';
import type { Citation, GraphPayload, GraphNode, GraphEdge } from '../types/graph';
import type { SimulationPayload, Timeline, TimelineMilestone } from '../types/timeline';

/** Simulated network latency for `runSimulation` (ms). */
const SIMULATION_DELAY_MS = 2500;
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

/**
 * Serializable slice of the Chronos wizard store.
 * Data payloads remain null until `runSimulation` completes.
 */
export interface ChronosStoreState {
  /** Wizard step: 1 Connect Data → 2 Define Decision → 3 Simulate → 4 Explore Chat */
  currentStep: number;

  /** User-authored decision question from step 2. */
  decisionQuestion: string;

  /** Knowledge graph payload; null until simulation run. */
  graphData: GraphPayload | null;

  /** Timeline simulation payload; null until simulation run. */
  simulationData: SimulationPayload | null;

  /** Avatar conversation transcript. */
  chatHistory: ChatMessage[];

  /** True while `runSimulation` is in flight. */
  isLoading: boolean;
}

export interface ChronosStoreActions {
  setStep: (step: number) => void;
  setDecisionQuestion: (question: string) => void;
  addChatMessage: (msg: ChatMessage) => void;
  runSimulation: () => Promise<void>;
}

export type ChronosStore = ChronosStoreState & ChronosStoreActions;

export const useChronosStore = create<ChronosStore>((set) => ({
  currentStep: 1,
  decisionQuestion: '',
  graphData: null,
  simulationData: null,
  chatHistory: [],
  isLoading: false,

  setStep: (step) => set({ currentStep: step }),

  setDecisionQuestion: (question) => set({ decisionQuestion: question }),

  addChatMessage: (msg) =>
    set((state) => ({ chatHistory: [...state.chatHistory, msg] })),

  runSimulation: async () => {
    set({ isLoading: true });

    try {
      const [graphResponse, forecastResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/graph`),
        fetch(`${API_BASE_URL}/forecast/decision`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: 'Chronos demo decision',
            type: 'Career',
            horizon: '1 year',
            risk: 55,
            goal: 'Explore plausible futures using the ingested memory graph.',
          }),
        }),
      ]);

      if (!graphResponse.ok) {
        throw new Error(`Graph request failed: ${graphResponse.status}`);
      }
      if (!forecastResponse.ok) {
        throw new Error(`Forecast request failed: ${forecastResponse.status}`);
      }

      const [graphJson, forecastJson] = await Promise.all([
        graphResponse.json(),
        forecastResponse.json(),
      ]);

      const graphData = adaptGraphPayload(graphJson);
      const simulationData = adaptForecastToSimulation(forecastJson);

      set({
        graphData,
        simulationData,
        isLoading: false,
        currentStep: 3,
      });
    } catch {
      await new Promise<void>((resolve) => {
        setTimeout(resolve, SIMULATION_DELAY_MS);
      });

      set({
        graphData: mockGraphPayload,
        simulationData: mockSimulationPayload,
        isLoading: false,
        currentStep: 3,
      });
    }
  },
}));

function adaptGraphPayload(payload: any): GraphPayload {
  const nodes: GraphNode[] = (payload.nodes ?? []).map((node: any) => ({
    id: String(node.id ?? node.node_id),
    type: node.type ?? node.node_type ?? 'decision',
    label: String(node.label ?? 'Untitled'),
    veracity: node.veracity ?? node.evidence_type ?? 'fact',
    confidence: Number(node.confidence ?? 0.5),
    source: node.source ?? 'document_ingest',
    citations: normalizeCitations(node),
    hasGap: Boolean(node.hasGap ?? node.has_gap ?? false),
    hasContradiction: Boolean(node.hasContradiction ?? node.has_contradiction ?? false),
    summaryText: node.summaryText ?? node.description,
  }));

  const edges: GraphEdge[] = (payload.edges ?? []).map((edge: any) => ({
    id: String(edge.id ?? edge.edge_id),
    source: String(edge.source ?? edge.source_node_id),
    target: String(edge.target ?? edge.target_node_id),
    type: edge.type ?? edge.edge_type ?? 'causal',
    confidence: Number(edge.confidence ?? 0.5),
    veracity: edge.veracity ?? edge.evidence_type ?? 'inference',
    label: edge.label ?? edge.description,
  }));

  return {
    nodes,
    edges,
    metadata: {
      generatedAt: payload.metadata?.generatedAt ?? new Date().toISOString(),
      schemaVersion: payload.metadata?.schemaVersion ?? '1.0.0',
      query: payload.metadata?.query,
    },
  };
}

function normalizeCitations(node: any): readonly Citation[] {
  const sourceChunkIds = Array.isArray(node.source_chunk_ids) ? node.source_chunk_ids : [];
  return sourceChunkIds.map((chunkId: string) => ({
    nodeId: String(node.id ?? node.node_id ?? chunkId),
    label: String(node.label ?? 'Source citation'),
    excerpt: node.description,
  }));
}

function adaptForecastToSimulation(payload: any): SimulationPayload {
  const timeline: Timeline = {
    id: payload.id ?? 'timeline_1',
    title: payload.request?.name ?? 'Simulated branch',
    description: payload.methodology ?? 'Heuristic forecast generated from the backend.',
    probabilityScore: inferProbability(payload.probabilityDistribution),
    expectedRegret: normalizeScore(payload.regretAnalysis?.regretScore),
    status: 'recommended',
    milestones: (payload.successForecast ?? []).map((point: any, index: number) => ({
      month: parseMonth(point.month, index),
      event: `Projected progress at ${point.month}`,
      type: index === 0 ? 'decision_point' : 'project_phase',
      veracity: 'prediction',
      citations: [],
      dataSparsity: Math.max(0, 1 - Number(point.value ?? 0) / 100),
    })) satisfies readonly TimelineMilestone[],
    confidenceBreakdown: {
      evidenceStrength: 0.72,
      sourceReliability: 0.66,
      modelConsensus: 0.63,
      temporalRelevance: 0.79,
      causalCoherence: 0.68,
    },
    anchorNodeIds: [],
    agentDisagreements: [],
  };

  return {
    metadata: {
      generatedAt: payload.createdAt ?? new Date().toISOString(),
      schemaVersion: '1.0.0',
      query: payload.request?.goal ?? 'Backend forecast',
      horizonMonths: 12,
    },
    timelines: [timeline],
    recommendedTimelineId: timeline.id,
    affectedNodeIds: [],
  };
}

function inferProbability(probabilityDistribution: any): number {
  if (!Array.isArray(probabilityDistribution) || probabilityDistribution.length === 0) {
    return 1;
  }
  const strongBranch = probabilityDistribution.reduce((best: any, current: any) => {
    const bestValue = Number(best?.value ?? 0);
    const currentValue = Number(current?.value ?? 0);
    return currentValue > bestValue ? current : best;
  });
  return Math.max(0.05, Number(strongBranch?.value ?? 100) / 100);
}

function normalizeScore(value: unknown): number {
  return Math.max(0, Math.min(1, Number(value ?? 50) / 100));
}

function parseMonth(label: string | undefined, fallback: number): number {
  if (!label) return fallback;
  const parsed = Number.parseInt(label.replace(/\D+/g, ''), 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}
