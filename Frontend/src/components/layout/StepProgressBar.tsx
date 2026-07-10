import { Cpu, Database, MessageSquare, Target, type LucideIcon } from 'lucide-react';

import { useChronosStore } from '../../store/useChronosStore';

interface StepConfig {
  readonly id: number;
  readonly label: string;
  readonly icon: LucideIcon;
}

const STEPS: readonly StepConfig[] = [
  { id: 1, label: 'Connect Data',    icon: Database      },
  { id: 2, label: 'Define Decision', icon: Target        },
  { id: 3, label: 'Simulate Futures',icon: Cpu           },
  { id: 4, label: 'Explore',         icon: MessageSquare },
];

type StepStatus = 'completed' | 'current' | 'future';

function getStepStatus(stepId: number, currentStep: number): StepStatus {
  if (stepId < currentStep) return 'completed';
  if (stepId === currentStep) return 'current';
  return 'future';
}

function isStepClickable(stepId: number, currentStep: number): boolean {
  return stepId < currentStep;
}

interface StepNodeProps {
  readonly step: StepConfig;
  readonly status: StepStatus;
  readonly clickable: boolean;
  readonly onNavigate: (stepId: number) => void;
}

function StepNode({ step, status, clickable, onNavigate }: StepNodeProps) {
  const Icon = step.icon;

  const circleClassMap: Record<StepStatus, string> = {
    completed: [
      'border-indigo-500 bg-indigo-600 text-white',
      'shadow-md shadow-indigo-500/40',
    ].join(' '),
    current: [
      'border-indigo-400 bg-[#0d1020] text-indigo-400',
      'ring-4 ring-indigo-500/20',
      'shadow-lg shadow-indigo-500/40',
    ].join(' '),
    future: 'border-white/10 bg-white/[0.04] text-slate-600',
  };
  const circleClass = circleClassMap[status];

  const labelClassMap: Record<StepStatus, string> = {
    completed: 'bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent font-semibold',
    current:   'bg-gradient-to-r from-indigo-300 to-violet-300 bg-clip-text text-transparent font-bold',
    future:    'text-slate-600 font-medium',
  };
  const labelClass = labelClassMap[status];

  const content = (
    <>
      <span
        className={[
          'flex size-10 items-center justify-center rounded-full border-2 transition-all duration-300',
          circleClass,
        ].join(' ')}
      >
        <Icon className="size-4" aria-hidden="true" />
      </span>
      <span
        className={[
          'mt-2 hidden text-center text-xs tracking-wide sm:block transition-all duration-200',
          labelClass,
        ].join(' ')}
      >
        {step.label}
      </span>
      <span className="mt-2 text-center text-[10px] font-medium text-slate-600 sm:hidden">
        {step.id}
      </span>
    </>
  );

  if (!clickable) {
    return (
      <div
        className="relative z-10 flex flex-col items-center"
        aria-current={status === 'current' ? 'step' : undefined}
        aria-disabled={status === 'future'}
      >
        {content}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onNavigate(step.id)}
      className="group relative z-10 flex flex-col items-center rounded-lg p-1 transition-opacity hover:opacity-90
        focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-[#0d1020] focus:outline-none"
      aria-label={`Go back to step ${step.id}: ${step.label}`}
    >
      {content}
    </button>
  );
}

interface ConnectorProps {
  readonly completed: boolean;
}

function Connector({ completed }: ConnectorProps) {
  return (
    <div className="mx-2 h-0.5 flex-1 self-start mt-5" aria-hidden="true">
      <div
        className={[
          'h-full w-full rounded-full transition-all duration-500',
          completed
            ? 'bg-gradient-to-r from-indigo-500 to-violet-500/60'
            : 'bg-white/[0.06]',
        ].join(' ')}
      />
    </div>
  );
}

export function StepProgressBar() {
  const currentStep = useChronosStore((state) => state.currentStep);
  const setStep = useChronosStore((state) => state.setStep);

  return (
    <nav
      aria-label="Chronos Engine workflow progress"
      className="w-full border-b border-white/[0.07] bg-[#0d1020]/80 backdrop-blur-md px-6 py-5"
    >
      <ol className="mx-auto flex max-w-4xl items-start">
        {STEPS.map((step, index) => {
          const status = getStepStatus(step.id, currentStep);
          const clickable = isStepClickable(step.id, currentStep);
          const connectorCompleted = step.id < currentStep;

          return (
            <li key={step.id} className="flex flex-1 items-start last:flex-none">
              <StepNode
                step={step}
                status={status}
                clickable={clickable}
                onNavigate={setStep}
              />
              {index < STEPS.length - 1 && (
                <Connector completed={connectorCompleted} />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}