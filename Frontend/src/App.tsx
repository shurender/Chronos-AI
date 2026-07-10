import { ChevronDown, Loader2, MessageSquare, FileText } from 'lucide-react';
import { useState, useEffect } from 'react';
import { FutureSelfChat } from './components/chat/FutureSelfChat';
import { MemoryGraphView } from './components/graph/MemoryGraphView';
import { StepProgressBar } from './components/layout/StepProgressBar';
import { TimelineCard } from './components/timeline/TimelineCard';
import { useChronosStore } from './store/useChronosStore';
import { LandingPage } from './components/layout/LandingPage';

// Custom Minimal SVGs for Logos
const NotionIcon = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M4 4v16h16V4H4z" />
    <path d="M8 8v8l8-8v8" />
  </svg>
);

const SlackIcon = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M14 3v18M10 3v18M3 14h18M3 10h18" />
  </svg>
);
const GithubIcon = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
  </svg>
);
// ── Step 1: Connect Data ──────────────────────────────────────────────────────
function ConnectDataView() {
  const setStep = useChronosStore((state) => state.setStep);
  const sources = [
    { icon: GithubIcon,       label: 'GitHub',   sub: 'Commits & issues'  },
    { icon: SlackIcon,    label: 'Slack',    sub: 'Threads & channels' },
    { icon: NotionIcon,   label: 'Notion',   sub: 'Docs & pages'       },
    { icon: FileText,     label: 'PDFs',     sub: 'Resumes & reports'  },
  ] as const;

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 bg-white">
      <div className="w-full max-w-2xl rounded-2xl border border-gray-200 bg-white p-10 text-center shadow-xl">
        <h1 className="text-3xl font-serif tracking-tight text-gray-900">
          Connect Your Data Sources
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-gray-500 max-w-lg mx-auto">
          Chronos ingests your decision history from code commits, team
          conversations, and documents to build a living memory graph.
        </p>

        {/* Group wrapper for hover dimming effect */}
        <div className="mt-10 grid grid-cols-2 gap-4 group">
          {sources.map(({ icon: Icon, label, sub }) => (
            <div
              key={label}
              className="flex flex-col items-center gap-3 rounded-xl border border-gray-100 bg-gray-50 px-6 py-6 text-center transition-all duration-500 group-hover:opacity-30 hover:!opacity-100 hover:scale-105 cursor-pointer hover:border-gray-300 hover:bg-white hover:shadow-md"
            >
              <Icon className="size-7 text-gray-800" />
              <div>
                <span className="block text-sm font-semibold text-gray-900">{label}</span>
                <span className="block mt-0.5 text-[11px] text-gray-500">{sub}</span>
              </div>
            </div>
          ))}
        </div>

        <button
          onClick={() => setStep(2)}
          className="mt-10 inline-flex w-full items-center justify-center gap-2.5 rounded-xl border border-gray-900 bg-gray-900 px-6 py-4 text-sm font-semibold text-white transition-all duration-200 hover:bg-gray-800"
        >
          <GithubIcon className="size-4" aria-hidden="true" />
          Connect GitHub &amp; Slack
        </button>
      </div>
    </div>
  );
}

// ── Step 2: Define Decision ───────────────────────────────────────────────────
const FIELD_CLASS =
  'mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 ' +
  'placeholder:text-gray-400 focus:border-gray-900 focus:ring-1 focus:ring-gray-900 focus:outline-none ' +
  'disabled:opacity-50 transition-all duration-200';
const LABEL_CLASS = 'text-xs font-medium text-gray-600 uppercase tracking-wide';

function DefineDecisionView() {
  const { decisionQuestion, setDecisionQuestion, decisionType, setDecisionType, horizon, setHorizon, risk, setRisk, goal, setGoal, constraints, setConstraints, geography, setGeography, optionA, setOptionA, optionB, setOptionB, optionC, setOptionC, runSimulation, isLoading } = useChronosStore();

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 bg-white">
      <div className="w-full max-w-2xl rounded-2xl border border-gray-200 bg-white p-8 shadow-xl">
        <h1 className="text-3xl font-serif tracking-tight text-gray-900">
          Define Your Decision
        </h1>
        <p className="mt-2 text-sm text-gray-500">
          What strategic fork are you standing at? Chronos will simulate plausible futures from your memory graph.
        </p>

        <textarea
          value={decisionQuestion}
          onChange={(e) => setDecisionQuestion(e.target.value)}
          placeholder="What decision are you facing?"
          rows={5}
          disabled={isLoading}
          className="mt-6 w-full resize-none rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-900 placeholder:text-gray-400 focus:border-gray-900 focus:ring-1 focus:ring-gray-900 focus:outline-none disabled:opacity-50 transition-all duration-200"
        />

        <div className="mt-6 grid grid-cols-2 gap-4">
          <div>
            <label className={LABEL_CLASS}>Decision type</label>
            <select value={decisionType} onChange={(e) => setDecisionType(e.target.value as any)} disabled={isLoading} className={FIELD_CLASS}>
              <option value="Career">Career</option>
              <option value="Startup">Startup</option>
              <option value="Financial">Financial</option>
              <option value="Life">Life</option>
              <option value="Relocation">Relocation</option>
            </select>
          </div>
          <div>
            <label className={LABEL_CLASS}>Horizon</label>
            <select value={horizon} onChange={(e) => setHorizon(e.target.value as any)} disabled={isLoading} className={FIELD_CLASS}>
              <option value="1 year">1 year</option>
              <option value="3 years">3 years</option>
              <option value="5 years">5 years</option>
              <option value="10 years">10 years</option>
            </select>
          </div>
        </div>

        <div className="mt-4">
          <label className={`${LABEL_CLASS} flex items-center justify-between`}>
            <span>Risk tolerance</span>
            <span className="text-gray-900">{risk}</span>
          </label>
          <input type="range" min={0} max={100} value={risk} onChange={(e) => setRisk(Number(e.target.value))} disabled={isLoading} className="mt-2 w-full accent-gray-900 disabled:opacity-50" />
        </div>

        <div className="mt-4">
          <label className={LABEL_CLASS}>Goal</label>
          <input type="text" value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="What does success look like?" disabled={isLoading} className={FIELD_CLASS} />
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div><label className={LABEL_CLASS}>Constraints</label><input type="text" value={constraints} onChange={(e) => setConstraints(e.target.value)} placeholder="e.g. limited runway" disabled={isLoading} className={FIELD_CLASS} /></div>
          <div><label className={LABEL_CLASS}>Geography / context</label><input type="text" value={geography} onChange={(e) => setGeography(e.target.value)} placeholder="e.g. remote, US-based" disabled={isLoading} className={FIELD_CLASS} /></div>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-3">
          <div><label className={LABEL_CLASS}>Option A</label><input type="text" value={optionA} onChange={(e) => setOptionA(e.target.value)} disabled={isLoading} className={FIELD_CLASS} /></div>
          <div><label className={LABEL_CLASS}>Option B</label><input type="text" value={optionB} onChange={(e) => setOptionB(e.target.value)} disabled={isLoading} className={FIELD_CLASS} /></div>
          <div><label className={LABEL_CLASS}>Option C (optional)</label><input type="text" value={optionC} onChange={(e) => setOptionC(e.target.value)} disabled={isLoading} className={FIELD_CLASS} /></div>
        </div>

        <button onClick={() => void runSimulation()} disabled={isLoading || decisionQuestion.trim().length === 0} className="mt-8 inline-flex w-full items-center justify-center rounded-xl bg-gray-900 px-6 py-3.5 text-sm font-semibold text-white shadow-md disabled:cursor-not-allowed disabled:opacity-35 transition-all hover:bg-gray-800">
          Run Simulation
        </button>
      </div>
    </div>
  );
}

// ── Panels ───────────────────────────────────────────────────────────────
function HistoricalPrecedentsPanel() {
  const historicalPrecedents = useChronosStore((state) => state.historicalPrecedents);
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="shrink-0 border-b border-gray-200 bg-white px-8 py-3">
      <button onClick={() => setExpanded((v) => !v)} className="flex w-full items-center justify-between text-left">
        <span className="text-xs font-semibold tracking-widest text-gray-600 uppercase">Historical Precedents</span>
        <ChevronDown className={`size-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>
      {expanded && (
        historicalPrecedents.length === 0 ? (
          <p className="mt-2 text-xs text-amber-600">No strong historical precedent found. Simulation confidence reduced.</p>
        ) : (
          <ul className="mt-3 flex gap-3 overflow-x-auto pb-2">
            {historicalPrecedents.map((p) => (
              <li key={p.chunk_id} className="w-72 shrink-0 rounded-lg border border-gray-200 bg-gray-50 p-4">
                <p className="text-xs leading-snug text-gray-800">{p.snippet}</p>
                <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-gray-500 font-mono">
                  {p.source_type && <span>{p.source_type}</span>}
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

function ExternalEvidencePanel() {
  const externalEvidence = useChronosStore((state) => state.externalEvidence);
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="shrink-0 border-b border-gray-200 bg-gray-50/50 px-8 py-3">
      <button onClick={() => setExpanded((v) => !v)} className="flex w-full items-center justify-between text-left">
        <span className="flex items-center gap-2">
          <span className="text-xs font-semibold tracking-widest text-gray-600 uppercase">External Evidence</span>
          <span className="rounded-full border border-gray-300 bg-white px-2 py-0.5 text-[10px] font-medium text-gray-600">Demo Pack</span>
        </span>
        <ChevronDown className={`size-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>
      {expanded && (
        externalEvidence.length === 0 ? (
          <p className="mt-2 text-xs text-gray-500">No external evidence attached.</p>
        ) : (
          <ul className="mt-3 flex gap-3 overflow-x-auto pb-2">
            {externalEvidence.map((e) => (
              <li key={e.id} className="w-80 shrink-0 rounded-lg border border-gray-200 bg-white p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-xs font-semibold leading-snug text-gray-900">{e.title}</p>
                  <span className="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-bold text-gray-600">{Math.round(e.confidence * 100)}%</span>
                </div>
                <p className="mt-2 text-[11px] leading-relaxed text-gray-600">{e.summary}</p>
              </li>
            ))}
          </ul>
        )
      )}
    </div>
  );
}

function AgentCouncilPanel() {
  const agentCouncil = useChronosStore((state) => state.agentCouncil);
  const [expanded, setExpanded] = useState(true);

  if (!agentCouncil) return null;

  return (
    <div className="shrink-0 border-b border-gray-200 bg-white px-8 py-3">
      <button onClick={() => setExpanded((v) => !v)} className="flex w-full items-center justify-between text-left">
        <span className="flex items-center gap-2">
          <span className="text-xs font-semibold tracking-widest text-gray-600 uppercase">Agent Council</span>
          <span className="rounded-full border border-gray-300 bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-800">Consensus {Math.round(agentCouncil.consensusScore * 100)}%</span>
        </span>
        <ChevronDown className={`size-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>
      {expanded && (
        <ul className="mt-3 flex gap-3 overflow-x-auto pb-2">
          {agentCouncil.agents.map((a) => (
            <li key={a.agent_id} className="w-72 shrink-0 rounded-lg border border-gray-200 bg-gray-50 p-4">
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs font-bold text-gray-900">{a.agent_label}</span>
              </div>
              <p className="mt-2 text-[11px] leading-relaxed text-gray-600">{a.position}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Step 3: Simulate Futures ──────────────────────────────────────────────────
function SimulateFuturesView() {
  const simulationData = useChronosStore((state) => state.simulationData);
  const setStep = useChronosStore((state) => state.setStep);
  const [activeTab, setActiveTab] = useState<'timelines' | 'graph'>('timelines');

  if (!simulationData) return <div className="flex flex-1 items-center justify-center text-sm text-gray-500 bg-gray-50">No data available. Run simulation from Step 2.</div>;

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-white">
      <div className="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white px-8 py-4">
        <div className="w-1/3">
          <h2 className="text-xl font-serif font-bold text-gray-900">Simulated Futures</h2>
          <p className="text-xs text-gray-500 mt-1">{simulationData.timelines.length} evidence-backed branches</p>
        </div>
        <div className="flex bg-gray-100 p-1 rounded-lg border border-gray-200">
          <button onClick={() => setActiveTab('timelines')} className={`px-6 py-1.5 text-xs font-semibold rounded-md transition-all ${activeTab === 'timelines' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}>Timeline Branches</button>
          <button onClick={() => setActiveTab('graph')} className={`px-6 py-1.5 text-xs font-semibold rounded-md transition-all ${activeTab === 'graph' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}>Memory Graph</button>
        </div>
        <div className="w-1/3 flex justify-end">
          <button onClick={() => setStep(4)} className="inline-flex items-center gap-2 rounded-lg bg-gray-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-gray-800">
            <MessageSquare className="size-4" /> Talk to Future Self
          </button>
        </div>
      </div>
      <div className="flex min-h-0 flex-1 relative bg-gray-50">
        {activeTab === 'timelines' && (
          <section className="absolute inset-0 flex flex-col overflow-hidden">
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
        {activeTab === 'graph' && (
          <section className="absolute inset-0 flex flex-col bg-white">
            <MemoryGraphView />
          </section>
        )}
      </div>
    </div>
  );
}

// ── Step 4: Explore ───────────────────────────────────────────────────────────
function ExploreChatView() {
  return <div className="min-h-0 flex-1 bg-white"><FutureSelfChat /></div>;
}

// ── Loading Overlay ───────────────────────────────────────────────────────────
function LoadingOverlay() {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-white/80 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-5 rounded-2xl border border-gray-200 bg-white px-12 py-10 shadow-2xl">
        <Loader2 className="size-10 animate-spin text-gray-900" />
        <div className="text-center">
          <p className="text-sm font-bold text-gray-900">Simulating plausible futures</p>
          <p className="text-xs text-gray-500 mt-1">Building evidence-backed scenarios…</p>
        </div>
      </div>
    </div>
  );
}

// ── ROOT APP SHELL ────────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { label: 'Impact', step: 0 },
  { label: 'Launch Program', step: 1 },
] as const;

export default function App() {
  const currentStep = useChronosStore((state) => state.currentStep);
  const isLoading = useChronosStore((state) => state.isLoading);
  const setStep = useChronosStore((state) => state.setStep);

  return (
    <div className="flex min-h-screen bg-white text-gray-900 font-sans antialiased overflow-hidden">
      
      {/* ── Youssri-style Narrow Left Sidebar ── */}
      {/* Fixed w-16 container with flex layout ensuring children don't overflow the width */}
      <aside className="fixed inset-y-0 left-0 w-16 border-r border-gray-200 bg-white z-50 flex flex-col items-center py-10">
        
        {/* Title container with explicit height to hold rotated text */}
        <div className="flex-none h-24 mb-16 relative w-full flex justify-center items-center">
          <span className="-rotate-90 whitespace-nowrap text-[13px] font-serif font-bold tracking-widest uppercase text-gray-900 absolute">
            Chronos
          </span>
        </div>

        {/* Navigation container */}
        <nav className="flex-1 flex flex-col items-center gap-16 justify-center w-full">
          {NAV_ITEMS.map((item) => (
            <div key={item.label} className="relative w-full h-32 flex justify-center items-center">
              <button
                type="button"
                onClick={() => setStep(item.step)}
                className={`-rotate-90 whitespace-nowrap text-[11px] tracking-[0.2em] uppercase absolute
                  transition-colors duration-300
                  ${currentStep === item.step ? 'text-gray-900 font-bold' : 'text-gray-400 hover:text-gray-900'}`}
              >
                {item.label}
              </button>
            </div>
          ))}
        </nav>
      </aside>

      {/* ── Main Content Area (Offset by sidebar width: pl-16) ── */}
      <main className="flex-1 flex flex-col pl-16 relative min-h-0 h-screen overflow-hidden bg-gray-50">
        {currentStep === 0 && <LandingPage />}

        {currentStep > 0 && (
          <div className="flex flex-col h-full">
            <header className="shrink-0 border-b border-gray-200 bg-white px-8 py-5">
              <h1 className="text-2xl font-serif font-bold text-gray-900 leading-none">
                Chronos Engine
              </h1>
              <p className="mt-1.5 text-xs text-gray-500 font-medium tracking-wide">
                AI Decision Intelligence · FlowState Demo
              </p>
            </header>
            
            <StepProgressBar />
            
            <div className="flex-1 overflow-auto flex flex-col relative bg-white">
              {currentStep === 1 && <ConnectDataView />}
              {currentStep === 2 && <DefineDecisionView />}
              {currentStep === 3 && <SimulateFuturesView />}
              {currentStep === 4 && <ExploreChatView />}
            </div>
          </div>
        )}
      </main>

      {isLoading && <LoadingOverlay />}
    </div>
  );
}