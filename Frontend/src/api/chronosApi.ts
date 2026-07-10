import { apiFetch } from './client';
import type {
  AvatarChatRequest,
  AvatarChatResponse,
  DigitalTwinBuildRequest,
  DigitalTwinProfile,
  EvidenceSearchResponse,
  GraphPayload,
  GraphResponse,
  HealthResponse,
  HistoricalPrecedent,
  IngestGithubRequest,
  IngestionRun,
  IntakeAnalysis,
  IntakeAnalyzeRequest,
  SimulationRequest,
  SimulationResponse,
} from './contracts';
import type {
  EdgeType,
  GraphEdge as FrontendGraphEdge,
  GraphPayload as FrontendGraphPayload,
  GraphSource,
  NodeType,
  VeracityType,
} from '../types/graph';

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.trim() ? value : fallback;
}

function asNumber(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function toNodeType(value: unknown): NodeType {
  const candidate = asString(value, 'decision');
  return ['decision', 'outcome', 'person', 'skill', 'project'].includes(candidate)
    ? (candidate as NodeType)
    : 'decision';
}

function toEdgeType(value: unknown): EdgeType {
  const candidate = asString(value, 'causal');
  return ['causal', 'temporal', 'contributory'].includes(candidate)
    ? (candidate as EdgeType)
    : 'causal';
}

function toVeracity(value: unknown): VeracityType {
  const candidate = asString(value, 'inference');
  return ['fact', 'inference', 'prediction'].includes(candidate)
    ? (candidate as VeracityType)
    : 'inference';
}

function toGraphSource(value: unknown): GraphSource {
  const candidate = asString(value, 'agent_inference');
  return ['user_input', 'document_ingest', 'agent_inference', 'external_api'].includes(candidate)
    ? (candidate as GraphSource)
    : 'agent_inference';
}

export function adaptBackendGraphToFrontendGraph(
  graph: GraphResponse | GraphPayload,
  query?: string,
): FrontendGraphPayload {
  return {
    metadata: {
      generatedAt: new Date().toISOString(),
      schemaVersion: '1.0.0',
      query,
    },
    nodes: graph.nodes.map((node) => {
      const id = asString(node.id ?? node.node_id, crypto.randomUUID());
      return {
        id,
        type: toNodeType(node.node_type ?? node.type),
        label: asString(node.label, id),
        veracity: toVeracity(node.evidence_type ?? node.veracity),
        confidence: asNumber(node.confidence, 0.5),
        source: toGraphSource(node.source),
        citations: [],
        hasGap: Boolean(node.hasGap ?? node.has_gap),
        hasContradiction: Boolean(node.hasContradiction ?? node.has_contradiction),
        summaryText: asString(node.description ?? node.summaryText),
      };
    }),
    edges: graph.edges.map((edge, index): FrontendGraphEdge => {
      const source = asString(edge.source ?? edge.source_node_id);
      const target = asString(edge.target ?? edge.target_node_id);
      return {
        id: asString(edge.id ?? edge.edge_id ?? edge.key, `${source}-${target}-${index}`),
        source,
        target,
        type: toEdgeType(edge.edge_type ?? edge.type),
        confidence: asNumber(edge.confidence, 0.5),
        veracity: toVeracity(edge.evidence_type ?? edge.veracity),
        label: asString(edge.description ?? edge.label),
      };
    }),
  };
}

export const chronosApi = {
  health: () => apiFetch<HealthResponse>('/health'),
  ready: () => apiFetch<{ ready: boolean }>('/health/ready'),
  getGraph: () => apiFetch<GraphResponse>('/graph'),
  ingestDemo: () => apiFetch<IngestionRun>('/ingest/demo', { method: 'POST' }),
  ingestGithub: (request: IngestGithubRequest) =>
    apiFetch<IngestionRun>('/ingest/github', {
      method: 'POST',
      body: JSON.stringify(request),
    }),
  ingestUpload: (files: FileList | File[]) => {
    const formData = new FormData();
    for (const file of Array.from(files)) {
      formData.append('files', file);
    }
    return apiFetch<IngestionRun>('/ingest/upload', {
      method: 'POST',
      body: formData,
    });
  },
  analyzeIntake: (request: IntakeAnalyzeRequest) =>
    apiFetch<IntakeAnalysis>('/intake/analyze', {
      method: 'POST',
      body: JSON.stringify(request),
    }),
  buildDigitalTwin: (request: DigitalTwinBuildRequest) =>
    apiFetch<DigitalTwinProfile>('/digital-twin/build', {
      method: 'POST',
      body: JSON.stringify(request),
    }),
  simulate: (request: SimulationRequest) =>
    apiFetch<SimulationResponse>('/simulate', {
      method: 'POST',
      body: JSON.stringify(request),
    }),
  findSimilar: (query: string, k = 5) =>
    apiFetch<{ items: HistoricalPrecedent[] }>(
      `/query/similar?q=${encodeURIComponent(query)}&k=${k}`,
    ),
  searchEvidence: (query: string, domain = '', k = 5) =>
    apiFetch<EvidenceSearchResponse>(
      `/evidence/search?query=${encodeURIComponent(query)}&domain=${encodeURIComponent(domain)}&k=${k}`,
    ),
  chat: (request: AvatarChatRequest) =>
    apiFetch<AvatarChatResponse>('/avatar/chat', {
      method: 'POST',
      body: JSON.stringify(request),
    }),
};
