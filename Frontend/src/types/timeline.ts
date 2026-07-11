/**
 * @file timeline.ts
 * @description Domain contracts for timeline simulation and probabilistic forecasting.
 * Cross-references {@link Citation} and {@link VeracityType} from the graph domain.
 */

import type { Citation, GraphNodeId, VeracityType } from './graph';

// ---------------------------------------------------------------------------
// Primitive unions
// ---------------------------------------------------------------------------

/**
 * Semantic classification of a point on a projected timeline.
 */
export type MilestoneType =
  | 'decision_point'
  | 'outcome_realized'
  | 'external_event'
  | 'skill_milestone'
  | 'project_phase';

/**
 * Lifecycle state of a simulated timeline branch.
 */
export type TimelineStatus = 'active' | 'archived' | 'recommended';

// ---------------------------------------------------------------------------
// Confidence & disagreement
// ---------------------------------------------------------------------------

/**
 * Decomposed confidence vector used by Recharts radar / breakdown UIs.
 * Every factor is independently normalized. Range per field: 0.0–1.0.
 */
export interface ConfidenceBreakdown {
  /** Strength and completeness of underlying evidence. Range: 0.0–1.0. */
  readonly evidenceStrength: number;

  /** Reliability of cited sources. Range: 0.0–1.0. */
  readonly sourceReliability: number;

  /** Inter-agent or inter-model agreement. Range: 0.0–1.0. */
  readonly modelConsensus: number;

  /** Temporal proximity of data to the projected milestone. Range: 0.0–1.0. */
  readonly temporalRelevance: number;

  /** Strength of causal linkage in the supporting graph. Range: 0.0–1.0. */
  readonly causalCoherence: number;
}

export interface DataCoverage {
  readonly graphNodes: number;
  readonly relevantPrecedents: number;
  readonly liveEvidence: number;
  readonly demoEvidence: number;
  readonly connectorSources: number;
  readonly uploadedSources: number;
  readonly digitalTwinCompleteness: number;
  readonly intakeCompleteness: number;
  readonly overallCoverage: number;
  readonly gaps: readonly string[];
}

/**
 * Records dissent between autonomous agents during simulation.
 */
export interface AgentDisagreement {
  /** Unique agent identifier (e.g. `"strategist"`, `"risk_analyst"`). */
  readonly agentId: string;

  /** Short human-readable name for UI display. */
  readonly agentLabel: string;

  /** The agent's stated position on this timeline branch. */
  readonly position: string;

  /** Agent confidence in its stated position. Range: 0.0–1.0. */
  readonly confidence: number;

  /** Structured rationale bullets for expandable UI panels. */
  readonly rationale: readonly string[];
}

// ---------------------------------------------------------------------------
// Milestones & timelines
// ---------------------------------------------------------------------------

/**
 * A single projected event along a timeline branch.
 * Citations MUST reference {@link GraphNodeId} values present in the companion graph.
 */
export interface TimelineMilestone {
  /**
   * Zero-based month offset from simulation origin (t=0).
   * Month 0 represents the decision point / present.
   */
  readonly month: number;

  /** Event headline rendered on the timeline axis. */
  readonly event: string;

  readonly type: MilestoneType;

  readonly veracity: VeracityType;

  /**
   * Evidence chain. Each {@link Citation.nodeId} MUST resolve to a
   * {@link GraphNode} in the associated knowledge graph payload.
   */
  readonly citations: readonly Citation[];

  /**
   * Inverse data density at this point (1.0 = no data, 0.0 = fully observed).
   * Drives sparsity warnings in the UI. Range: 0.0–1.0.
   */
  readonly dataSparsity: number;
}

/**
 * A single probabilistic future branch produced by the Chronos simulation engine.
 */
export interface Timeline {
  readonly id: string;

  readonly title: string;

  /** Narrative summary of this branch outcome. */
  readonly description: string;

  /**
   * Relative likelihood of this branch among siblings in a {@link SimulationPayload}.
   * Range: 0.0–1.0. Sibling probabilities SHOULD sum to ~1.0.
   */
  readonly probabilityScore: number;

  /**
   * Expected regret if this branch is chosen (higher = worse).
   * Range: 0.0–1.0.
   */
  readonly expectedRegret: number;

  readonly status: TimelineStatus;

  /** Ordered milestones along this branch (ascending by {@link month}). */
  readonly milestones: readonly TimelineMilestone[];

  readonly confidenceBreakdown: ConfidenceBreakdown;

  /**
   * Graph nodes most central to this branch narrative.
   * Enables cross-highlighting between timeline and graph views.
   */
  readonly anchorNodeIds: readonly GraphNodeId[];

  /** Dissenting agent positions, if any. */
  readonly agentDisagreements: readonly AgentDisagreement[];

  readonly evidenceUsed?: readonly string[];

  readonly claimIds?: readonly string[];
}

// ---------------------------------------------------------------------------
// Root payload
// ---------------------------------------------------------------------------

/**
 * Aggregate metadata for a simulation response.
 */
export interface SimulationMetadata {
  /** ISO-8601 timestamp of simulation completion. */
  readonly generatedAt: string;

  /** Schema or engine version for forward-compatible parsing. */
  readonly schemaVersion: string;

  /** Natural-language scenario query that triggered this simulation. */
  readonly query: string;

  /** Total projection horizon in months across all milestones. */
  readonly horizonMonths: number;
}

/**
 * Root JSON contract for `POST /simulate` (or equivalent) responses.
 */
export interface SimulationPayload {
  readonly metadata: SimulationMetadata;

  /** All simulated branches, including the recommended path. */
  readonly timelines: readonly Timeline[];

  /**
   * {@link Timeline.id} of the engine's recommended branch.
   * MUST reference an entry in {@link timelines}.
   */
  readonly recommendedTimelineId: string;

  /**
   * Graph nodes mutated or created during this simulation run.
   * Enables incremental graph merges without a full re-fetch.
   */
  readonly affectedNodeIds: readonly GraphNodeId[];

  readonly isDemoEvidence?: boolean;

  readonly evidenceProvider?: string | null;

  readonly dataCoverage?: DataCoverage;
}
