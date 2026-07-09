import { create } from 'zustand';

import { mockGraphPayload } from '../mocks/graph.mock';
import { mockSimulationPayload } from '../mocks/timeline.mock';
import type { ChatMessage } from '../types/avatar';
import type { GraphPayload } from '../types/graph';
import type { SimulationPayload } from '../types/timeline';

export interface ChronosStoreState {
  currentStep: number;
  decisionQuestion: string;
  graphData: GraphPayload | null;
  simulationData: SimulationPayload | null;
  chatHistory: ChatMessage[];
  isLoading: boolean;
}

export interface ChronosStoreActions {
  setStep: (step: number) => void;
  setDecisionQuestion: (question: string) => void;
  addChatMessage: (msg: ChatMessage) => void;
  runSimulation: () => Promise<void>;
}

export type ChronosStore = ChronosStoreState & ChronosStoreActions;

export const useChronosStore = create<ChronosStore>((set, get) => ({
  currentStep: 0,
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

      // 2. Fetch Forecast Data from Backend
      const forecastRes = await fetch('http://localhost:8000/forecast/decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: get().decisionQuestion,
          type: "Startup",
          horizon: "3 years",
          risk: 50,
          goal: "Maximize upside"
        })
      });
      const forecastData = await forecastRes.json();
      console.log("Backend Forecast Received:", forecastData);

      set({
        graphData: actualGraphData, // Powered by your LIVE Python Backend!
        simulationData: mockSimulationPayload, // Using mock until python returns `timelines`
        isLoading: false,
        currentStep: 3,
      });

    } catch (error) {
      console.warn("Backend not running or failed. Falling back to mock data.", error);
      // Fallback to mocks if backend isn't running so the UI doesn't break during demos
      set({
        graphData: mockGraphPayload,
        simulationData: mockSimulationPayload,
        isLoading: false,
        currentStep: 3,
      });
    }
  },
}));