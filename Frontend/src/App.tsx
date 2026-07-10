import { ChevronDown, GitBranch, Loader2, MessageSquare, FileText, Hash} from 'lucide-react';
import { useState } from 'react';
import { FutureSelfChat } from './components/chat/FutureSelfChat';
import { MemoryGraphView } from './components/graph/MemoryGraphView';
import { StepProgressBar } from './components/layout/StepProgressBar';
import { TimelineCard } from './components/timeline/TimelineCard';
import { useChronosStore } from './store/useChronosStore';
import { LandingPage } from './components/layout/LandingPage';
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
const FIELD_CLASS =
  'mt-1 w-full rounded-lg border border-white/[0.09] bg-white/[0.04] px-3 py-2 text-sm text-slate-100 ' +
  'placeholder:text-slate-600 focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none ' +
  'disabled:opacity-50 transition-all duration-200';
const LABEL_CLASS = 'text-xs font-medium text-slate-500';

function DefineDecisionView() {
  const decisionQuestion = useChronosStore((state) => state.decisionQuestion);
  const setDecisionQuestion = useChronosStore((state) => state.setDecisionQuestion);
  const decisionType = useChronosStore((state) => state.decisionType);
  const setDecisionType = useChronosStore((state) => state.setDecisionType);
  const horizon = useChronosStore((state) => state.horizon);
  const setHorizon = useChronosStore((state) => state.setHorizon);
  const risk = useChronosStore((state) => state.risk);
  const setRisk = useChronosStore((state) => state.setRisk);
  const goal = useChronosStore((state) => state.goal);
  const setGoal = useChronosStore((state) => state.setGoal);
  const constraints = useChronosStore((state) => state.constraints);
  const setConstraints = useChronosStore((state) => state.setConstraints);
  const geography = useChronosStore((state) => state.geography);
  const setGeography = useChronosStore((state) => state.setGeography);
  const optionA = useChronosStore((state) => state.optionA);
  const setOptionA = useChronosStore((state) => state.setOptionA);
  const optionB = useChronosStore((state) => state.optionB);
  const setOptionB = useChronosStore((state) => state.setOptionB);
  const optionC = useChronosStore((state) => state.optionC);
  const setOptionC = useChronosStore((state) => state.setOptionC);
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

        <p className="mt-4 text-xs text-slate-500">
          These details reduce uncertainty in the simulation.
        </p>

        <div className="mt-3 grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="decision-type" className={LABEL_CLASS}>Decision type</label>
            <select
              id="decision-type"
              value={decisionType}
              onChange={(e) => setDecisionType(e.target.value as typeof decisionType)}
              disabled={isLoading}
              className={FIELD_CLASS}
            >
              <option value="Career">Career</option>
              <option value="Startup">Startup</option>
              <option value="Financial">Financial</option>
              <option value="Life">Life</option>
              <option value="Relocation">Relocation</option>
            </select>
          </div>
          <div>
            <label htmlFor="horizon" className={LABEL_CLASS}>Horizon</label>
            <select
              id="horizon"
              value={horizon}
              onChange={(e) => setHorizon(e.target.value as typeof horizon)}
              disabled={isLoading}
              className={FIELD_CLASS}
            >
              <option value="1 year">1 year</option>
              <option value="3 years">3 years</option>
              <option value="5 years">5 years</option>
              <option value="10 years">10 years</option>
            </select>
          </div>
        </div>

        <div className="mt-3">
          <label htmlFor="risk" className={`${LABEL_CLASS} flex items-center justify-between`}>
            <span>Risk tolerance</span>
            <span className="text-slate-400">{risk}</span>
          </label>
          <input
            id="risk"
            type="range"
            min={0}
            max={100}
            value={risk}
            onChange={(e) => setRisk(Number(e.target.value))}
            disabled={isLoading}
            className="mt-1 w-full accent-indigo-500 disabled:opacity-50"
          />
        </div>

        <div className="mt-3">
          <label htmlFor="goal" className={LABEL_CLASS}>Goal</label>
          <input
            id="goal"
            type="text"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="What does success look like?"
            disabled={isLoading}
            className={FIELD_CLASS}
          />
        </div>

        <div className="mt-3 grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="constraints" className={LABEL_CLASS}>Constraints</label>
            <input
              id="constraints"
              type="text"
              value={constraints}
              onChange={(e) => setConstraints(e.target.value)}
              placeholder="e.g. limited runway"
              disabled={isLoading}
              className={FIELD_CLASS}
            />
          </div>
          <div>
            <label htmlFor="geography" className={LABEL_CLASS}>Geography / context</label>
            <input
              id="geography"
              type="text"
              value={geography}
              onChange={(e) => setGeography(e.target.value)}
              placeholder="e.g. remote, US-based"
              disabled={isLoading}
              className={FIELD_CLASS}
            />
          </div>
        </div>

        <div className="mt-3 grid grid-cols-3 gap-3">
          <div>
            <label htmlFor="option-a" className={LABEL_CLASS}>Option A</label>
            <input
              id="option-a"
              type="text"
              value={optionA}
              onChange={(e) => setOptionA(e.target.value)}
              disabled={isLoading}
              className={FIELD_CLASS}
            />
          </div>
          <div>
            <label htmlFor="option-b" className={LABEL_CLASS}>Option B</label>
            <input
              id="option-b"
              type="text"
              value={optionB}
              onChange={(e) => setOptionB(e.target.value)}
              disabled={isLoading}
              className={FIELD_CLASS}
            />
          </div>
          <div>
            <label htmlFor="option-c" className={LABEL_CLASS}>Option C (optional)</label>
            <input
              id="option-c"
              type="text"
              value={optionC}
              onChange={(e) => setOptionC(e.target.value)}
              disabled={isLoading}
              className={FIELD_CLASS}
            />
          </div>
        </div>

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

// ── Historical Precedent Panel ────────────────────────────────────────────────
function HistoricalPrecedentsPanel() {
  const historicalPrecedents = useChronosStore((state) => state.historicalPrecedents);
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="shrink-0 border-b border-white/[0.07] bg-[#0d1020]/60 px-8 py-3">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between text-left"
      >
        <span className="text-xs font-semibold tracking-wide text-slate-300 uppercase">
          Historical Precedents
        </span>
        <ChevronDown
          className={`size-4 text-slate-500 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      {expanded && (
        historicalPrecedents.length === 0 ? (
          <p className="mt-2 text-xs text-amber-400/80">
            No strong historical precedent found. Simulation confidence reduced.
          </p>
        ) : (
          <ul className="mt-2 flex gap-3 overflow-x-auto pb-1">
            {historicalPrecedents.map((p) => (
              <li
                key={p.chunk_id}
                className="w-72 shrink-0 rounded-lg border border-white/[0.07] bg-white/[0.03] p-3"
              >
                <p className="text-xs leading-snug text-slate-300">{p.snippet}</p>
                <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-500">
                  {p.source_type && <span>{p.source_type}</span>}
                  {p.project && <span>{p.project}</span>}
                  {p.timestamp && <span>{p.timestamp}</span>}
                  <span>grounding {Math.round(Math.max(0, 1 - p.distance) * 100)}%</span>
                </div>
              </li>
            ))}
          </ul>
        )
      )}
    </div>
  );
}

// ── External Evidence Panel (Demo Evidence Pack) ──────────────────────────────
function ExternalEvidencePanel() {
  const externalEvidence = useChronosStore((state) => state.externalEvidence);
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="shrink-0 border-b border-white/[0.07] bg-[#0d1020]/60 px-8 py-3">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between text-left"
      >
        <span className="flex items-center gap-2">
          <span className="text-xs font-semibold tracking-wide text-slate-300 uppercase">
            External Evidence
          </span>
          <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-300/90">
            Demo Evidence Pack
          </span>
        </span>
        <ChevronDown
          className={`size-4 text-slate-500 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      {expanded && (
        externalEvidence.length === 0 ? (
          <p className="mt-2 text-xs text-slate-500">
            No external evidence attached to this simulation.
          </p>
        ) : (
          <ul className="mt-2 flex gap-3 overflow-x-auto pb-1">
            {externalEvidence.map((e) => (
              <li
                key={e.id}
                className="w-80 shrink-0 rounded-lg border border-white/[0.07] bg-white/[0.03] p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-xs font-semibold leading-snug text-slate-200">{e.title}</p>
                  <span className="shrink-0 rounded-full bg-indigo-500/15 px-2 py-0.5 text-[10px] font-medium text-indigo-300">
                    {Math.round(e.confidence * 100)}%
                  </span>
                </div>
                <p className="mt-1.5 text-[11px] leading-snug text-slate-400">{e.summary}</p>
                <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-500">
                  <span>{e.evidence_type.replace(/_/g, ' ')}</span>
                  <span>{e.source_name}</span>
                  {e.published_at && <span>{e.published_at}</span>}
                </div>
              </li>
            ))}
          </ul>
        )
      )}
    </div>
  );
}

// ── Agent Council Panel ───────────────────────────────────────────────────────
function AgentCouncilPanel() {
  const agentCouncil = useChronosStore((state) => state.agentCouncil);
  const [expanded, setExpanded] = useState(true);

  if (!agentCouncil) return null;

  return (
    <div className="shrink-0 border-b border-white/[0.07] bg-[#0d1020]/60 px-8 py-3">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between text-left"
      >
        <span className="flex items-center gap-2">
          <span className="text-xs font-semibold tracking-wide text-slate-300 uppercase">
            Agent Council
          </span>
          <span className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 text-[10px] font-medium text-indigo-300">
            Consensus {Math.round(agentCouncil.consensusScore * 100)}%
          </span>
        </span>
        <ChevronDown
          className={`size-4 text-slate-500 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      {expanded && (
        <ul className="mt-2 flex gap-3 overflow-x-auto pb-1">
          {agentCouncil.agents.map((a) => (
            <li
              key={a.agent_id}
              className="w-72 shrink-0 rounded-lg border border-white/[0.07] bg-white/[0.03] p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs font-semibold text-slate-200">{a.agent_label}</span>
                <span className="shrink-0 rounded-full bg-indigo-500/15 px-2 py-0.5 text-[10px] font-medium text-indigo-300">
                  {Math.round(a.confidence * 100)}%
                </span>
              </div>
              <p className="mt-1.5 text-[11px] leading-snug text-slate-400">{a.position}</p>
              {a.concerns.length > 0 && (
                <p className="mt-1.5 text-[11px] leading-snug text-amber-400/80">
                  ⚠ {a.concerns[0]}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Step 3: Simulate Futures ──────────────────────────────────────────────────
// ── Step 3: Simulate Futures (TABBED VIEW) ────────────────────────────────────
function SimulateFuturesView() {
  const simulationData = useChronosStore((state) => state.simulationData);
  const setStep = useChronosStore((state) => state.setStep);
  
  // Create state for our tabs
  const [activeTab, setActiveTab] = useState<'timelines' | 'graph'>('timelines');

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
        <div className="w-1/3">
          <h2 className="text-sm font-semibold text-slate-100">Simulated Futures</h2>
          <p className="text-xs text-slate-500">
            {simulationData.timelines.length} evidence-backed plausible timelines
          </p>
          <p className="mt-0.5 text-[10px] italic text-slate-600">
            Chronos explores plausible futures from available evidence. It does not predict the future.
          </p>
        </div>

        {/* --- SLEEK TAB SWITCHER --- */}
        <div className="flex bg-black/40 p-1 rounded-lg border border-white/10 w-fit">
          <button 
            onClick={() => setActiveTab('timelines')}
            className={`px-6 py-1.5 text-xs font-medium rounded-md transition-all duration-300 ${
              activeTab === 'timelines' 
              ? 'bg-indigo-500/20 text-indigo-300 shadow-sm' 
              : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Timeline Branches
          </button>
          <button 
            onClick={() => setActiveTab('graph')}
            className={`px-6 py-1.5 text-xs font-medium rounded-md transition-all duration-300 ${
              activeTab === 'graph' 
              ? 'bg-indigo-500/20 text-indigo-300 shadow-sm' 
              : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Memory Graph
          </button>
        </div>
        {/* ------------------------ */}

        <div className="w-1/3 flex justify-end">
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
      </div>

      {/* Main Content Area (Absolute positioning allows smooth cross-fading if you add animations) */}
      <div className="flex min-h-0 flex-1 relative overflow-hidden">
        
        {/* Timeline Branches panel */}
        {activeTab === 'timelines' && (
          <section className="absolute inset-0 flex flex-col bg-[#080b14] animate-in fade-in duration-300">
            <HistoricalPrecedentsPanel />
            <ExternalEvidencePanel />
            <AgentCouncilPanel />
            <div className="flex min-h-0 flex-1 gap-6 overflow-x-auto p-8 items-start">
              {simulationData.timelines.map((timeline) => (
                <TimelineCard key={timeline.id} timeline={timeline} className="h-[90%]" />
              ))}
            </div>
          </section>
        )}

        {/* Memory Graph panel */}
        {activeTab === 'graph' && (
          <section className="absolute inset-0 flex flex-col bg-[#0a0d1a] animate-in fade-in duration-300">
            <div className="min-h-0 flex-1">
              <MemoryGraphView />
            </div>
          </section>
        )}

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
            Building evidence-backed scenario branches…
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
// ── Root ──────────────────────────────────────────────────────────────────────
function App() {
  const currentStep = useChronosStore((state) => state.currentStep);
  const isLoading = useChronosStore((state) => state.isLoading);

  return (
    <div className="relative flex h-screen flex-col bg-[#080b14] text-white overflow-hidden">
      <AmbientBackground />

      {/* Conditionally render header ONLY if we are past the landing page (Step 0) */}
      {currentStep > 0 && (
        <header className="relative z-10 shrink-0 animate-in fade-in slide-in-from-top-4 duration-500">
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
      )}

      <main className="relative z-10 flex min-h-0 flex-1 flex-col overflow-hidden">
        {currentStep === 0 && <LandingPage />}
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
