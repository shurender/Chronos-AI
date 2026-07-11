/**
 * @file graph.ts
 * @description Root domain contracts for the Chronos knowledge graph.
 * All graph entities are immutable-friendly (readonly arrays) for safe UI consumption.
 */

// ---------------------------------------------------------------------------
// Primitive unions
// ---------------------------------------------------------------------------

/**
 * Epistemic classification of a claim or relationship.
 * Drives veracity badges and trust-weighting in the UI.
 */
export type VeracityType = 'fact' | 'inference' | 'prediction';

/**
 * Semantic category of a graph vertex.
 * Maps directly to React Flow node renderers and legend filters.
 */
export type NodeType =
  | 'decision'
  | 'outcome'
  | 'person'
  | 'skill'
  | 'project';

export type SourceType = 'github' | 'slack' | 'notion' | 'pdf' | 'demo' | 'upload' | 'unknown';

/**
 * Semantic category of a directed graph edge.
 * Determines edge styling, arrowheads, and layout algorithms.
 */
export type EdgeType = 'causal' | 'temporal' | 'contributory';

/**
 * Stable identifier for a {@link GraphNode}.
 * Backend MUST guarantee uniqueness within a single {@link GraphPayload}.
 */
export type GraphNodeId = string;

/**
 * Stable identifier for a {@link GraphEdge}.
 */
export type GraphEdgeId = string;

// ---------------------------------------------------------------------------
// Supporting entities
// ---------------------------------------------------------------------------

/**
 * Provenance record linking narrative text to a substantiating graph node.
 * Shared across graph nodes and timeline milestones for citation drill-down.
 */
export interface Citation {
  /** {@link GraphNode.id} that this citation substantiates or references. */
  readonly nodeId: GraphNodeId;

  /** Human-readable citation label (e.g. source title or node label). */
  readonly label: string;

  /** Optional verbatim excerpt from the underlying source. */
  readonly excerpt?: string;

  /** Optional URI to the primary source document. */
  readonly url?: string;

  readonly source_type?: string;

  readonly source_name?: string;

  readonly source_url?: string;

  readonly timestamp?: string;
}

/**
 * Provenance descriptor for how a node was derived.
 */
export type GraphSource =
  | 'user_input'
  | 'document_ingest'
  | 'agent_inference'
  | 'external_api';

// ---------------------------------------------------------------------------
// Core graph entities
// ---------------------------------------------------------------------------

/**
 * A single vertex in the Chronos decision-intelligence knowledge graph.
 */
export interface GraphNode {
  readonly id: GraphNodeId;

  readonly type: NodeType;

  /** Primary display label rendered on the canvas. */
  readonly label: string;

  readonly veracity: VeracityType;

  /** Model confidence in this node's existence and classification. Range: 0.0–1.0. */
  readonly confidence: number;

  /** Origin channel for audit trails and filtering. */
  readonly source: GraphSource;

  /**
   * Supporting citations. Each {@link Citation.nodeId} SHOULD resolve to an
   * existing node within the same {@link GraphPayload} (self-reference or peer).
   */
  readonly citations: readonly Citation[];

  /**
   * When true, the UI MUST surface a data-gap warning (missing evidence chain).
   */
  readonly hasGap: boolean;

  /**
   * When true, the UI MUST surface a contradiction warning (conflicting claims).
   */
  readonly hasContradiction: boolean;

  /** Optional expanded narrative shown in detail panels. */
  readonly summaryText?: string;

  readonly sourceType?: SourceType | string;

  readonly sourceAuth?: string;

  readonly sourceLive?: boolean;

  readonly raw?: Record<string, unknown>;
}

/**
 * A directed, typed relationship between two {@link GraphNode} instances.
 */
export interface GraphEdge {
  readonly id: GraphEdgeId;

  /** {@link GraphNode.id} of the edge origin. */
  readonly source: GraphNodeId;

  /** {@link GraphNode.id} of the edge target. */
  readonly target: GraphNodeId;

  readonly type: EdgeType;

  /** Confidence in the stated relationship. Range: 0.0–1.0. */
  readonly confidence: number;

  readonly veracity: VeracityType;

  /** Optional edge label rendered along the connector. */
  readonly label?: string;
}

/**
 * Aggregate metadata for a graph payload response.
 */
export interface GraphMetadata {
  /** ISO-8601 timestamp of graph generation. */
  readonly generatedAt: string;

  /** Schema or engine version for forward-compatible parsing. */
  readonly schemaVersion: string;

  /** Natural-language query that produced this graph, if applicable. */
  readonly query?: string;
}

/**
 * Root JSON contract for `GET /graph` (or equivalent) responses.
 */
export interface GraphPayload {
  readonly nodes: readonly GraphNode[];

  readonly edges: readonly GraphEdge[];

  readonly metadata: GraphMetadata;
}

export interface GraphSummary {
  nodeCountsByType: Record<string, number>;
  edgeCountsByType: Record<string, number>;
  topProjects: Array<{ label: string; count: number }>;
  topDecisions: Array<{ id: string; label: string; confidence: number; degree: number; source_type?: string }>;
  topOutcomes: Array<{ id: string; label: string; confidence: number; degree: number; source_type?: string }>;
  topPeople: Array<{ id: string; label: string; confidence: number; degree: number; source_type?: string }>;
  recentSources: Array<{ id: string; label: string; timestamp?: string; source_type?: string }>;
  mostConnectedNodes: Array<{ id: string; label: string; type: string; degree: number; confidence: number }>;
  graphHealth: {
    totalNodes: number;
    totalEdges: number;
    orphanNodes: number;
    averageDegree: number;
  };
}
