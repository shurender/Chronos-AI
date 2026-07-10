import { create } from 'zustand';

import { adaptBackendGraphToFrontendGraph, chronosApi } from '../api/chronosApi';
import type {
  AgentCouncil,
  DigitalTwinProfile,
  EvidenceItem,
  HistoricalPrecedent,
  IngestionRun,
  IntakeAnalysis,
  SimulationRequest,
  TimelineBranch as BackendTimelineBranch,
  TimelineMilestone as BackendTimelineMilestone,
} from '../api/contracts';
import type { ChatMessage } from '../types/avatar';
import type { Citation, GraphPayload } from '../types/graph';
import type { SimulationPayload, Timeline, TimelineMilestone } from '../types/timeline';

export type DecisionType = 'Career' | 'Startup' | 'Financial' | 'Life' | 'Relocation';
export type Horizon = '1 year' | '3 years' | '5 years' | '10 years';
export type BackendStatus = 'unknown' | 'connected' | 'disconnected';

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
  backendStatus: BackendStatus;
  connectStatus: string | null;
  errorMessage: string | null;
  graphData: GraphPayload | null;
  simulationData: SimulationPayload | null;
  intakeAnalysis: IntakeAnalysis | null;
  digitalTwinProfile: DigitalTwinProfile | null;
  historicalPrecedents: HistoricalPrecedent[];
  externalEvidence: EvidenceItem[];
  agentCouncil: AgentCouncil | null;
  selectedTimelineId: string | null;
  lastIngestionRun: IngestionRun | null;
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
  checkBackendStatus: () => Promise<void>;
  loadDemoWorkspace: () => Promise<void>;
  ingestGithubRepo: (repo: string) => Promise<void>;
  uploadFiles: (files: FileList | File[]) => Promise<void>;
  refreshGraph: () => Promise<GraphPayload>;
  runSimulation: () => Promise<void>;
}

export type ChronosStore = ChronosStoreState & ChronosStoreActions;

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function getOptions(state: ChronosStoreState): string[] {
  return [state.optionA, state.optionB, state.optionC]
    .map((option) => option.trim())
    .filter(Boolean);
}

function buildSimulationRequest(state: ChronosStoreState): SimulationRequest {
  return {
    name: state.decisionQuestion.trim(),
    type: state.decisionType,
    horizon: state.horizon,
    risk: state.risk,
    goal: state.goal.trim() || 'Maximize favorable outcome, minimize regret',
    constraints: state.constraints.trim() || null,
    geography: state.geography.trim() || null,
    options: getOptions(state),
  };
}

function normalizeCitation(citation: { nodeId: string; label: string; excerpt?: string | null; url?: string | null }): Citation {
  return {
    nodeId: citation.nodeId,
    label: citation.label,
    excerpt: citation.excerpt ?? undefined,
    url: citation.url ?? undefined,
  };
}

function normalizeMilestone(milestone: BackendTimelineMilestone): TimelineMilestone {
  return {
    ...milestone,
    citations: milestone.citations.map(normalizeCitation),
  };
}

function normalizeTimeline(timeline: BackendTimelineBranch): Timeline {
  return {
    ...timeline,
    milestones: timeline.milestones.map(normalizeMilestone),
  };
}

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
  backendStatus: 'unknown',
  connectStatus: null,
  errorMessage: null,
  graphData: null,
  simulationData: null,
  intakeAnalysis: null,
  digitalTwinProfile: null,
  historicalPrecedents: [],
  externalEvidence: [],
  agentCouncil: null,
  selectedTimelineId: null,
  lastIngestionRun: null,
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

  checkBackendStatus: async () => {
    try {
      await chronosApi.ready();
      set({ backendStatus: 'connected', errorMessage: null });
    } catch (readyError) {
      try {
        await chronosApi.health();
        set({ backendStatus: 'connected', errorMessage: null });
      } catch (healthError) {
        console.warn('Chronos backend health check failed.', { readyError, healthError });
        set({
          backendStatus: 'disconnected',
          errorMessage: 'Backend is disconnected. Start the API on http://localhost:8000.',
        });
      }
    }
  },

  refreshGraph: async () => {
    const graph = adaptBackendGraphToFrontendGraph(
      await chronosApi.getGraph(),
      get().decisionQuestion,
    );
    set({ graphData: graph });
    return graph;
  },

  loadDemoWorkspace: async () => {
    set({ isLoading: true, connectStatus: 'Loading demo workspace...', errorMessage: null });
    try {
      const run = await chronosApi.ingestDemo();
      await get().refreshGraph();
      set({
        lastIngestionRun: run,
        connectStatus: `Demo workspace loaded: ${run.nodes_created} nodes, ${run.edges_created} edges.`,
        backendStatus: 'connected',
        isLoading: false,
        currentStep: 2,
      });
    } catch (error) {
      console.warn('Demo ingestion failed.', error);
      set({
        backendStatus: 'disconnected',
        connectStatus: null,
        errorMessage: getErrorMessage(error, 'Demo ingestion is unavailable.'),
        isLoading: false,
      });
    }
  },

  ingestGithubRepo: async (repo) => {
    set({ isLoading: true, connectStatus: `Ingesting ${repo}...`, errorMessage: null });
    try {
      const run = await chronosApi.ingestGithub({ repo });
      await get().refreshGraph();
      set({
        lastIngestionRun: run,
        connectStatus: `GitHub repo ingested: ${run.nodes_created} nodes, ${run.edges_created} edges.`,
        backendStatus: 'connected',
        isLoading: false,
      });
    } catch (error) {
      console.warn('GitHub ingestion failed.', error);
      set({
        connectStatus: null,
        errorMessage: getErrorMessage(error, 'GitHub ingestion is unavailable.'),
        isLoading: false,
      });
    }
  },

  uploadFiles: async (files) => {
    set({ isLoading: true, connectStatus: 'Uploading files...', errorMessage: null });
    try {
      const run = await chronosApi.ingestUpload(files);
      await get().refreshGraph();
      set({
        lastIngestionRun: run,
        connectStatus: `Files ingested: ${run.nodes_created} nodes, ${run.edges_created} edges.`,
        backendStatus: 'connected',
        isLoading: false,
      });
    } catch (error) {
      console.warn('Upload ingestion failed.', error);
      set({
        connectStatus: null,
        errorMessage: getErrorMessage(error, 'File upload ingestion is unavailable.'),
        isLoading: false,
      });
    }
  },

  runSimulation: async () => {
    set({ isLoading: true, errorMessage: null });

    try {
      const state = get();
      const simulationRequest = buildSimulationRequest(state);

      let intakeAnalysis: IntakeAnalysis | null = null;
      try {
        intakeAnalysis = await chronosApi.analyzeIntake({
          decisionQuestion: state.decisionQuestion,
          decisionType: state.decisionType,
          horizon: state.horizon,
          risk: state.risk,
          goal: state.goal,
          constraints: state.constraints,
          geography: state.geography,
          options: getOptions(state),
          evidenceCount: state.externalEvidence.length,
          precedentCount: state.historicalPrecedents.length,
        });
      } catch (error) {
        console.warn('/intake/analyze unavailable; continuing simulation.', error);
      }

      let digitalTwinProfile: DigitalTwinProfile | null = null;
      try {
        digitalTwinProfile = await chronosApi.buildDigitalTwin({
          decisionQuestion: state.decisionQuestion,
          decisionType: state.decisionType,
          goal: state.goal,
          constraints: state.constraints,
          geography: state.geography,
          options: getOptions(state),
          useGraph: true,
          useEvidence: true,
        });
      } catch (error) {
        console.warn('/digital-twin/build unavailable; continuing simulation.', error);
      }

      const simulation = await chronosApi.simulate(simulationRequest);

      let graphData = state.graphData;
      try {
        graphData = await get().refreshGraph();
      } catch (error) {
        console.warn('/graph refresh failed after simulation.', error);
      }

      let historicalPrecedents: HistoricalPrecedent[] = [];
      try {
        historicalPrecedents = (await chronosApi.findSimilar(state.decisionQuestion, 5)).items;
      } catch (error) {
        console.warn('/query/similar unavailable; continuing without precedents.', error);
      }

      const simulationData: SimulationPayload = {
        metadata: simulation.metadata,
        timelines: simulation.timelines.map(normalizeTimeline),
        recommendedTimelineId: simulation.recommendedTimelineId,
        affectedNodeIds: simulation.affectedNodeIds,
        isDemoEvidence: simulation.isDemoEvidence,
        evidenceProvider: simulation.evidenceProvider,
      };

      set({
        backendStatus: 'connected',
        graphData,
        simulationData,
        intakeAnalysis: simulation.intakeAnalysis ?? intakeAnalysis,
        digitalTwinProfile,
        historicalPrecedents,
        externalEvidence: simulation.externalEvidenceUsed,
        agentCouncil: simulation.agentCouncil,
        selectedTimelineId: simulation.recommendedTimelineId,
        isLoading: false,
        currentStep: 3,
      });
    } catch (error) {
      console.warn('Simulation failed.', error);
      set({
        errorMessage: getErrorMessage(error, 'Simulation failed. Confirm the backend is running.'),
        isLoading: false,
      });
    }
  },
}));
