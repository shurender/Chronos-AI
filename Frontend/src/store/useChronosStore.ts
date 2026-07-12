import { create } from 'zustand';

import { adaptBackendGraphToFrontendGraph, chronosApi } from '../api/chronosApi';
import type {
  AgentCouncil,
  ConnectorProvider,
  ConnectorSource,
  ConnectorSyncOptions,
  ConnectorStatus,
  DigitalTwinProfile,
  EvidenceItem,
  GithubRepoCheckResponse,
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
  activeSection: string;
  isCurtainVisible: boolean;
  isCurtainAnimatingOut: boolean;
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
  githubRepoCheck: GithubRepoCheckResponse | null;
  connectorStatuses: Record<ConnectorProvider, ConnectorStatus>;
  connectorSources: Record<ConnectorProvider, ConnectorSource[]>;
  selectedConnectorSourceIds: Record<ConnectorProvider, string[]>;
  chatHistory: ChatMessage[];
  isLoading: boolean;
}

export interface ChronosStoreActions {
  setStep: (step: number) => void;
  setActiveSection: (section: string) => void;
  triggerAppLaunch: () => void;
  setCurtainState: (visible: boolean, animatingOut: boolean) => void;
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
  refreshConnectors: () => Promise<void>;
  startConnector: (provider: ConnectorProvider) => void;
  loadConnectorSources: (provider: ConnectorProvider) => Promise<void>;
  selectConnectorSources: (provider: ConnectorProvider, sourceIds: string[]) => Promise<void>;
  syncConnector: (provider: ConnectorProvider, options?: ConnectorSyncOptions) => Promise<void>;
  disconnectConnector: (provider: ConnectorProvider) => Promise<void>;
  setSelectedTimelineId: (timelineId: string | null) => void;
  loadDemoWorkspace: () => Promise<void>;
  checkGithubRepo: (repo: string) => Promise<void>;
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
    source_type: (citation as any).source_type ?? undefined,
    source_name: (citation as any).source_name ?? undefined,
    source_url: (citation as any).source_url ?? undefined,
    timestamp: (citation as any).timestamp ?? undefined,
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

function defaultConnectorStatus(provider: ConnectorProvider): ConnectorStatus {
  return {
    provider,
    status: 'not_connected',
    connected: false,
    last_synced: null,
    error: null,
    source_counts: {},
  };
}

function mergeConnectorStatuses(
  statuses: ConnectorStatus[],
): Record<ConnectorProvider, ConnectorStatus> {
  const next = {
    github: defaultConnectorStatus('github'),
    slack: defaultConnectorStatus('slack'),
    notion: defaultConnectorStatus('notion'),
  };
  for (const status of statuses) {
    next[status.provider] = status;
  }
  return next;
}

function emptyProviderRecord<T>(value: T): Record<ConnectorProvider, T> {
  return { github: value, slack: value, notion: value };
}

function ingestionSummary(run: IngestionRun, label: string): string {
  const base = `${label}: ${run.nodes_created} nodes, ${run.edges_created} edges.`;
  const fileBits =
    run.files_received > 0
      ? ` Files: ${run.files_parsed}/${run.files_received} parsed${run.files_failed ? `, ${run.files_failed} failed` : ''}.`
      : '';
  const warning = run.warnings.length ? ` Warning: ${run.warnings[0]}` : '';
  return `${base}${fileBits}${warning}`;
}

function ingestionIssues(run: IngestionRun): string | null {
  const issues = [...run.errors, ...run.warnings].filter(Boolean);
  if (!issues.length) return null;
  if (issues.length === 1) return issues[0];
  return `${issues[0]} ${issues.length - 1} more issue(s) were reported.`;
}

export const useChronosStore = create<ChronosStore>((set, get) => ({
  currentStep: 0,
  activeSection: 'chronos-top',
  isCurtainVisible: true,
  isCurtainAnimatingOut: false,
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
  githubRepoCheck: null,
  connectorStatuses: {
    github: defaultConnectorStatus('github'),
    slack: defaultConnectorStatus('slack'),
    notion: defaultConnectorStatus('notion'),
  },
  connectorSources: emptyProviderRecord([]),
  selectedConnectorSourceIds: emptyProviderRecord([]),
  chatHistory: [],
  isLoading: false,

  setStep: (step) => set({ currentStep: step }),
  setActiveSection: (section) => set({ activeSection: section }),
  setCurtainState: (visible, animatingOut) =>
    set({ isCurtainVisible: visible, isCurtainAnimatingOut: animatingOut }),
  triggerAppLaunch: () => {
    set({ isCurtainVisible: true, isCurtainAnimatingOut: false });
    setTimeout(() => {
      set({ currentStep: 1 });
      document.getElementById('main-scroll-area')?.scrollTo(0, 0);
      set({ isCurtainAnimatingOut: true });
      setTimeout(() => {
        set({ isCurtainVisible: false });
      }, 1000);
    }, 800);
  },
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

  refreshConnectors: async () => {
    try {
      const statuses = await chronosApi.getConnectors();
      set({ connectorStatuses: mergeConnectorStatuses(statuses), backendStatus: 'connected' });
    } catch (error) {
      console.warn('Connector status refresh failed.', error);
      set({ errorMessage: getErrorMessage(error, 'Connector status is unavailable.') });
    }
  },

  startConnector: (provider) => {
    window.location.href = chronosApi.getConnectorStartUrl(provider);
  },

  loadConnectorSources: async (provider) => {
    try {
      const [sources, selected] = await Promise.all([
        chronosApi.getConnectorSources(provider),
        chronosApi.getSelectedConnectorSources(provider),
      ]);
      set((state) => ({
        connectorSources: { ...state.connectorSources, [provider]: sources },
        selectedConnectorSourceIds: {
          ...state.selectedConnectorSourceIds,
          [provider]: selected.sourceIds.length ? selected.sourceIds : sources.filter((source) => source.selected).map((source) => source.id),
        },
        backendStatus: 'connected',
      }));
    } catch (error) {
      console.warn(`${provider} source discovery failed.`, error);
      set({ errorMessage: getErrorMessage(error, `${provider} sources are unavailable.`) });
    }
  },

  selectConnectorSources: async (provider, sourceIds) => {
    try {
      const selected = await chronosApi.selectConnectorSources(provider, sourceIds);
      set((state) => ({
        selectedConnectorSourceIds: { ...state.selectedConnectorSourceIds, [provider]: selected.sourceIds },
        connectorSources: {
          ...state.connectorSources,
          [provider]: state.connectorSources[provider].map((source) => ({
            ...source,
            selected: selected.sourceIds.includes(source.id),
          })),
        },
        errorMessage: null,
      }));
    } catch (error) {
      console.warn(`${provider} source selection failed.`, error);
      set({ errorMessage: getErrorMessage(error, `${provider} source selection failed.`) });
    }
  },

  syncConnector: async (provider, options) => {
    set((state) => ({
      isLoading: true,
      errorMessage: null,
      connectStatus: `Syncing ${provider}...`,
      connectorStatuses: {
        ...state.connectorStatuses,
        [provider]: { ...state.connectorStatuses[provider], status: 'syncing', error: null },
      },
    }));
    try {
      const sourceIds = options?.sourceIds ?? get().selectedConnectorSourceIds[provider];
      const response = await chronosApi.syncConnector(provider, { ...options, sourceIds });
      if (response.run) {
        await get().refreshGraph();
      }
      await get().refreshConnectors();
      set({
        lastIngestionRun: response.run ?? get().lastIngestionRun,
        connectStatus: `${provider} synced: ${response.source_counts.nodes ?? 0} nodes, ${response.source_counts.edges ?? 0} edges.`,
        backendStatus: 'connected',
        isLoading: false,
      });
    } catch (error) {
      console.warn(`${provider} connector sync failed.`, error);
      set((state) => ({
        connectStatus: null,
        errorMessage: getErrorMessage(error, `${provider} connector is not available yet.`),
        isLoading: false,
        connectorStatuses: {
          ...state.connectorStatuses,
          [provider]: {
            ...state.connectorStatuses[provider],
            status: 'error',
            error: getErrorMessage(error, `${provider} connector is not available yet.`),
          },
        },
      }));
    }
  },

  disconnectConnector: async (provider) => {
    try {
      const status = await chronosApi.disconnectConnector(provider);
      set((state) => ({
        connectorStatuses: { ...state.connectorStatuses, [provider]: status },
        connectStatus: `${provider} disconnected.`,
      }));
    } catch (error) {
      console.warn(`${provider} disconnect failed.`, error);
      set({ errorMessage: getErrorMessage(error, `${provider} disconnect failed.`) });
    }
  },

  setSelectedTimelineId: (selectedTimelineId) => set({ selectedTimelineId }),

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

  checkGithubRepo: async (repo) => {
    set({ isLoading: true, connectStatus: `Checking ${repo}...`, errorMessage: null, githubRepoCheck: null });
    try {
      const check = await chronosApi.checkGithubRepo({ repo });
      set({
        githubRepoCheck: check,
        connectStatus: check.exists ? check.message : null,
        errorMessage: check.exists ? null : check.message,
        backendStatus: 'connected',
        isLoading: false,
      });
    } catch (error) {
      console.warn('GitHub repo check failed.', error);
      set({
        connectStatus: null,
        errorMessage: getErrorMessage(error, 'Could not verify this GitHub repository.'),
        isLoading: false,
      });
    }
  },

  ingestGithubRepo: async (repo) => {
    set({ isLoading: true, connectStatus: `Ingesting ${repo}...`, errorMessage: null });
    try {
      const run = await chronosApi.ingestGithub({ repo });
      await get().refreshGraph();
      const hasUsefulOutput = run.chunks_created > 0 || run.nodes_created > 0 || run.edges_created > 0;
      set({
        lastIngestionRun: run,
        connectStatus: `GitHub repo ingested: ${run.chunks_created} chunks, ${run.nodes_created} nodes, ${run.edges_created} edges.`,
        errorMessage: hasUsefulOutput ? null : 'Repo was reachable, but no useful commits/issues were ingested. Try another public repo with recent commits or issues.',
        backendStatus: 'connected',
        isLoading: false,
        currentStep: hasUsefulOutput ? 2 : get().currentStep,
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
        connectStatus: ingestionSummary(run, 'Files ingested'),
        errorMessage: ingestionIssues(run),
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
        dataCoverage: simulation.dataCoverage,
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
