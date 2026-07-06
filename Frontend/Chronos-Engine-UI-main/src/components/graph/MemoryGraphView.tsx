import dagre from '@dagrejs/dagre';
import { useMemo } from 'react';
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

import { useChronosStore } from '../../store/useChronosStore';
import type { GraphEdge, GraphNode } from '../../types/graph';
import { GraphNodeCard, type GraphNodeCardData } from './GraphNodeCard';

/** Must match GraphNodeCard fixed dimensions for accurate dagre layout. */
export const GRAPH_NODE_WIDTH = 250;
export const GRAPH_NODE_HEIGHT = 100;

const nodeTypes: NodeTypes = {
  graphNodeCard: GraphNodeCard,
};

const EDGE_STROKE: Record<GraphEdge['type'], string> = {
  causal: '#6366f1',
  temporal: '#94a3b8',
  contributory: '#64748b',
};

function mapGraphNodeToFlowNode(graphNode: GraphNode): Node<GraphNodeCardData> {
  return {
    id: graphNode.id,
    type: 'graphNodeCard',
    data: { graphNode },
    position: { x: 0, y: 0 },
  };
}

function mapGraphEdgeToFlowEdge(graphEdge: GraphEdge): Edge {
  return {
    id: graphEdge.id,
    source: graphEdge.source,
    target: graphEdge.target,
    label: graphEdge.label,
    animated: graphEdge.type === 'temporal',
    style: {
      stroke: EDGE_STROKE[graphEdge.type],
      strokeWidth: 1.5,
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
    const positioned = dagreGraph.node(node.id) as { x: number; y: number };

    return {
      ...node,
      position: {
        x: positioned.x - GRAPH_NODE_WIDTH / 2,
        y: positioned.y - GRAPH_NODE_HEIGHT / 2,
      },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    };
  });

  return { nodes: layoutedNodes, edges };
}

export function MemoryGraphView() {
  const graphData = useChronosStore((state) => state.graphData);

  const { nodes, edges } = useMemo(() => {
    if (!graphData) {
      return { nodes: [] as Node<GraphNodeCardData>[], edges: [] as Edge[] };
    }

    const flowNodes = graphData.nodes.map(mapGraphNodeToFlowNode);
    const flowEdges = graphData.edges.map(mapGraphEdgeToFlowEdge);

    return getLayoutedElements(flowNodes, flowEdges);
  }, [graphData]);

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
    <div className="h-full w-full">
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
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} size={1} color="#e5e7eb" />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor="#c7d2fe"
          maskColor="rgba(243, 244, 246, 0.75)"
          className="!bg-white"
        />
      </ReactFlow>
    </div>
  );
}
