import { create } from 'zustand';

import { mockGraphPayload } from '../mocks/graph.mock';
import { mockSimulationPayload } from '../mocks/timeline.mock';
import type { ChatMessage } from '../types/avatar';
import type { GraphPayload } from '../types/graph';
import type { SimulationPayload } from '../types/timeline';

/** Simulated network latency for `runSimulation` (ms). */
const SIMULATION_DELAY_MS = 2500;

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

    await new Promise<void>((resolve) => {
      setTimeout(resolve, SIMULATION_DELAY_MS);
    });

    set({
      graphData: mockGraphPayload,
      simulationData: mockSimulationPayload,
      isLoading: false,
      currentStep: 3,
    });
  },
}));
