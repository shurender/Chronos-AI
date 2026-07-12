import { AlertCircle, CheckCircle2, ChevronDown, FileText, Loader2, MessageSquare, Plug, Upload } from 'lucide-react';
import { useState, useEffect, useLayoutEffect } from 'react';
import { FutureSelfChat } from './components/chat/FutureSelfChat';
import { MemoryGraphView } from './components/graph/MemoryGraphView';
import { StepProgressBar } from './components/layout/StepProgressBar';
import { TimelineCard } from './components/timeline/TimelineCard';
import { useChronosStore } from './store/useChronosStore';
import { LandingPage } from './components/layout/LandingPage';
import type { ConnectorProvider, ConnectorSource, ConnectorStatus } from './api/contracts';

const CHRONOS_LOGO_SRC = '/chronos-logo.svg';

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
  const [maxItems, setMaxItems] = useState(200);
  const [manualGithubRepo, setManualGithubRepo] = useState('');
  const publicGithubExamples = ['fastapi/fastapi', 'vercel/next.js', 'microsoft/vscode'];
  const loadDemoWorkspace = useChronosStore((state) => state.loadDemoWorkspace);
  const startConnector = useChronosStore((state) => state.startConnector);
  const ingestGithubRepo = useChronosStore((state) => state.ingestGithubRepo);
  const loadConnectorSources = useChronosStore((state) => state.loadConnectorSources);
  const selectConnectorSources = useChronosStore((state) => state.selectConnectorSources);
  const syncConnector = useChronosStore((state) => state.syncConnector);
  const uploadFiles = useChronosStore((state) => state.uploadFiles);
  const refreshConnectors = useChronosStore((state) => state.refreshConnectors);
  const connectorStatuses = useChronosStore((state) => state.connectorStatuses);
  const connectorSources = useChronosStore((state) => state.connectorSources);
  const selectedConnectorSourceIds = useChronosStore((state) => state.selectedConnectorSourceIds);
  const connectStatus = useChronosStore((state) => state.connectStatus);
  const errorMessage = useChronosStore((state) => state.errorMessage);
  const backendStatus = useChronosStore((state) => state.backendStatus);
  const isLoading = useChronosStore((state) => state.isLoading);

  useEffect(() => {
    void refreshConnectors();
  }, [refreshConnectors]);

  useEffect(() => {
    (['slack', 'notion'] as ConnectorProvider[]).forEach((provider) => {
      if (connectorStatuses[provider].connected && connectorSources[provider].length === 0) {
        void loadConnectorSources(provider);
      }
    });
  }, [connectorStatuses, connectorSources, loadConnectorSources]);

  const sources = [
    { provider: 'github', icon: GithubIcon, label: 'Add public GitHub repo', sub: 'Paste owner/repo or URL' },
    { provider: 'slack', icon: SlackIcon, label: 'Connect Slack', sub: 'Threads & channels' },
    { provider: 'notion', icon: NotionIcon, label: 'Connect Notion', sub: 'Docs & pages' },
  ] as const;

  const sourceLabel = (source: ConnectorSource) => {
    if ('full_name' in source) return source.full_name;
    if ('title' in source) return source.title;
    return `#${source.name}`;
  };

  const sourceMeta = (source: ConnectorSource) => {
    if ('private' in source) return source.private ? 'Private repo' : 'Public repo';
    if ('is_private' in source) return source.is_private ? (source.is_member ? 'Private channel' : 'Private, not joined') : 'Public channel';
    return source.type;
  };

  const toggleSource = (provider: ConnectorProvider, sourceId: string) => {
    const current = selectedConnectorSourceIds[provider];
    const next = current.includes(sourceId)
      ? current.filter((id) => id !== sourceId)
      : [...current, sourceId];
    void selectConnectorSources(provider, next);
  };

  const statusText = (status: ConnectorStatus) => {
    if (status.status === 'not_connected') return 'Not connected';
    if (status.status === 'syncing') return 'Syncing';
    if (status.status === 'connecting') return 'Connecting';
    if (status.status === 'connected') return status.last_synced ? `Last synced ${new Date(status.last_synced).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Connected';
    return 'Error';
  };

  const statusClass = (status: ConnectorStatus) => {
    if (status.status === 'connected') return 'text-emerald-700';
    if (status.status === 'syncing' || status.status === 'connecting') return 'text-amber-700';
    if (status.status === 'error') return 'text-red-600';
    return 'text-gray-500';
  };

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 py-8 sm:px-6 sm:py-12 bg-white animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="w-full max-w-3xl rounded-2xl border border-gray-200 bg-white p-5 text-center shadow-xl sm:p-10">
        <h1 className="text-3xl font-serif tracking-tight text-gray-900">
          Connect Your Data Sources
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-gray-500 max-w-lg mx-auto">
          Chronos ingests your decision history from code commits, team
          conversations, and documents to build a living memory graph.
        </p>
        <p className={`mt-4 text-xs font-medium ${backendStatus === 'connected' ? 'text-emerald-700' : 'text-amber-700'}`}>
          Backend {backendStatus === 'connected' ? 'connected' : backendStatus === 'disconnected' ? 'disconnected' : 'checking...'}
        </p>

        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
          {sources.map(({ provider, icon: Icon, label, sub }) => {
            const status = connectorStatuses[provider];
            const availableSources = connectorSources[provider];
            const selectedIds = selectedConnectorSourceIds[provider];
            return (
            <div
              key={label}
              className="flex min-h-[310px] flex-col items-center gap-3 rounded-xl border border-gray-100 bg-gray-50 px-5 py-5 text-center transition-all duration-300 hover:border-gray-300 hover:bg-white hover:shadow-md"
            >
              <Icon className="size-7 text-gray-800" />
              <div>
                <span className="block text-sm font-semibold text-gray-900">{label}</span>
                <span className="block mt-0.5 text-[11px] text-gray-500">{sub}</span>
              </div>
              <div className={`mt-auto flex items-center gap-1.5 text-[11px] font-medium ${provider === 'github' ? 'text-gray-500' : statusClass(status)}`}>
                {provider === 'github' ? <Plug className="size-3.5" /> : status.status === 'connected' ? <CheckCircle2 className="size-3.5" /> : status.status === 'error' ? <AlertCircle className="size-3.5" /> : <Plug className="size-3.5" />}
                <span>{provider === 'github' ? 'Public repo only' : statusText(status)}</span>
              </div>
              {status.connected && provider !== 'github' && (
                <div className="w-full rounded-lg border border-gray-200 bg-white p-2 text-left">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="text-[11px] font-semibold text-gray-700">{selectedIds.length} selected</span>
                    <button
                      type="button"
                      onClick={() => void loadConnectorSources(provider)}
                      className="text-[11px] font-semibold text-gray-500 hover:text-gray-900"
                    >
                      Refresh
                    </button>
                  </div>
                  {availableSources.length === 0 ? (
                    <p className="text-[11px] text-gray-500">Refresh to choose sources.</p>
                  ) : (
                    <div className="max-h-32 space-y-1 overflow-auto pr-1">
                      {availableSources.slice(0, 20).map((source) => {
                        const disabled = 'is_private' in source && source.is_private && !source.is_member;
                        return (
                          <label key={source.id} className={`flex gap-2 rounded-md px-1 py-1 text-[11px] ${disabled ? 'text-gray-400' : 'text-gray-700'}`}>
                            <input
                              type="checkbox"
                              checked={selectedIds.includes(source.id)}
                              disabled={disabled || isLoading}
                              onChange={() => toggleSource(provider, source.id)}
                              className="mt-0.5 size-3 accent-gray-900"
                            />
                            <span className="min-w-0">
                              <span className="block truncate font-medium">{sourceLabel(source)}</span>
                              <span className="block truncate text-gray-400">{sourceMeta(source)}</span>
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
              {provider !== 'github' && (
                <button
                  onClick={() => {
                    if (status.connected) {
                      void syncConnector(provider, { sourceIds: selectedIds, maxItems });
                    } else {
                      startConnector(provider);
                    }
                  }}
                  disabled={isLoading}
                  className="w-full rounded-lg border border-gray-900 bg-gray-900 px-3 py-2 text-xs font-semibold text-white transition hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {status.status === 'syncing' ? 'Syncing...' : status.connected ? 'Sync selected' : 'Connect'}
                </button>
              )}
              {provider !== 'github' && status.error && <p className="text-[11px] leading-snug text-red-600">{status.error}</p>}
              {provider === 'github' && (
                <form
                  className="w-full rounded-lg border border-gray-200 bg-white p-2 text-left"
                  onSubmit={(event) => {
                    event.preventDefault();
                    const repo = manualGithubRepo.trim();
                    if (repo) void ingestGithubRepo(repo);
                  }}
                >
                  <label className="block text-[11px] font-semibold text-gray-700">
                    Public repo to ingest
                  </label>
                  <input
                    type="text"
                    value={manualGithubRepo}
                    onChange={(event) => setManualGithubRepo(event.target.value)}
                    placeholder="owner/repo or GitHub URL"
                    disabled={isLoading}
                    className="mt-1 w-full rounded-md border border-gray-200 px-2 py-1.5 text-[11px] text-gray-900 placeholder:text-gray-400 focus:border-gray-900 focus:outline-none disabled:opacity-50"
                  />
                  <button
                    type="submit"
                    disabled={isLoading || !manualGithubRepo.trim()}
                    className="mt-2 w-full rounded-md border border-gray-200 bg-white px-2 py-1.5 text-[11px] font-semibold text-gray-700 transition hover:border-gray-300 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Ingest & continue
                  </button>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {publicGithubExamples.map((repo) => (
                      <button
                        key={repo}
                        type="button"
                        onClick={() => setManualGithubRepo(repo)}
                        disabled={isLoading}
                        className="rounded-full border border-gray-200 px-2 py-1 text-[10px] font-medium text-gray-500 transition hover:border-gray-300 hover:text-gray-900 disabled:opacity-40"
                      >
                        {repo}
                      </button>
                    ))}
                  </div>
                  <p className="mt-2 text-[10px] leading-snug text-gray-400">
                    This public demo does not browse token-backed account repositories.
                  </p>
                </form>
              )}
              {status.connected && provider !== 'github' && (
                <p className="text-[11px] text-gray-500">
                  {(status.source_counts.new ?? 0)} new · {(status.source_counts.updated ?? 0)} updated · {(status.source_counts.skipped_duplicate ?? 0)} skipped
                </p>
              )}
              {status.connected && provider !== 'github' && (
                <p className="text-[11px] text-gray-500">
                  {status.items_ingested ?? status.source_counts.chunks ?? 0} items · {status.source_counts.nodes ?? 0} nodes
                </p>
              )}
            </div>
            );
          })}
        </div>

        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="inline-flex items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-semibold text-gray-800">
            Max items
            <input
              type="number"
              min={1}
              max={200}
              value={maxItems}
              onChange={(event) => setMaxItems(Number(event.target.value))}
              className="w-20 rounded-lg border border-gray-200 px-2 py-1 text-xs"
            />
          </label>
          <label className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-semibold text-gray-800 transition hover:border-gray-300 hover:bg-gray-50">
            <Upload className="size-4" aria-hidden="true" />
            Upload files
            <input
              type="file"
              multiple
              className="hidden"
              onChange={(event) => {
                if (event.target.files?.length) void uploadFiles(event.target.files);
                event.currentTarget.value = '';
              }}
            />
          </label>
          <button
            onClick={() => void loadDemoWorkspace()}
            disabled={isLoading}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-semibold text-gray-600 transition hover:border-gray-300 hover:bg-gray-50 disabled:opacity-50"
          >
            <FileText className="size-4" aria-hidden="true" />
            {isLoading ? 'Loading sample data...' : 'Use sample demo data'}
          </button>
        </div>
        {connectStatus && <p className="mt-3 text-xs text-emerald-700">{connectStatus}</p>}
        {errorMessage && <p className="mt-3 text-xs text-red-600">{errorMessage}</p>}
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
  const { decisionQuestion, setDecisionQuestion, decisionType, setDecisionType, horizon, setHorizon, risk, setRisk, goal, setGoal, constraints, setConstraints, geography, setGeography, optionA, setOptionA, optionB, setOptionB, optionC, setOptionC, runSimulation, isLoading, errorMessage } = useChronosStore();

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 py-8 sm:px-6 sm:py-12 bg-white animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="w-full max-w-2xl rounded-2xl border border-gray-200 bg-white p-5 shadow-xl sm:p-8">
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

        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
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

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div><label className={LABEL_CLASS}>Constraints</label><input type="text" value={constraints} onChange={(e) => setConstraints(e.target.value)} placeholder="e.g. limited runway" disabled={isLoading} className={FIELD_CLASS} /></div>
          <div><label className={LABEL_CLASS}>Geography / context</label><input type="text" value={geography} onChange={(e) => setGeography(e.target.value)} placeholder="e.g. remote, US-based" disabled={isLoading} className={FIELD_CLASS} /></div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div><label className={LABEL_CLASS}>Option A</label><input type="text" value={optionA} onChange={(e) => setOptionA(e.target.value)} disabled={isLoading} className={FIELD_CLASS} /></div>
          <div><label className={LABEL_CLASS}>Option B</label><input type="text" value={optionB} onChange={(e) => setOptionB(e.target.value)} disabled={isLoading} className={FIELD_CLASS} /></div>
          <div><label className={LABEL_CLASS}>Option C (optional)</label><input type="text" value={optionC} onChange={(e) => setOptionC(e.target.value)} disabled={isLoading} className={FIELD_CLASS} /></div>
        </div>

        <button onClick={() => void runSimulation()} disabled={isLoading || decisionQuestion.trim().length === 0} className="mt-8 inline-flex w-full items-center justify-center rounded-xl bg-gray-900 px-6 py-3.5 text-sm font-semibold text-white shadow-md disabled:cursor-not-allowed disabled:opacity-35 transition-all hover:bg-gray-800">
          Run Simulation
        </button>
        {errorMessage && <p className="mt-3 text-xs text-red-600">{errorMessage}</p>}
      </div>
    </div>
  );
}

// ── Panels ───────────────────────────────────────────────────────────────
function HistoricalPrecedentsPanel() {
  const historicalPrecedents = useChronosStore((state) => state.historicalPrecedents);
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="shrink-0 border-b border-gray-200 bg-white px-4 py-3 sm:px-8">
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
              <li key={p.chunk_id} className="w-[min(18rem,80vw)] shrink-0 rounded-lg border border-gray-200 bg-gray-50 p-4">
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
  const simulationData = useChronosStore((state) => state.simulationData);
  const [expanded, setExpanded] = useState(false);
  const evidenceLabel = simulationData?.isDemoEvidence
    ? 'Demo Pack'
    : simulationData?.evidenceProvider ?? 'Evidence';

  return (
    <div className="shrink-0 border-b border-gray-200 bg-gray-50/50 px-4 py-3 sm:px-8">
      <button onClick={() => setExpanded((v) => !v)} className="flex w-full items-center justify-between text-left">
        <span className="flex items-center gap-2">
          <span className="text-xs font-semibold tracking-widest text-gray-600 uppercase">External Evidence</span>
          <span className="rounded-full border border-gray-300 bg-white px-2 py-0.5 text-[10px] font-medium text-gray-600">{evidenceLabel}</span>
        </span>
        <ChevronDown className={`size-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>
      {expanded && (
        externalEvidence.length === 0 ? (
          <p className="mt-2 text-xs text-gray-500">No external evidence attached.</p>
        ) : (
          <ul className="mt-3 flex gap-3 overflow-x-auto pb-2">
            {externalEvidence.map((e) => (
              <li key={e.id} className="w-[min(20rem,82vw)] shrink-0 rounded-lg border border-gray-200 bg-white p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-xs font-semibold leading-snug text-gray-900">{e.title}</p>
                  <span className="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-bold text-gray-600">{Math.round(e.confidence * 100)}%</span>
                </div>
                <p className="mt-2 text-[11px] leading-relaxed text-gray-600">{e.summary}</p>
                <div className="mt-3 flex items-center justify-between gap-2 text-[10px] text-gray-500">
                  <span className="truncate">{e.is_live_source ? 'Live' : e.is_demo_source ? 'Demo' : 'Source'} · {e.source_name}</span>
                  {e.source_url && (
                    <a href={e.source_url} target="_blank" rel="noreferrer" className="shrink-0 font-semibold text-gray-800 underline underline-offset-2">
                      Open
                    </a>
                  )}
                </div>
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
  const [expanded, setExpanded] = useState(false);

  if (!agentCouncil) return null;

  return (
    <div className="shrink-0 border-b border-gray-200 bg-white px-4 py-3 sm:px-8">
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
            <li key={a.agent_id} className="w-[min(18rem,80vw)] shrink-0 rounded-lg border border-gray-200 bg-gray-50 p-4">
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
  const selectedTimelineId = useChronosStore((state) => state.selectedTimelineId);
  const setSelectedTimelineId = useChronosStore((state) => state.setSelectedTimelineId);
  const [activeTab, setActiveTab] = useState<'timelines' | 'graph'>('timelines');

  if (!simulationData) return <div className="flex flex-1 items-center justify-center text-sm text-gray-500 bg-gray-50">No data available. Run simulation from Step 2.</div>;

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-white animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex shrink-0 flex-col gap-3 border-b border-gray-200 bg-white px-4 py-4 sm:px-8 md:flex-row md:items-center md:justify-between">
        <div className="md:w-1/3">
          <h2 className="text-xl font-serif font-bold text-gray-900">Simulated Futures</h2>
          <p className="text-xs text-gray-500 mt-1">{simulationData.timelines.length} evidence-backed branches</p>
        </div>
        <div className="flex w-full bg-gray-100 p-1 rounded-lg border border-gray-200 md:w-auto">
          <button onClick={() => setActiveTab('timelines')} className={`flex-1 px-3 py-1.5 text-xs font-semibold rounded-md transition-all sm:px-6 ${activeTab === 'timelines' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}>Timeline Branches</button>
          <button onClick={() => setActiveTab('graph')} className={`flex-1 px-3 py-1.5 text-xs font-semibold rounded-md transition-all sm:px-6 ${activeTab === 'graph' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}>Memory Graph</button>
        </div>
        <div className="flex md:w-1/3 md:justify-end">
          <button onClick={() => setStep(4)} className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-gray-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-gray-800 md:w-auto">
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
            <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-auto p-4 sm:gap-6 sm:p-8 lg:flex lg:items-start">
              {simulationData.timelines.map((timeline) => (
                <TimelineCard
                  key={timeline.id}
                  timeline={timeline}
                  selected={selectedTimelineId === timeline.id}
                  onSelect={setSelectedTimelineId}
                />
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
  return <div className="min-h-0 flex-1 bg-white animate-in fade-in slide-in-from-bottom-4 duration-700"><FutureSelfChat /></div>;
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


// ── Global Black Transition Curtain ─────────────────────────────────────────
// Driven entirely by React state + CSS transitions (not @keyframes fired at
// mount time), which is what makes the fade reliable across browsers instead
// of occasionally just flashing black with no visible animation.
//
// - fadeInOnMount=false (initial page load): the curtain is already opaque
//   on the very first paint (so there's no flash of the landing page),
//   holds while the shimmer text reads, then fades out smoothly.
// - fadeInOnMount=true (Launch Program transition): the curtain fades IN
//   over visible content, the step swap happens once it's fully opaque,
//   then it fades back out to reveal the wizard.
function Curtain({ animatingOut, fadeInOnMount = false }: { animatingOut: boolean; fadeInOnMount?: boolean }) {
  const [entered, setEntered] = useState(!fadeInOnMount);
  const [textVisible, setTextVisible] = useState(!fadeInOnMount);

  useEffect(() => {
    if (!fadeInOnMount) return;
    const raf = requestAnimationFrame(() => setEntered(true));
    return () => cancelAnimationFrame(raf);
  }, [fadeInOnMount]);

  useEffect(() => {
    const delay = fadeInOnMount ? 500 : 150;
    const t = setTimeout(() => setTextVisible(true), delay);
    return () => clearTimeout(t);
  }, [fadeInOnMount]);

  const curtainShown = entered && !animatingOut;
  const textShown = textVisible && !animatingOut;

  return (
    <div
      className={`fixed inset-0 z-[200] bg-black flex flex-col items-center justify-center
        transition-opacity duration-[800ms] ease-[cubic-bezier(0.76,0,0.24,1)]
        ${curtainShown ? 'opacity-100' : 'opacity-0'} ${animatingOut ? 'pointer-events-none' : ''}`}
    >
      <img
        src={CHRONOS_LOGO_SRC}
        alt=""
        className={`mb-5 size-14 transition-all duration-700 ease-out
          ${textShown ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}
      />
      <h1
        className={`text-5xl font-serif tracking-tighter transition-all duration-700 ease-out
          ${textShown ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}
      >
        <span className="shimmer-text">Chronos Engine</span>
      </h1>
    </div>
  );
}

// ── ROOT APP SHELL ────────────────────────────────────────────────────────────

export default function App() {
  const currentStep = useChronosStore((state) => state.currentStep);
  const isLoading = useChronosStore((state) => state.isLoading);
  const setStep = useChronosStore((state) => state.setStep);
  const checkBackendStatus = useChronosStore((state) => state.checkBackendStatus);
  const activeSection = useChronosStore((state) => state.activeSection);
  const isCurtainVisible = useChronosStore((state) => state.isCurtainVisible);
  const isCurtainAnimatingOut = useChronosStore((state) => state.isCurtainAnimatingOut);
  const triggerAppLaunch = useChronosStore((state) => state.triggerAppLaunch);
  const setCurtainState = useChronosStore((state) => state.setCurtainState);

  useEffect(() => {
    void checkBackendStatus();
  }, [checkBackendStatus]);

  // Initial Full-Screen Intro Loading Curtain: hold for the shimmer text to
  // read, then fade out smoothly (800ms transition, see Curtain component).
  useEffect(() => {
    const t1 = setTimeout(() => setCurtainState(true, true), 1900);
    const t2 = setTimeout(() => setCurtainState(false, false), 2700);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [setCurtainState]);

  // Launch Program → Wizard transition curtain (separate from the initial
  // load curtain above, but reuses the same Curtain component/behavior).
  const [isLaunchTransitioning, setIsLaunchTransitioning] = useState(false);
  const [isLaunchExiting, setIsLaunchExiting] = useState(false);

  const handleLaunch = () => {
    if (isLaunchTransitioning) return;
    setIsLaunchTransitioning(true);
    setIsLaunchExiting(false);
    // Wait for the curtain to fully fade to black before swapping content
    // underneath, so the step change is never visible mid-transition.
    const t1 = setTimeout(() => {
      triggerAppLaunch();
      setIsLaunchExiting(true);
    }, 900);
    // Unmount once the fade-out transition has finished.
    const t2 = setTimeout(() => {
      setIsLaunchTransitioning(false);
      setIsLaunchExiting(false);
    }, 900 + 800);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  };

  // Fix: there are two scrollable containers here — the outer #main-scroll-area
  // AND a nested #wizard-scroll-area that holds the actual step content — and
  // both can retain whatever scroll position the landing page was left at.
  // Reset both, synchronously before paint (useLayoutEffect) and with
  // scroll-behavior forced to 'auto' so it's an instant jump, not a visible
  // slide down-then-up.
  useLayoutEffect(() => {
    if (currentStep > 0) {
      ['main-scroll-area', 'wizard-scroll-area'].forEach((id) => {
        const el = document.getElementById(id);
        if (!el) return;
        const prevBehavior = el.style.scrollBehavior;
        el.style.scrollBehavior = 'auto';
        el.scrollTop = 0;
        el.style.scrollBehavior = prevBehavior;
      });
    }
  }, [currentStep]);

  // Utility to handle navigation scrolling when on Step 0
  const handleScrollNav = (id: string) => {
    setStep(0);
    setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  return (
    <div className="flex min-h-screen bg-white text-gray-900 font-sans antialiased overflow-hidden relative">
      
      {/* ── Global Black Transition Curtain ── */}
      {isCurtainVisible && <Curtain animatingOut={isCurtainAnimatingOut} />}
      {isLaunchTransitioning && <Curtain animatingOut={isLaunchExiting} fadeInOnMount />}

      {/* ── Youssri-style Narrow Left Sidebar ── */}
      <aside className="fixed inset-x-0 top-0 z-50 flex h-14 items-center border-b border-gray-200 bg-white px-4 sm:inset-y-0 sm:left-0 sm:h-auto sm:w-16 sm:flex-col sm:border-b-0 sm:border-r sm:px-0 sm:py-10">
        <div className="relative flex h-full w-auto flex-none items-center justify-center sm:mb-16 sm:h-24 sm:w-full">
          <img src={CHRONOS_LOGO_SRC} alt="Chronos Engine" className="size-8 sm:size-10" />
        </div>

        <nav className="ml-auto flex flex-1 items-center justify-end gap-4 sm:ml-0 sm:w-full sm:flex-col sm:justify-center sm:gap-16">

          {/* Chronos Link */}
          <div className="relative flex h-auto w-auto items-center justify-center sm:h-32 sm:w-full">
            <button
              type="button"
              onClick={() => handleScrollNav('chronos-top')}
              className={`whitespace-nowrap text-[10px] tracking-[0.12em] uppercase transition-colors duration-300 sm:absolute sm:-rotate-90 sm:text-[11px] sm:tracking-[0.2em]
                ${currentStep === 0 && activeSection === 'chronos-top' ? 'text-gray-900 font-bold' : 'text-gray-400 hover:text-gray-900'}`}
            >
              Chronos
            </button>
          </div>

          {/* Impact / FAQ Dynamic Link */}
          <div className="relative flex h-auto w-auto items-center justify-center sm:h-32 sm:w-full">
            <button
              type="button"
              onClick={() => handleScrollNav('impact-section')}
              className="relative flex h-4 w-16 items-center justify-center whitespace-nowrap text-[10px] tracking-[0.12em] uppercase sm:absolute sm:w-24 sm:-rotate-90 sm:text-[11px] sm:tracking-[0.2em]"
            >
              <span className={`absolute transition-opacity duration-500 ${currentStep === 0 && (activeSection === 'impact-section' || activeSection === 'faq-section') ? 'text-gray-900 font-bold' : 'text-gray-400 hover:text-gray-900'} ${activeSection === 'faq-section' ? 'opacity-0' : 'opacity-100'}`}>
                Impact
              </span>
              <span className={`absolute transition-opacity duration-500 ${currentStep === 0 && (activeSection === 'impact-section' || activeSection === 'faq-section') ? 'text-gray-900 font-bold' : 'text-gray-400 hover:text-gray-900'} ${activeSection === 'faq-section' ? 'opacity-100' : 'opacity-0'}`}>
                FAQ
              </span>
            </button>
          </div>

          {/* Launch Program Link */}
          <div className="relative flex h-auto w-auto items-center justify-center sm:h-32 sm:w-full">
            <button
              type="button"
              onClick={handleLaunch}
              className={`whitespace-nowrap text-[10px] tracking-[0.12em] uppercase transition-colors duration-300 sm:absolute sm:-rotate-90 sm:text-[11px] sm:tracking-[0.2em]
                ${currentStep > 0 ? 'text-gray-900 font-bold' : 'text-gray-400 hover:text-gray-900'}`}
            >
              Launch Program
            </button>
          </div>

        </nav>
      </aside>

      {/* ── Main Content Area (Offset by sidebar width: pl-16) ── */}
      <main id="main-scroll-area" className="flex-1 flex flex-col pt-14 sm:pl-16 sm:pt-0 relative min-h-0 h-screen overflow-auto bg-gray-50">

        {/* Step 0: The Unified Scrolling Landing Page */}
        {currentStep === 0 && <LandingPage onLaunch={handleLaunch} />}

        {/* Steps 1-4: The Application Wizard */}
        {currentStep > 0 && (
          <div className="flex flex-col h-full bg-gray-50">
            <header className="shrink-0 border-b border-gray-200 bg-white px-4 py-4 sm:px-8 sm:py-5">
              <img src={CHRONOS_LOGO_SRC} alt="" className="mb-2 size-9" />
              <h1 className="text-2xl font-serif font-bold text-gray-900 leading-none">
                Chronos Engine
              </h1>
              <p className="mt-1.5 text-xs text-gray-500 font-medium tracking-wide">
                AI Decision Intelligence · FlowState Demo
              </p>
            </header>
            
            <StepProgressBar />
            
            <div id="wizard-scroll-area" className="flex-1 overflow-auto flex flex-col relative bg-white">
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
