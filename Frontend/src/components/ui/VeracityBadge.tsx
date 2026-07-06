import {
  CheckCircle2,
  Lightbulb,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';

import type { VeracityType } from '../../types/graph';

interface VeracityStyle {
  readonly bg: string;
  readonly text: string;
  readonly border: string;
  readonly icon: LucideIcon;
  readonly label: string;
}

const VERACITY_CONFIG: Record<VeracityType, VeracityStyle> = {
  fact: {
    bg: 'bg-blue-100',
    text: 'text-blue-700',
    border: 'border-blue-300',
    icon: CheckCircle2,
    label: 'Fact',
  },
  inference: {
    bg: 'bg-amber-100',
    text: 'text-amber-700',
    border: 'border-amber-300',
    icon: Lightbulb,
    label: 'Inference',
  },
  prediction: {
    bg: 'bg-purple-100',
    text: 'text-purple-700',
    border: 'border-purple-300',
    icon: Sparkles,
    label: 'Prediction',
  },
};

export interface VeracityBadgeProps {
  readonly type: VeracityType;
  readonly className?: string;
}

export function VeracityBadge({ type, className = '' }: VeracityBadgeProps) {
  const { bg, text, border, icon: Icon, label } = VERACITY_CONFIG[type];

  return (
    <span
      role="status"
      aria-label={`Veracity: ${label}`}
      className={[
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5',
        'text-xs font-medium leading-none whitespace-nowrap',
        bg,
        text,
        border,
        className,
      ].join(' ')}
    >
      <Icon className="size-3 shrink-0" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}
