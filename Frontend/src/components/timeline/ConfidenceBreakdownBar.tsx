import type { ConfidenceBreakdown } from '../../types/timeline';

interface BreakdownFactor {
  readonly key: keyof ConfidenceBreakdown;
  readonly label: string;
}

const BREAKDOWN_FACTORS: readonly BreakdownFactor[] = [
  { key: 'evidenceStrength', label: 'Evidence' },
  { key: 'sourceReliability', label: 'Sources' },
  { key: 'modelConsensus', label: 'Consensus' },
  { key: 'temporalRelevance', label: 'Temporal' },
  { key: 'causalCoherence', label: 'Causal' },
];

export interface ConfidenceBreakdownBarProps {
  readonly breakdown: ConfidenceBreakdown;
  readonly className?: string;
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function ConfidenceBreakdownBar({
  breakdown,
  className = '',
}: ConfidenceBreakdownBarProps) {
  return (
    <div className={['flex flex-col gap-2.5', className].join(' ')}>
      {BREAKDOWN_FACTORS.map(({ key, label }) => {
        const value = breakdown[key];

        return (
          <div key={key} className="flex flex-col gap-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-gray-600">{label}</span>
              <span className="tabular-nums text-gray-500">
                {formatPercent(value)}
              </span>
            </div>
            <div
              className="h-2 w-full overflow-hidden rounded-full bg-gray-100"
              role="progressbar"
              aria-valuenow={Math.round(value * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${label}: ${formatPercent(value)}`}
            >
              <div
                className="h-full rounded-full bg-indigo-500 transition-[width] duration-300"
                style={{ width: `${value * 100}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
