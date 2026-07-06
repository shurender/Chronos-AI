import { GitBranch, Loader2, MessageSquare, FileText, Hash} from 'lucide-react';

import { FutureSelfChat } from './components/chat/FutureSelfChat';
import { MemoryGraphView } from './components/graph/MemoryGraphView';
import { StepProgressBar } from './components/layout/StepProgressBar';
import { TimelineCard } from './components/timeline/TimelineCard';
import { useChronosStore } from './store/useChronosStore';

// ── Ambient background with radial glows ─────────────────────────────────────
function AmbientBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden="true">
      <div className="absolute top-[-20%] left-[5%]  w-[700px] h-[700px] rounded-full bg-indigo-900/20 blur-[130px]" />
      <div className="absolute bottom-[-15%] right-[0%] w-[550px] h-[550px] rounded-full bg-violet-900/15 blur-[110px]" />
      <div className="absolute top-[40%] right-[20%]  w-[350px] h-[350px] rounded-full bg-indigo-800/10 blur-[90px]" />
    </div>
  );
}

// ── Step 1: Connect Data ──────────────────────────────────────────────────────
function ConnectDataView() {
  const setStep = useChronosStore((state) => state.setStep);

  const sources = [
    { icon: GitBranch,    label: 'GitHub',   sub: 'Commits & issues'  },
    { icon: Hash,        label: 'Hash',    sub: 'Threads & channels' },
    { icon: FileText,     label: 'Notion',   sub: 'Docs & pages'       },
    { icon: MessageSquare,label: 'PDFs',     sub: 'Resumes & reports'  },
  ] as const;

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-lg rounded-2xl border border-white/[0.09] bg-white/[0.04] p-8 text-center shadow-2xl shadow-black/40 backdrop-blur-xl">
        <h1 className="text-2xl font-bold tracking-tight text-white">
          Connect Your Data Sources
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-400">
          Chronos ingests your decision history from code commits, team
          conversations, and documents to build a living memory graph.
        </p>

        <div className="mt-6 grid grid-cols-2 gap-3">
          {sources.map(({ icon: Icon, label, sub }) => (
            <div
              key={label}
              className="flex flex-col items-center gap-2 rounded-xl border border-white/[0.07] bg-white/[0.04] px-4 py-4 text-center"
            >
              <Icon className="size-5 text-indigo-400" aria-hidden="true" />
              <span className="text-xs font-semibold text-slate-200">{label}</span>
              <span className="text-[11px] text-slate-500">{sub}</span>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={() => setStep(2)}
          className="mt-6 inline-flex w-full items-center justify-center gap-2.5 rounded-xl
            bg-gradient-to-r from-indigo-600 to-violet-600
            hover:from-indigo-500 hover:to-violet-500
            px-6 py-3.5 text-sm font-semibold text-white
            shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/45
            transition-all duration-200"
        >
          <GitBranch className="size-4" aria-hidden="true" />
          Connect GitHub &amp; Slack
        </button>
      </div>
    </div>
  );
}

// ── Step 2: Define Decision ───────────────────────────────────────────────────
function DefineDecisionView() {
  const decisionQuestion = useChronosStore((state) => state.decisionQuestion);
  const setDecisionQuestion = useChronosStore((state) => state.setDecisionQuestion);
  const runSimulation = useChronosStore((state) => state.runSimulation);
  const isLoading = useChronosStore((state) => state.isLoading);

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-2xl rounded-2xl border border-white/[0.09] bg-white/[0.04] p-8 shadow-2xl shadow-black/40 backdrop-blur-xl">
        <h1 className="text-2xl font-bold tracking-tight text-white">
          Define Your Decision
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          What strategic fork are you standing at? Chronos will simulate plausible
          futures from your memory graph.
        </p>

        <label htmlFor="decision-question" className="sr-only">
          What decision are you facing?
        </label>
        <textarea
          id="decision-question"
          value={decisionQuestion}
          onChange={(e) => setDecisionQuestion(e.target.value)}
          placeholder="What decision are you facing?"
          rows={6}
          disabled={isLoading}
          className="mt-6 w-full resize-none rounded-xl border border-white/[0.09]
            bg-white/[0.04] px-4 py-3 text-sm text-slate-100
            placeholder:text-slate-600
            focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none
            disabled:opacity-50 transition-all duration-200"
        />

        <button
          type="button"
          onClick={() => void runSimulation()}
          disabled={isLoading || decisionQuestion.trim().length === 0}
          className="mt-4 inline-flex w-full items-center justify-center rounded-xl
            bg-gradient-to-r from-indigo-600 to-violet-600
            hover:from-indigo-500 hover:to-violet-500
            px-6 py-3.5 text-sm font-semibold text-white
            shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/45
            disabled:cursor-not-allowed disabled:opacity-35
            transition-all duration-200"
        >
          Run Simulation
        </button>
      </div>
    </div>
  );
}

// ── Step 3: Simulate Futures ──────────────────────────────────────────────────
function SimulateFuturesView() {
  const simulationData = useChronosStore((state) => state.simulationData);
  const setStep = useChronosStore((state) => state.setStep);

  if (!simulationData) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-slate-500">
        No simulation data available. Run a simulation from Step 2.
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* Sub-header */}
      <div className="flex shrink-0 items-center justify-between border-b border-white/[0.07]
        bg-[#0d1020]/80 backdrop-blur-md px-5 py-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-100">Simulated Futures</h2>
          <p className="text-xs text-slate-500">
            {simulationData.timelines.length} branches · memory graph + timeline comparison
          </p>
        </div>
        <button
          type="button"
          onClick={() => setStep(4)}
          className="inline-flex items-center gap-2 rounded-lg
            bg-gradient-to-r from-indigo-600 to-violet-600
            hover:from-indigo-500 hover:to-violet-500
            px-4 py-2 text-sm font-medium text-white
            shadow-md shadow-indigo-500/25
            transition-all duration-200"
        >
          <MessageSquare className="size-4" aria-hidden="true" />
          Talk to Future Self
        </button>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* Memory Graph panel */}
        <section className="flex w-[40%] min-w-0 flex-col border-r border-white/[0.06] bg-[#0a0d1a]">
          <div className="shrink-0 border-b border-white/[0.05] px-4 py-2">
            <h3 className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
              Memory Graph
            </h3>
          </div>
          <div className="min-h-0 flex-1">
            <MemoryGraphView />
          </div>
        </section>

        {/* Timeline Branches panel */}
        <section className="flex w-[60%] min-w-0 flex-col bg-[#080b14]">
          <div className="shrink-0 border-b border-white/[0.05] px-4 py-2">
            <h3 className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
              Timeline Branches
            </h3>
          </div>
          <div className="flex min-h-0 flex-1 gap-4 overflow-x-auto p-4">
            {simulationData.timelines.map((timeline) => (
              <TimelineCard key={timeline.id} timeline={timeline} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

// ── Step 4: Explore ───────────────────────────────────────────────────────────
function ExploreChatView() {
  return (
    <div className="min-h-0 flex-1">
      <FutureSelfChat />
    </div>
  );
}

// ── Loading overlay ───────────────────────────────────────────────────────────
function LoadingOverlay() {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-5 rounded-2xl
        border border-indigo-500/20 bg-[#0d1020]
        px-12 py-10 shadow-2xl shadow-indigo-500/10">
        {/* Animated ring */}
        <div className="relative flex items-center justify-center">
          <div className="size-14 rounded-full border-2 border-indigo-500/20" />
          <Loader2
            className="absolute size-10 animate-spin text-indigo-400"
            aria-hidden="true"
          />
        </div>
        <div className="flex flex-col items-center gap-1">
          <p className="text-sm font-medium text-slate-200">
            Simulating plausible futures
          </p>
          <p className="text-xs text-slate-500">
            Multi-agent simulation running on AMD GPU…
          </p>
        </div>
        {/* Progress dots */}
        <div className="flex gap-1.5">
          {[0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="size-1.5 rounded-full bg-indigo-500/60"
              style={{ animation: `bounce-dot 1.4s ease-in-out ${i * 0.15}s infinite` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Root ──────────────────────────────────────────────────────────────────────
function App() {
  const currentStep = useChronosStore((state) => state.currentStep);
  const isLoading = useChronosStore((state) => state.isLoading);

  return (
    <div className="relative flex h-screen flex-col bg-[#080b14] text-white overflow-hidden">
      <AmbientBackground />

      {/* Header */}
      <header className="relative z-10 shrink-0">
        <div className="border-b border-white/[0.07] bg-[#0d1020]/90 backdrop-blur-md px-6 py-4">
          <h1 className="text-lg font-bold bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent leading-none">
            Chronos Engine
          </h1>
          <p className="mt-0.5 text-xs text-slate-500">
            AI Decision Intelligence · FlowState B2B Pivot Demo
          </p>
        </div>
        <StepProgressBar />
      </header>

      <main className="relative z-10 flex min-h-0 flex-1 flex-col overflow-hidden">
        {currentStep === 1 && <ConnectDataView />}
        {currentStep === 2 && <DefineDecisionView />}
        {currentStep === 3 && <SimulateFuturesView />}
        {currentStep === 4 && <ExploreChatView />}
      </main>

      {isLoading && <LoadingOverlay />}
    </div>
  );
}

export default App;