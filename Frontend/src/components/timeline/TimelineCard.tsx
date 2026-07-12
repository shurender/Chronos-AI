import type { Timeline, TimelineMilestone } from '../../types/timeline';
import { VeracityBadge } from '../ui/VeracityBadge';
import { ConfidenceBreakdownBar } from './ConfidenceBreakdownBar';

type RegretLevel = 'High' | 'Med' | 'Low';

interface RegretStyle {
  readonly label: RegretLevel;
  readonly bg: string;
  readonly text: string;
  readonly border: string;
}

const REGRET_STYLES: Record<RegretLevel, RegretStyle> = {
  High: {
    label: 'High',
    bg: 'bg-red-100',
    text: 'text-red-700',
    border: 'border-red-300',
  },
  Med: {
    label: 'Med',
    bg: 'bg-yellow-100',
    text: 'text-yellow-800',
    border: 'border-yellow-300',
  },
  Low: {
    label: 'Low',
    bg: 'bg-green-100',
    text: 'text-green-700',
    border: 'border-green-300',
  },
};

function getRegretLevel(regret: number): RegretLevel {
  if (regret >= 0.65) return 'High';
  if (regret >= 0.35) return 'Med';
  return 'Low';
}

function formatProbability(score: number): string {
  return `${Math.round(score * 100)}%`;
}

function formatMonth(month: number): string {
  return month === 0 ? 'M0 · Now' : `M+${month}`;
}

/** Rows with high data sparsity (sparse evidence) render at reduced opacity. */
function milestoneOpacity(dataSparsity: number): number {
  return Math.max(0.45, 1 - dataSparsity * 0.55);
}

export interface TimelineCardProps {
  readonly timeline: Timeline;
  readonly className?: string;
  readonly selected?: boolean;
  readonly onSelect?: (timelineId: string) => void;
}

function MilestoneRow({ milestone }: { readonly milestone: TimelineMilestone }) {
  return (
    <li
      className="relative flex flex-col gap-1.5 pb-4 pl-5 last:pb-0"
      style={{ opacity: milestoneOpacity(milestone.dataSparsity) }}
    >
      <span
        className="absolute top-1.5 left-0 size-2 -translate-x-1/2 rounded-full bg-indigo-400 ring-2 ring-white"
        aria-hidden="true"
      />
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold tracking-wide text-indigo-600 uppercase">
          {formatMonth(milestone.month)}
        </span>
        <VeracityBadge type={milestone.veracity} />
      </div>
      <p className="text-sm leading-snug text-gray-700">{milestone.event}</p>
    </li>
  );
}

export function TimelineCard({ timeline, className = '', selected = false, onSelect }: TimelineCardProps) {
  const regretLevel = getRegretLevel(timeline.expectedRegret);
  const regretStyle = REGRET_STYLES[regretLevel];
  const isRecommended = timeline.status === 'recommended';

  return (
    <article
      onClick={() => onSelect?.(timeline.id)}
      className={[
        'flex w-full min-w-0 flex-col rounded-xl border bg-white shadow-sm lg:w-96 lg:shrink-0',
        onSelect ? 'cursor-pointer transition hover:border-indigo-300' : '',
        selected
          ? 'border-indigo-500 ring-2 ring-indigo-200'
          : isRecommended
          ? 'border-indigo-300 ring-2 ring-indigo-100'
          : 'border-gray-200',
        className,
      ].join(' ')}
      aria-label={`Timeline: ${timeline.title}`}
    >
      <header className="flex flex-col gap-3 border-b border-gray-100 px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-base leading-snug font-semibold text-gray-900">
            {timeline.title}
          </h3>
          {isRecommended && (
            <span className="shrink-0 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">
              Recommended
            </span>
          )}
        </div>

        <p className="text-sm leading-relaxed text-gray-500">
          {timeline.description}
        </p>

        <div className="flex items-center justify-between gap-3">
          <div className="flex flex-col">
            <span className="text-xs font-medium text-gray-500">
              Probability
            </span>
            <span className="text-2xl font-bold tracking-tight text-gray-900 tabular-nums">
              {formatProbability(timeline.probabilityScore)}
            </span>
          </div>

          <div className="flex flex-col items-end gap-1">
            <span className="text-xs font-medium text-gray-500">
              Expected Regret
            </span>
            <span
              className={[
                'inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold',
                regretStyle.bg,
                regretStyle.text,
                regretStyle.border,
              ].join(' ')}
            >
              {regretStyle.label}
            </span>
          </div>
        </div>
      </header>

      <div className="border-b border-gray-100 px-5 py-4">
        <h4 className="mb-3 text-xs font-semibold tracking-wide text-gray-500 uppercase">
          Confidence Breakdown
        </h4>
        <ConfidenceBreakdownBar breakdown={timeline.confidenceBreakdown} />
      </div>

      <footer className="flex flex-1 flex-col px-5 py-4">
        <h4 className="mb-3 text-xs font-semibold tracking-wide text-gray-500 uppercase">
          Milestones
        </h4>
        <ol className="relative border-l border-gray-200">
          {timeline.milestones.map((milestone) => (
            <MilestoneRow key={`${milestone.month}-${milestone.event}`} milestone={milestone} />
          ))}
        </ol>
      </footer>
    </article>
  );
}
