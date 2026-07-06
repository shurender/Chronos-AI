import { Handle, Position, type NodeProps } from 'reactflow';

import type { GraphNode, NodeType } from '../../types/graph';
import { GapWarningBadge } from '../ui/GapWarningBadge';
import { VeracityBadge } from '../ui/VeracityBadge';

/** Payload attached to each React Flow node instance. */
export interface GraphNodeCardData {
  readonly graphNode: GraphNode;
}

const NODE_TYPE_LABEL: Record<NodeType, string> = {
  decision: 'Decision',
  outcome: 'Outcome',
  person: 'Person',
  skill: 'Skill',
  project: 'Project',
};

const NODE_TYPE_ACCENT: Record<NodeType, string> = {
  decision: 'border-l-violet-500',
  outcome: 'border-l-emerald-500',
  person: 'border-l-sky-500',
  skill: 'border-l-orange-500',
  project: 'border-l-indigo-500',
};

export function GraphNodeCard({ data }: NodeProps<GraphNodeCardData>) {
  const { graphNode } = data;

  const borderClass = graphNode.hasGap
    ? 'border-2 border-dashed border-amber-400'
    : graphNode.hasContradiction
      ? 'border-2 border-red-300'
      : 'border border-gray-200';

  return (
    <div
      className={[
        'flex h-[100px] w-[250px] flex-col justify-between rounded-lg bg-white p-3 shadow-sm',
        'border-l-4',
        NODE_TYPE_ACCENT[graphNode.type],
        borderClass,
      ].join(' ')}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!size-2 !border-2 !border-gray-300 !bg-white"
      />

      <div className="flex items-start justify-between gap-2">
        <span className="text-[10px] font-semibold tracking-wide text-gray-400 uppercase">
          {NODE_TYPE_LABEL[graphNode.type]}
        </span>
        <span className="text-[10px] font-medium text-gray-400 tabular-nums">
          {Math.round(graphNode.confidence * 100)}%
        </span>
      </div>

      <p className="line-clamp-2 text-sm leading-snug font-medium text-gray-900">
        {graphNode.label}
      </p>

      <div className="flex flex-wrap items-center gap-1">
        <VeracityBadge type={graphNode.veracity} />
        {graphNode.hasGap && <GapWarningBadge />}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!size-2 !border-2 !border-gray-300 !bg-white"
      />
    </div>
  );
}
