import dagre from '@dagrejs/dagre';
import { Search, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Position,
  type Edge,
  type Node,
  type NodeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { adaptBackendGraphToFrontendGraph, chronosApi } from '../../api/chronosApi';
import { useChronosStore } from '../../store/useChronosStore';
import type { GraphEdge, GraphNode, GraphPayload, GraphSummary, NodeType, VeracityType } from '../../types/graph';
import { GraphNodeCard, type GraphNodeCardData } from './GraphNodeCard';

export const GRAPH_NODE_WIDTH = 250;
export const GRAPH_NODE_HEIGHT = 100;

type GraphMode = 'overview' | 'decision' | 'source' | 'timeline';

const nodeTypes: NodeTypes = {
  graphNodeCard: GraphNodeCard,
};

const EDGE_STROKE: Record<GraphEdge['type'], string> = {
  causal: '#6366f1',
  temporal: '#94a3b8',
  contributory: '#64748b',
};

const NODE_FILTERS: NodeType[] = ['decision', 'outcome', 'person', 'project', 'skill'];
const VERACITY_FILTERS: VeracityType[] = ['fact', 'inference', 'prediction'];
const SOURCE_FILTERS = ['github', 'slack', 'notion', 'pdf', 'demo'];

function filterPayload(
  payload: GraphPayload,
  nodeFilters: Set<string>,
  veracityFilters: Set<string>,
  sourceFilters: Set<string>,
): GraphPayload {
  const nodes = payload.nodes.filter((node) => {
    const source = String(node.sourceType ?? 'unknown').toLowerCase();
    return (
      nodeFilters.has(node.type) &&
      veracityFilters.has(node.veracity) &&
      (sourceFilters.size === 0 || sourceFilters.has(source))
    );
  });
  const ids = new Set(nodes.map((node) => node.id));
  return {
    ...payload,
    nodes,
    edges: payload.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)),
  };
}

function importantPayload(payload: GraphPayload, maxNodes = 12): GraphPayload {
  if (payload.nodes.length <= maxNodes) return payload;
  const degree = new Map<string, number>();
  for (const edge of payload.edges) {
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1);
  }
  const selected = payload.nodes
    .slice()
    .sort((a, b) => (degree.get(b.id) ?? 0) + b.confidence - ((degree.get(a.id) ?? 0) + a.confidence))
    .slice(0, maxNodes);
  const ids = new Set(selected.map((node) => node.id));
  return {
    ...payload,
    nodes: selected,
    edges: payload.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)),
  };
}

function mapGraphNodeToFlowNode(graphNode: GraphNode, highlightedIds: Set<string>): Node<GraphNodeCardData> {
  return {
    id: graphNode.id,
    type: 'graphNodeCard',
    data: { graphNode, highlighted: highlightedIds.has(graphNode.id) },
    position: { x: 0, y: 0 },
  };
}

function mapGraphEdgeToFlowEdge(graphEdge: GraphEdge, highlightedIds: Set<string>): Edge {
  const highlighted = highlightedIds.has(graphEdge.source) || highlightedIds.has(graphEdge.target);
  return {
    id: graphEdge.id,
    source: graphEdge.source,
    target: graphEdge.target,
    label: graphEdge.label,
    animated: highlighted || graphEdge.type === 'temporal',
    style: {
      stroke: highlighted ? '#4f46e5' : EDGE_STROKE[graphEdge.type],
      strokeWidth: highlighted ? 2.5 : 1.5,
      strokeDasharray: graphEdge.type === 'contributory' ? '6 4' : undefined,
    },
    labelStyle: { fontSize: 10, fill: '#4b5563' },
    labelBgStyle: { fill: '#ffffff', fillOpacity: 0.9 },
  };
}

export function getLayoutedElements(
  nodes: Node<GraphNodeCardData>[],
  edges: Edge[],
): { nodes: Node<GraphNodeCardData>[]; edges: Edge[] } {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({
    rankdir: 'LR',
    nodesep: 48,
    ranksep: 72,
    marginx: 24,
    marginy: 24,
  });

  for (const node of nodes) {
    dagreGraph.setNode(node.id, {
      width: GRAPH_NODE_WIDTH,
      height: GRAPH_NODE_HEIGHT,
    });
  }

  for (const edge of edges) {
    dagreGraph.setEdge(edge.source, edge.target);
  }

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const positioned = dagreGraph.node(node.id) as { x: number; y: number } | undefined;

    return {
      ...node,
      position: {
        x: (positioned?.x ?? 0) - GRAPH_NODE_WIDTH / 2,
        y: (positioned?.y ?? 0) - GRAPH_NODE_HEIGHT / 2,
      },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    };
  });

  return { nodes: layoutedNodes, edges };
}

function Toggle({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'rounded-full border px-2.5 py-1 text-[11px] font-semibold capitalize',
        active ? 'border-gray-900 bg-gray-900 text-white' : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300',
      ].join(' ')}
    >
      {label}
    </button>
  );
}

function nodeWhy(node: GraphNode, edges: readonly GraphEdge[]) {
  const connected = edges.filter((edge) => edge.source === node.id || edge.target === node.id).length;
  if (node.type === 'decision') return `This decision anchors ${connected} relationship${connected === 1 ? '' : 's'} in the memory graph.`;
  if (node.type === 'outcome') return `This outcome shows what the graph thinks may follow from nearby decisions.`;
  if (node.type === 'person') return `This person appears in source evidence connected to decisions or projects.`;
  if (node.type === 'project') return `This project groups related source evidence and decisions.`;
  return `This skill contributes context to nearby decisions and outcomes.`;
}

export function MemoryGraphView() {
  const graphData = useChronosStore((state) => state.graphData);
  const simulationData = useChronosStore((state) => state.simulationData);
  const selectedTimelineId = useChronosStore((state) => state.selectedTimelineId);
  const [mode, setMode] = useState<GraphMode>('overview');
  const [query, setQuery] = useState('');
  const [focusedGraph, setFocusedGraph] = useState<GraphPayload | null>(null);
  const [summary, setSummary] = useState<GraphSummary | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [nodeFilters, setNodeFilters] = useState(() => new Set<string>(NODE_FILTERS));
  const [veracityFilters, setVeracityFilters] = useState(() => new Set<string>(VERACITY_FILTERS));
  const [sourceFilters, setSourceFilters] = useState(() => new Set<string>());

  useEffect(() => {
    chronosApi.getGraphSummary().then(setSummary).catch((error) => {
      console.warn('/graph/summary unavailable.', error);
    });
  }, []);

  useEffect(() => {
    if (!graphData || graphData.nodes.length <= 75) return;
    chronosApi.focusGraph({ depth: 1, limit: 50 })
      .then((payload) => setFocusedGraph(adaptBackendGraphToFrontendGraph(payload, query)))
      .catch((error) => console.warn('/graph/focus unavailable; using local summary.', error));
  }, [graphData, query]);

  const selectedTimeline = simulationData?.timelines.find((timeline) => timeline.id === selectedTimelineId);
  const highlightedIds = useMemo(() => {
    const ids = new Set<string>();
    if (!selectedTimeline) return ids;
    selectedTimeline.anchorNodeIds.forEach((id) => ids.add(id));
    selectedTimeline.evidenceUsed?.forEach((id) => ids.add(id));
    selectedTimeline.claimIds?.forEach((id) => ids.add(id));
    selectedTimeline.milestones.forEach((milestone) => milestone.citations.forEach((citation) => ids.add(citation.nodeId)));
    return ids;
  }, [selectedTimeline]);

  const basePayload = focusedGraph ?? graphData;
  const displayedPayload = useMemo(() => {
    if (!basePayload) return null;
    const initial = mode === 'overview' ? importantPayload(basePayload, graphData && graphData.nodes.length > 75 ? 12 : 20) : basePayload;
    const timelineFiltered = mode === 'timeline' && highlightedIds.size
      ? {
          ...initial,
          nodes: initial.nodes.filter((node) => highlightedIds.has(node.id)),
          edges: initial.edges.filter((edge) => highlightedIds.has(edge.source) && highlightedIds.has(edge.target)),
        }
      : initial;
    return filterPayload(timelineFiltered, nodeFilters, veracityFilters, sourceFilters);
  }, [basePayload, graphData, highlightedIds, mode, nodeFilters, sourceFilters, veracityFilters]);

  const { nodes, edges } = useMemo(() => {
    if (!displayedPayload) {
      return { nodes: [] as Node<GraphNodeCardData>[], edges: [] as Edge[] };
    }

    const flowNodes = displayedPayload.nodes.map((node) => mapGraphNodeToFlowNode(node, highlightedIds));
    const flowEdges = displayedPayload.edges.map((edge) => mapGraphEdgeToFlowEdge(edge, highlightedIds));

    return getLayoutedElements(flowNodes, flowEdges);
  }, [displayedPayload, highlightedIds]);

  const selectedNode = displayedPayload?.nodes.find((node) => node.id === selectedNodeId) ?? null;
  const isHairball = Boolean(graphData && graphData.nodes.length > 75);

  const toggleSet = (value: string, setter: (next: Set<string>) => void, current: Set<string>) => {
    const next = new Set(current);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    setter(next);
  };

  const runFocusSearch = async () => {
    try {
      const payload = await chronosApi.focusGraph({ query: query.trim(), depth: 1, limit: 50 });
      setFocusedGraph(adaptBackendGraphToFrontendGraph(payload, query));
      setMode(query.toLowerCase().includes('source') ? 'source' : 'decision');
    } catch (error) {
      console.warn('/graph/focus search failed.', error);
    }
  };

  if (!graphData) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-gray-50">
        <p className="text-sm text-gray-500">
          Run a simulation to load the memory graph.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full bg-white">
      <aside className="flex w-80 shrink-0 flex-col gap-4 border-r border-gray-200 bg-gray-50 p-4">
        <div>
          <h3 className="text-sm font-bold text-gray-900">Memory Graph</h3>
          <p className="mt-1 text-xs text-gray-500">
            {summary?.graphHealth.totalNodes ?? graphData.nodes.length} nodes / {summary?.graphHealth.totalEdges ?? graphData.edges.length} edges
          </p>
        </div>

        {isHairball && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            Showing focused graph; use search/filter to expand.
          </div>
        )}

        <div className="grid grid-cols-2 gap-2">
          {(['overview', 'decision', 'source', 'timeline'] as GraphMode[]).map((item) => (
            <button
              key={item}
              onClick={() => setMode(item)}
              className={[
                'rounded-lg border px-3 py-2 text-xs font-semibold capitalize',
                mode === item ? 'border-gray-900 bg-gray-900 text-white' : 'border-gray-200 bg-white text-gray-600',
              ].join(' ')}
            >
              {item === 'timeline' ? 'Timeline-linked' : `${item} mode`}
            </button>
          ))}
        </div>

        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute top-2.5 left-2.5 size-3.5 text-gray-400" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') void runFocusSearch();
              }}
              placeholder="Focus by decision, project, person..."
              className="w-full rounded-lg border border-gray-200 bg-white py-2 pr-3 pl-8 text-xs text-gray-900 placeholder:text-gray-400 focus:border-gray-900 focus:outline-none"
            />
          </div>
          <button onClick={() => void runFocusSearch()} className="rounded-lg bg-gray-900 px-3 text-xs font-semibold text-white">
            Focus
          </button>
        </div>

        <section>
          <h4 className="mb-2 text-[11px] font-bold tracking-wide text-gray-500 uppercase">Node Type</h4>
          <div className="flex flex-wrap gap-1.5">
            {NODE_FILTERS.map((item) => (
              <Toggle key={item} label={item} active={nodeFilters.has(item)} onClick={() => toggleSet(item, setNodeFilters, nodeFilters)} />
            ))}
          </div>
        </section>

        <section>
          <h4 className="mb-2 text-[11px] font-bold tracking-wide text-gray-500 uppercase">Veracity</h4>
          <div className="flex flex-wrap gap-1.5">
            {VERACITY_FILTERS.map((item) => (
              <Toggle key={item} label={item} active={veracityFilters.has(item)} onClick={() => toggleSet(item, setVeracityFilters, veracityFilters)} />
            ))}
          </div>
        </section>

        <section>
          <h4 className="mb-2 text-[11px] font-bold tracking-wide text-gray-500 uppercase">Source</h4>
          <div className="flex flex-wrap gap-1.5">
            {SOURCE_FILTERS.map((item) => (
              <Toggle key={item} label={item} active={sourceFilters.has(item)} onClick={() => toggleSet(item, setSourceFilters, sourceFilters)} />
            ))}
          </div>
          {sourceFilters.size > 0 && (
            <button onClick={() => setSourceFilters(new Set())} className="mt-2 text-[11px] font-semibold text-gray-500">
              Clear source filters
            </button>
          )}
        </section>

        <section>
          <h4 className="mb-2 text-[11px] font-bold tracking-wide text-gray-500 uppercase">Legend</h4>
          <div className="space-y-1 text-[11px] text-gray-600">
            <p><span className="font-semibold text-violet-600">Decision</span> choices or forks</p>
            <p><span className="font-semibold text-emerald-600">Outcome</span> observed or predicted results</p>
            <p><span className="font-semibold text-indigo-600">Project</span> source/project clusters</p>
            <p><span className="font-semibold text-emerald-700">Live badge</span> authenticated/live source</p>
          </div>
        </section>
      </aside>

      <div className="relative min-w-0 flex-1">
        {displayedPayload && displayedPayload.nodes.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-gray-500">No graph nodes match the current filters.</div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.2}
            maxZoom={1.5}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable
            onNodeClick={(_, node) => setSelectedNodeId(node.id)}
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={16} size={1} color="#e5e7eb" />
            <Controls showInteractive={false} />
            <MiniMap nodeColor="#c7d2fe" maskColor="rgba(243, 244, 246, 0.75)" className="!bg-white" />
          </ReactFlow>
        )}
      </div>

      {selectedNode && (
        <aside className="w-80 shrink-0 border-l border-gray-200 bg-white p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold tracking-wide text-gray-400 uppercase">{selectedNode.type}</p>
              <h3 className="mt-1 text-base font-semibold leading-snug text-gray-900">{selectedNode.label}</h3>
            </div>
            <button onClick={() => setSelectedNodeId(null)} className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700">
              <X className="size-4" />
            </button>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-gray-500">Confidence</p>
              <p className="font-bold text-gray-900">{Math.round(selectedNode.confidence * 100)}%</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-gray-500">Source</p>
              <p className="font-bold text-gray-900">{String(selectedNode.raw?.source_name ?? selectedNode.sourceType ?? selectedNode.source)}</p>
            </div>
          </div>
          {Boolean(selectedNode.raw?.source_url || selectedNode.raw?.external_id || selectedNode.raw?.timestamp) && (
            <section className="mt-5 rounded-lg border border-gray-100 bg-gray-50 p-3 text-xs text-gray-600">
              <h4 className="font-bold tracking-wide text-gray-500 uppercase">Source metadata</h4>
              {selectedNode.raw?.source_url && typeof selectedNode.raw.source_url === 'string' && selectedNode.raw.source_url.startsWith('http') ? (
                <a href={selectedNode.raw.source_url} target="_blank" rel="noreferrer" className="mt-2 block truncate font-semibold text-gray-900 underline underline-offset-2">
                  Open source
                </a>
              ) : selectedNode.raw?.source_url ? (
                <p className="mt-2 truncate">{String(selectedNode.raw.source_url)}</p>
              ) : null}
              {Boolean(selectedNode.raw?.external_id) && <p className="mt-1 truncate">ID: {String(selectedNode.raw?.external_id)}</p>}
              {Boolean(selectedNode.raw?.timestamp) && <p className="mt-1 truncate">Time: {String(selectedNode.raw?.timestamp)}</p>}
            </section>
          )}

          <section className="mt-5">
            <h4 className="text-xs font-bold tracking-wide text-gray-500 uppercase">Why this matters</h4>
            <p className="mt-2 text-sm leading-relaxed text-gray-600">{nodeWhy(selectedNode, displayedPayload?.edges ?? [])}</p>
          </section>

          <section className="mt-5">
            <h4 className="text-xs font-bold tracking-wide text-gray-500 uppercase">Connected decisions/outcomes</h4>
            <ul className="mt-2 space-y-2">
              {(displayedPayload?.edges ?? [])
                .filter((edge) => edge.source === selectedNode.id || edge.target === selectedNode.id)
                .slice(0, 6)
                .map((edge) => {
                  const otherId = edge.source === selectedNode.id ? edge.target : edge.source;
                  const other = displayedPayload?.nodes.find((node) => node.id === otherId);
                  return (
                    <li key={edge.id} className="rounded-lg border border-gray-100 bg-gray-50 p-2 text-xs text-gray-700">
                      {other?.label ?? otherId}
                    </li>
                  );
                })}
            </ul>
          </section>

          <section className="mt-5">
            <h4 className="text-xs font-bold tracking-wide text-gray-500 uppercase">Citations / chunks</h4>
            <div className="mt-2 space-y-2 text-xs text-gray-600">
              {selectedNode.citations.length ? selectedNode.citations.map((citation) => (
                <p key={`${citation.nodeId}-${citation.label}`} className="rounded-lg border border-gray-100 p-2">{citation.label}</p>
              )) : (
                <p className="rounded-lg border border-gray-100 p-2">{String(selectedNode.raw?.id ?? selectedNode.id)}</p>
              )}
            </div>
          </section>
        </aside>
      )}
    </div>
  );
}
