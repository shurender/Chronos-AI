import { TriangleAlert } from 'lucide-react';

export interface GapWarningBadgeProps {
  readonly className?: string;
  readonly label?: string;
}

export function GapWarningBadge({
  className = '',
  label = 'Data Gap',
}: GapWarningBadgeProps) {
  return (
    <span
      role="status"
      aria-label={label}
      className={[
        'inline-flex items-center gap-1 rounded-full border border-dashed',
        'border-amber-400 bg-amber-50 px-2 py-0.5',
        'text-xs font-medium leading-none text-amber-800 whitespace-nowrap',
        className,
      ].join(' ')}
    >
      <TriangleAlert className="size-3 shrink-0" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}
