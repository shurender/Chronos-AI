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

function StepNode({ step, status, clickable, onNavigate }: { step: StepConfig, status: StepStatus, clickable: boolean, onNavigate: (id: number) => void }) {
  const Icon = step.icon;

  const circleClassMap: Record<StepStatus, string> = {
    completed: 'border-gray-900 bg-gray-900 text-white shadow-sm',
    current:   'border-gray-900 bg-white text-gray-900 ring-4 ring-gray-100 shadow-md',
    future:    'border-gray-200 bg-gray-50 text-gray-400',
  };

  const labelClassMap: Record<StepStatus, string> = {
    completed: 'text-gray-900 font-semibold',
    current:   'text-gray-900 font-bold',
    future:    'text-gray-400 font-medium',
  };

  const content = (
    <>
      <span className={['flex size-10 items-center justify-center rounded-full border-2 transition-all duration-300', circleClassMap[status]].join(' ')}>
        <Icon className="size-4" aria-hidden="true" />
      </span>
      <span className={['mt-2 hidden text-center text-xs tracking-wide sm:block transition-all duration-200', labelClassMap[status]].join(' ')}>
        {step.label}
      </span>
    </>
  );

  if (!clickable) return <div className="relative z-10 flex flex-col items-center">{content}</div>;

  return (
    <button onClick={() => onNavigate(step.id)} className="group relative z-10 flex flex-col items-center rounded-lg p-1 transition-opacity hover:opacity-80 focus:outline-none">
      {content}
    </button>
  );
}

export function StepProgressBar() {
  const currentStep = useChronosStore((state) => state.currentStep);
  const setStep = useChronosStore((state) => state.setStep);

  return (
    <nav className="w-full border-b border-gray-200 bg-white/90 backdrop-blur-md px-6 py-5">
      <ol className="mx-auto flex max-w-4xl items-start">
        {STEPS.map((step, index) => {
          const status = getStepStatus(step.id, currentStep);
          return (
            <li key={step.id} className="flex flex-1 items-start last:flex-none">
              <StepNode step={step} status={status} clickable={step.id < currentStep} onNavigate={setStep} />
              {index < STEPS.length - 1 && (
                <div className="mx-2 h-0.5 flex-1 self-start mt-5">
                  <div className={['h-full w-full rounded-full transition-all duration-500', step.id < currentStep ? 'bg-gray-900' : 'bg-gray-100'].join(' ')} />
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}