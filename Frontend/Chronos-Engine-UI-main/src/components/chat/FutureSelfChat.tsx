import { Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from 'react';

import { mockChatHistory } from '../../mocks/avatar.mock';
import { useChronosStore } from '../../store/useChronosStore';
import type { ChatMessage } from '../../types/avatar';
import type { Citation, VeracityType } from '../../types/graph';
import { VeracityBadge } from '../ui/VeracityBadge';

type GroundingLabel = 'graph_grounded' | 'general_opinion';

const FAKE_RESPONSE_DELAY_MS = 1000;

function createMessageId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

function getGroundingLabel(message: ChatMessage): GroundingLabel {
  if (message.role !== 'assistant') return 'graph_grounded';
  return message.citations.length > 0 ? 'graph_grounded' : 'general_opinion';
}

function formatClock(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function buildFakeAssistantReply(userText: string): ChatMessage {
  const lower = userText.toLowerCase();

  if (lower.includes('runway') || lower.includes('money') || lower.includes('cash')) {
    return {
      id: createMessageId('msg_assistant'),
      role: 'assistant',
      content:
        'Your runway node shows 14 months at current burn. I would prioritize closing one enterprise design partner before cutting B2C revenue — that milestone shifts the cash-out probability more than incremental cost cuts.',
      timestamp: new Date().toISOString(),
      referencedNodeIds: ['node_outcome_runway', 'node_decision_pivot_eval'],
      citations: [
        {
          nodeId: 'node_outcome_runway',
          label: '$1.2M Raised — 14 Months Runway',
          excerpt: '$86K net burn/month at current headcount of 8 FTE.',
        },
        {
          nodeId: 'node_decision_pivot_eval',
          label: 'Formal B2B Pivot Evaluation (Q3 2026)',
          excerpt: 'Present decision point — all timelines branch from here.',
        },
      ],
    };
  }

  return {
    id: createMessageId('msg_assistant'),
    role: 'assistant',
    content:
      'That is a thoughtful question. I do not have a specific simulation branch mapped to it yet, but I can reason from general startup heuristics until we ingest more evidence into your memory graph.',
    timestamp: new Date().toISOString(),
    referencedNodeIds: [],
    citations: [],
  };
}

// ── Grounding meter ───────────────────────────────────────────────────────────
// Signature instrument: instead of a throwaway "general reasoning" caption,
// every assistant reply carries a visible readout of how many memory-graph
// nodes actually support it.
interface GroundingMeterProps {
  readonly citationCount: number;
}

function GroundingMeter({ citationCount }: GroundingMeterProps) {
  const filled = Math.min(citationCount, 4);

  return (
    <div
      className="flex items-center gap-1.5"
      title={`${citationCount} memory graph node${citationCount === 1 ? '' : 's'} cited`}
    >
      <div className="flex items-end gap-[3px]" aria-hidden="true">
        {[0, 1, 2, 3].map((tick) => (
          <span
            key={tick}
            className={[
              'w-[3px] rounded-sm transition-colors duration-300',
              tick < filled ? 'bg-emerald-400' : 'bg-white/[0.08]',
            ].join(' ')}
            style={{ height: `${5 + tick * 3}px` }}
          />
        ))}
      </div>
      <span className="font-mono text-[9px] tracking-widest text-emerald-400/80 uppercase">
        grounded · {citationCount} node{citationCount === 1 ? '' : 's'}
      </span>
    </div>
  );
}

// ── Citation chip ─────────────────────────────────────────────────────────────
interface CitationChipProps {
  readonly citation: Citation;
  readonly veracity: VeracityType;
}

function CitationChip({ citation, veracity }: CitationChipProps) {
  return (
    <button
      type="button"
      title={citation.excerpt ?? citation.label}
      className="group inline-flex max-w-full items-center gap-1.5 rounded
        border border-white/[0.09] bg-white/[0.03]
        px-2 py-1 font-mono text-[11px] text-slate-400
        hover:border-emerald-500/40 hover:bg-emerald-500/[0.06]
        transition-all duration-150"
    >
      <VeracityBadge type={veracity} />
      <span className="truncate text-slate-300 group-hover:text-emerald-100">
        {citation.label}
      </span>
    </button>
  );
}

// ── Typing indicator ──────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex justify-start px-4 py-2">
      <div className="flex items-center gap-3 rounded-2xl rounded-tl-sm border border-white/[0.08] bg-[#141829] px-4 py-3 shadow-xl">
        <div className="flex h-4 items-center gap-1" aria-hidden="true">
          <span
            className="size-1.5 animate-bounce rounded-full bg-indigo-400"
            style={{ animationDelay: '0ms' }}
          />
          <span
            className="size-1.5 animate-bounce rounded-full bg-indigo-400"
            style={{ animationDelay: '150ms' }}
          />
          <span
            className="size-1.5 animate-bounce rounded-full bg-indigo-400"
            style={{ animationDelay: '300ms' }}
          />
        </div>
        <span className="font-mono text-[10px] tracking-widest text-slate-500 uppercase">
          computing response
        </span>
      </div>
    </div>
  );
}

// ── Message bubble ────────────────────────────────────────────────────────────
interface MessageBubbleProps {
  readonly message: ChatMessage;
  readonly resolveVeracity: (nodeId: string) => VeracityType;
}

function MessageBubble({ message, resolveVeracity }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const groundingLabel = getGroundingLabel(message);

  if (isSystem) {
    return (
      <div className="flex justify-center px-4 py-2">
        <p className="rounded-full border border-white/[0.06] bg-white/[0.03] px-3 py-1 text-center font-mono text-[10px] tracking-wide text-slate-600 uppercase">
          {message.content}
        </p>
      </div>
    );
  }

  return (
    <div className={['flex px-4 py-2', isUser ? 'justify-end' : 'justify-start'].join(' ')}>
      <div
        className={[
          'max-w-[80%] rounded-2xl',
          isUser
            ? 'rounded-tr-sm bg-gradient-to-br from-indigo-600 via-indigo-500 to-violet-600 px-4 py-3 text-sm text-white shadow-lg shadow-indigo-500/20 ring-1 ring-white/10'
            : 'overflow-hidden rounded-tl-sm border border-white/[0.08] bg-[#10142a]/95 shadow-xl shadow-black/40',
        ].join(' ')}
      >
        {!isUser && (
          /* Instrument meta bar: who's speaking, when, and how grounded it is */
          <div className="flex items-center gap-2.5 border-b border-white/[0.06] bg-indigo-950/30 px-4 py-2">
            <span className="relative flex size-1.5" aria-hidden="true">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-indigo-400 opacity-60" />
              <span className="relative inline-flex size-1.5 rounded-full bg-indigo-400" />
            </span>
            <span className="font-mono text-[10px] font-semibold tracking-[0.2em] text-indigo-400 uppercase">
              future_self
            </span>
            <span className="font-mono text-[10px] text-slate-600">
              {formatClock(message.timestamp)}
            </span>
            <div className="ml-auto">
              {groundingLabel === 'graph_grounded' ? (
                <GroundingMeter citationCount={message.citations.length} />
              ) : (
                <span className="font-mono text-[9px] tracking-widest text-amber-500/70 uppercase">
                  general reasoning
                </span>
              )}
            </div>
          </div>
        )}

        {/* Content */}
        {isUser ? (
          <div>
            <p className="text-sm leading-relaxed">{message.content}</p>
            <p className="mt-1 text-right font-mono text-[9px] text-white/40">
              {formatClock(message.timestamp)}
            </p>
          </div>
        ) : (
          /* No @tailwindcss/typography (breaks Tailwind v4 resolution in this
             project) — styled by hand with descendant arbitrary variants so
             nested elements (e.g. <strong> inside <p>, <li> inside <ul>) are
             covered, not just direct children. */
          <div
            className="px-4 py-3.5 text-[13.5px] leading-relaxed text-slate-200
              [&_p]:mb-3 [&_p:last-child]:mb-0
              [&_strong]:font-semibold [&_strong]:text-white
              [&_em]:font-medium [&_em]:text-indigo-300 [&_em]:not-italic
              [&_ul]:my-2 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5
              [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-5
              [&_li]:text-slate-200 [&_li]:marker:text-indigo-500/60
              [&_blockquote]:my-2 [&_blockquote]:border-l-2 [&_blockquote]:border-indigo-500/50 [&_blockquote]:pl-3 [&_blockquote]:text-slate-400 [&_blockquote]:italic
              [&_code]:rounded [&_code]:bg-indigo-950/60 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[12px] [&_code]:text-indigo-300
              [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:border [&_pre]:border-white/[0.08] [&_pre]:bg-black/30 [&_pre]:p-3
              [&_pre_code]:bg-transparent [&_pre_code]:p-0
              [&_h1]:mt-1 [&_h1]:mb-2 [&_h1]:text-base [&_h1]:font-semibold [&_h1]:text-white
              [&_h2]:mt-1 [&_h2]:mb-1.5 [&_h2]:text-[13.5px] [&_h2]:font-semibold [&_h2]:text-white
              [&_h3]:text-[13.5px] [&_h3]:font-semibold [&_h3]:text-slate-100
              [&_a]:text-indigo-300 [&_a]:underline [&_a]:underline-offset-2 [&_a:hover]:text-indigo-200
              [&_hr]:my-3 [&_hr]:border-white/[0.08]"
          >
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}

        {/* Citations */}
        {!isUser && message.citations.length > 0 && (
          <div className="flex flex-col gap-2 border-t border-white/[0.06] px-4 pt-3 pb-3.5">
            <span className="font-mono text-[9px] font-semibold tracking-[0.2em] text-slate-500 uppercase">
              source nodes · memory graph
            </span>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.map((citation) => (
                <CitationChip
                  key={`${message.id}-${citation.nodeId}`}
                  citation={citation}
                  veracity={resolveVeracity(citation.nodeId)}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export function FutureSelfChat() {
  const chatHistory     = useChronosStore((state) => state.chatHistory);
  const graphData       = useChronosStore((state) => state.graphData);
  const addChatMessage  = useChronosStore((state) => state.addChatMessage);
  const setStep         = useChronosStore((state) => state.setStep);

  const [draft, setDraft]                   = useState('');
  const [isReplyPending, setIsReplyPending] = useState(false);

  const scrollAnchorRef = useRef<HTMLDivElement>(null);
  const hydratedRef     = useRef(false);
  const replyTimerRef   = useRef<ReturnType<typeof setTimeout> | null>(null);

  const resolveVeracity = useCallback(
    (nodeId: string): VeracityType => {
      const node = graphData?.nodes.find((entry) => entry.id === nodeId);
      return node?.veracity ?? 'inference';
    },
    [graphData],
  );

  useEffect(() => {
    if (hydratedRef.current || chatHistory.length > 0) return;
    hydratedRef.current = true;
    for (const message of mockChatHistory) {
      addChatMessage(message);
    }
  }, [chatHistory.length, addChatMessage]);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isReplyPending]);

  useEffect(() => {
    return () => {
      if (replyTimerRef.current !== null) clearTimeout(replyTimerRef.current);
    };
  }, []);

  // Back button shows an `esc` hint — make it real.
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setStep(3);
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setStep]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || isReplyPending) return;

    const userMessage: ChatMessage = {
      id: createMessageId('msg_user'),
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
      referencedNodeIds: [],
      citations: [],
    };

    addChatMessage(userMessage);
    setDraft('');
    setIsReplyPending(true);

    replyTimerRef.current = setTimeout(() => {
      addChatMessage(buildFakeAssistantReply(trimmed));
      setIsReplyPending(false);
      replyTimerRef.current = null;
    }, FAKE_RESPONSE_DELAY_MS);
  };

  return (
    <div className="flex h-full flex-col bg-[#080b14]">

      {/* ── Console chrome + navigation header ── */}
      <header className="shrink-0 border-b border-white/[0.07] bg-[#0d1020]/90 backdrop-blur-md">
        {/* Terminal strip */}
        <div className="flex items-center gap-2 border-b border-white/[0.05] bg-black/20 px-4 py-1.5">
          <span className="flex items-center gap-1.5" aria-hidden="true">
            <span className="size-2 rounded-full bg-red-500/60" />
            <span className="size-2 rounded-full bg-amber-500/60" />
            <span className="size-2 rounded-full bg-emerald-500/60" />
          </span>
          <span className="font-mono text-[9px] tracking-[0.2em] text-slate-600">
            chronos://future-self · session_04
          </span>
          <span className="ml-auto flex items-center gap-1.5 font-mono text-[9px] tracking-[0.2em] text-emerald-400/80 uppercase">
            <span className="size-1.5 animate-pulse rounded-full bg-emerald-400" aria-hidden="true" />
            live simulation
          </span>
        </div>

        {/* Nav row */}
        <div className="flex items-center justify-between px-5 py-3">
          <button
            type="button"
            onClick={() => setStep(3)}
            className="group flex items-center gap-2 rounded-lg border border-transparent px-3 py-1.5
              text-sm text-indigo-400 hover:text-white
              hover:border-white/[0.08] hover:bg-white/[0.05]
              transition-all duration-200"
            aria-label="Back to Simulate Futures"
          >
            <span
              className="inline-block text-base transition-transform duration-200 group-hover:-translate-x-0.5"
              aria-hidden="true"
            >
              ←
            </span>
            Back to Timelines
            <kbd className="ml-1 rounded border border-white/10 bg-white/5 px-1.5 py-0.5 font-mono text-[9px] text-slate-500 group-hover:text-slate-300">
              esc
            </kbd>
          </button>

          <div className="absolute left-1/2 -translate-x-1/2 text-center">
            <p className="font-mono text-[10px] tracking-widest text-indigo-400 uppercase">
              Future Self Avatar
            </p>
            <p className="mt-0.5 text-[11px] text-slate-500">
              Answers cite nodes from your memory graph
            </p>
          </div>

          {/* Spacer keeps title centered */}
          <div className="w-36" aria-hidden="true" />
        </div>
      </header>

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto py-4">
        {chatHistory.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-3 opacity-40 select-none">
            <div className="flex items-center gap-1.5" aria-hidden="true">
              <span className="size-1 animate-pulse rounded-full bg-indigo-400" />
              <span className="font-mono text-[10px] tracking-[0.3em] text-indigo-400 uppercase">
                awaiting query
              </span>
            </div>
            <p className="text-sm text-slate-500">Ask your simulated future self anything.</p>
          </div>
        )}

        {chatHistory.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            resolveVeracity={resolveVeracity}
          />
        ))}

        {isReplyPending && <TypingIndicator />}

        <div ref={scrollAnchorRef} aria-hidden="true" />
      </div>

      {/* ── Input bar ── */}
      <form
        onSubmit={handleSubmit}
        className="shrink-0 border-t border-white/[0.07] bg-[#0d1020]/80 backdrop-blur-md p-4"
      >
        <div
          className="flex items-center gap-2 rounded-xl border border-white/[0.09] bg-white/[0.04] pl-3
            focus-within:border-indigo-500/50 focus-within:ring-2 focus-within:ring-indigo-500/20
            transition-all duration-200"
        >
          <span className="select-none font-mono text-sm text-indigo-500/70" aria-hidden="true">
            &gt;
          </span>
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask your future self…"
            disabled={isReplyPending}
            aria-label="Chat message"
            className="flex-1 bg-transparent py-2.5 pr-2 text-sm text-slate-100
              placeholder:text-slate-600
              focus:outline-none
              disabled:opacity-50 transition-all duration-200"
          />
          <button
            type="submit"
            disabled={!draft.trim() || isReplyPending}
            className="inline-flex items-center gap-2 rounded-lg m-1.5
              bg-gradient-to-r from-indigo-600 to-violet-600
              hover:from-indigo-500 hover:to-violet-500
              px-4 py-2 text-sm font-medium text-white
              shadow-md shadow-indigo-500/25
              disabled:cursor-not-allowed disabled:opacity-35
              transition-all duration-200"
          >
            <Send className="size-4" aria-hidden="true" />
            Send
          </button>
        </div>
        <p className="mt-2 text-center font-mono text-[9px] tracking-widest text-slate-700 uppercase">
          [enter] send · [shift+enter] new line
        </p>
      </form>
    </div>
  );
}