import { Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';

import { chronosApi } from '../../api/chronosApi';
import { useChronosStore } from '../../store/useChronosStore';
import type { ChatMessage } from '../../types/avatar';
import type { Citation, VeracityType } from '../../types/graph';
import { VeracityBadge } from '../ui/VeracityBadge';

type GroundingLabel = 'graph_grounded' | 'general_opinion';

function createMessageId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

function normalizeCitations(citations: readonly { nodeId: string; label: string; excerpt?: string | null; url?: string | null }[]): Citation[] {
  return citations.map((citation) => ({
    nodeId: citation.nodeId,
    label: citation.label,
    excerpt: citation.excerpt ?? undefined,
    url: citation.url ?? undefined,
  }));
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
              tick < filled ? 'bg-gray-800' : 'bg-gray-200',
            ].join(' ')}
            style={{ height: `${5 + tick * 3}px` }}
          />
        ))}
      </div>
      <span className="font-mono text-[9px] tracking-widest text-gray-600 uppercase">
        grounded · {citationCount} node{citationCount === 1 ? '' : 's'}
      </span>
    </div>
  );
}

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
        border border-gray-200 bg-white
        px-2 py-1 font-mono text-[11px] text-gray-500
        hover:border-gray-900 hover:bg-gray-50
        transition-all duration-150"
    >
      <VeracityBadge type={veracity} />
      <span className="truncate text-gray-700 group-hover:text-gray-900">
        {citation.label}
      </span>
    </button>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start px-4 py-2">
      <div className="flex items-center gap-3 rounded-2xl rounded-tl-sm border border-gray-200 bg-gray-50 px-4 py-3 shadow-sm">
        <div className="flex h-4 items-center gap-1" aria-hidden="true">
          <span className="size-1.5 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '0ms' }} />
          <span className="size-1.5 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '150ms' }} />
          <span className="size-1.5 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '300ms' }} />
        </div>
        <span className="font-mono text-[10px] tracking-widest text-gray-500 uppercase">
          computing response
        </span>
      </div>
    </div>
  );
}

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
        <p className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-center font-mono text-[10px] tracking-wide text-gray-500 uppercase">
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
            ? 'rounded-tr-sm bg-gray-900 px-4 py-3 text-sm text-white shadow-sm ring-1 ring-gray-900/10'
            : 'overflow-hidden rounded-tl-sm border border-gray-200 bg-white shadow-sm',
        ].join(' ')}
      >
        {!isUser && (
          <div className="flex items-center gap-2.5 border-b border-gray-100 bg-gray-50 px-4 py-2">
            <span className="relative flex size-1.5" aria-hidden="true">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-gray-900 opacity-60" />
              <span className="relative inline-flex size-1.5 rounded-full bg-gray-900" />
            </span>
            <span className="font-mono text-[10px] font-bold tracking-[0.2em] text-gray-900 uppercase">
              future_self
            </span>
            <span className="font-mono text-[10px] text-gray-500">
              {formatClock(message.timestamp)}
            </span>
            <div className="ml-auto">
              {groundingLabel === 'graph_grounded' ? (
                <GroundingMeter citationCount={message.citations.length} />
              ) : (
                <span className="font-mono text-[9px] tracking-widest text-amber-600 uppercase">
                  general reasoning
                </span>
              )}
            </div>
          </div>
        )}

        {isUser ? (
          <div>
            <p className="text-sm leading-relaxed">{message.content}</p>
            <p className="mt-1 text-right font-mono text-[9px] text-gray-400">
              {formatClock(message.timestamp)}
            </p>
          </div>
        ) : (
          <div
            className="px-4 py-3.5 text-[13.5px] leading-relaxed text-gray-700
              [&_p]:mb-3 [&_p:last-child]:mb-0
              [&_strong]:font-semibold [&_strong]:text-gray-900
              [&_em]:font-medium [&_em]:text-gray-900 [&_em]:not-italic
              [&_ul]:my-2 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5
              [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-5
              [&_li]:text-gray-700 [&_li]:marker:text-gray-400
              [&_blockquote]:my-2 [&_blockquote]:border-l-2 [&_blockquote]:border-gray-300 [&_blockquote]:pl-3 [&_blockquote]:text-gray-500 [&_blockquote]:italic
              [&_code]:rounded [&_code]:bg-gray-100 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[12px] [&_code]:text-gray-800
              [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:border [&_pre]:border-gray-200 [&_pre]:bg-gray-50 [&_pre]:p-3
              [&_pre_code]:bg-transparent [&_pre_code]:p-0
              [&_h1]:mt-1 [&_h1]:mb-2 [&_h1]:text-base [&_h1]:font-semibold [&_h1]:text-gray-900
              [&_h2]:mt-1 [&_h2]:mb-1.5 [&_h2]:text-[13.5px] [&_h2]:font-semibold [&_h2]:text-gray-900
              [&_h3]:text-[13.5px] [&_h3]:font-semibold [&_h3]:text-gray-800
              [&_a]:text-gray-900 [&_a]:underline [&_a]:underline-offset-2 [&_a:hover]:text-gray-600
              [&_hr]:my-3 [&_hr]:border-gray-200"
          >
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}

        {!isUser && message.citations.length > 0 && (
          <div className="flex flex-col gap-2 border-t border-gray-100 px-4 pt-3 pb-3.5 bg-gray-50/50">
            <span className="font-mono text-[9px] font-semibold tracking-[0.2em] text-gray-500 uppercase">
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

export function FutureSelfChat() {
  const chatHistory       = useChronosStore((state) => state.chatHistory);
  const graphData         = useChronosStore((state) => state.graphData);
  const addChatMessage    = useChronosStore((state) => state.addChatMessage);
  const setStep           = useChronosStore((state) => state.setStep);
  const decisionQuestion  = useChronosStore((state) => state.decisionQuestion);
  const simulationData    = useChronosStore((state) => state.simulationData);

  const [draft, setDraft]                   = useState('');
  const [isReplyPending, setIsReplyPending] = useState(false);

  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  const resolveVeracity = useCallback(
    (nodeId: string): VeracityType => {
      const node = graphData?.nodes.find((entry) => entry.id === nodeId);
      return node?.veracity ?? 'inference';
    },
    [graphData],
  );

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isReplyPending]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setStep(3);
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setStep]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
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

    try {
      const data = await chronosApi.chat({
        message: trimmed,
        decisionQuestion,
        selectedTimelineId: simulationData?.recommendedTimelineId ?? null,
        simulationContext: simulationData ? { simulationData } : null,
        graphNodeIds: graphData?.nodes.map((n) => n.id) ?? [],
      });

      addChatMessage({
        id: createMessageId('msg_assistant'),
        role: 'assistant',
        content: data.content,
        timestamp: new Date().toISOString(),
        referencedNodeIds: data.referencedNodeIds ?? [],
        citations: normalizeCitations(data.citations ?? []),
      });
    } catch (error) {
      console.warn('Future Self backend unavailable; showing a low-confidence fallback message.', error);
      addChatMessage({
        id: createMessageId('msg_assistant'),
        role: 'assistant',
        content:
          '_(Future Self backend is unreachable, so this is general reasoning with low confidence.)_\n\n' +
          'I could not reach the simulation backend to ground this answer. Once the backend is running, ' +
          'I can cite your memory graph and evidence directly.',
        timestamp: new Date().toISOString(),
        referencedNodeIds: [],
        citations: [],
      });
    } finally {
      setIsReplyPending(false);
    }
  };

  return (
    <div className="flex h-full flex-col bg-white">
      <header className="shrink-0 border-b border-gray-200 bg-white/90 backdrop-blur-md">
        <div className="flex items-center gap-2 border-b border-gray-100 bg-gray-50 px-4 py-1.5">
          <span className="flex items-center gap-1.5" aria-hidden="true">
            <span className="size-2 rounded-full bg-red-400" />
            <span className="size-2 rounded-full bg-amber-400" />
            <span className="size-2 rounded-full bg-green-400" />
          </span>
          <span className="font-mono text-[9px] tracking-[0.2em] text-gray-500 uppercase">
            chronos://future-self · session_04
          </span>
          <span className="ml-auto flex items-center gap-1.5 font-mono text-[9px] tracking-[0.2em] text-gray-900 uppercase">
            <span className="size-1.5 animate-pulse rounded-full bg-gray-900" aria-hidden="true" />
            structured simulation
          </span>
        </div>

        <div className="flex items-center justify-between px-5 py-3">
          <button
            type="button"
            onClick={() => setStep(3)}
            className="group flex items-center gap-2 rounded-lg border border-transparent px-3 py-1.5
              text-sm text-gray-500 hover:text-gray-900
              hover:border-gray-200 hover:bg-gray-50
              transition-all duration-200"
          >
            <span className="inline-block text-base transition-transform duration-200 group-hover:-translate-x-0.5" aria-hidden="true">
              ←
            </span>
            Back to Timelines
            <kbd className="ml-1 rounded border border-gray-200 bg-white px-1.5 py-0.5 font-mono text-[9px] text-gray-400 group-hover:text-gray-600">
              esc
            </kbd>
          </button>

          <div className="absolute left-1/2 -translate-x-1/2 text-center">
            <p className="font-serif text-lg font-bold text-gray-900">
              Future Self Avatar
            </p>
            <p className="mt-0.5 text-[11px] text-gray-500">
              Answers cite nodes from your memory graph
            </p>
          </div>
          <div className="w-36" aria-hidden="true" />
        </div>
      </header>

      <div className="flex-1 overflow-y-auto py-4 bg-gray-50/30">
        {chatHistory.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-3 opacity-40 select-none">
            <div className="flex items-center gap-1.5" aria-hidden="true">
              <span className="size-1 animate-pulse rounded-full bg-gray-400" />
              <span className="font-mono text-[10px] tracking-[0.3em] text-gray-500 uppercase">
                awaiting query
              </span>
            </div>
            <p className="text-sm text-gray-400">Ask your simulated future self anything.</p>
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

      <form
        onSubmit={handleSubmit}
        className="shrink-0 border-t border-gray-200 bg-white/80 backdrop-blur-md p-4"
      >
        <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 pl-3 focus-within:border-gray-900 focus-within:ring-1 focus-within:ring-gray-900/10 transition-all duration-200">
          <span className="select-none font-mono text-sm text-gray-400" aria-hidden="true">
            &gt;
          </span>
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask your future self…"
            disabled={isReplyPending}
            className="flex-1 bg-transparent py-3 pr-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none disabled:opacity-50 transition-all duration-200"
          />
          <button
            type="submit"
            disabled={!draft.trim() || isReplyPending}
            className="inline-flex items-center gap-2 rounded-lg m-1.5 bg-gray-900 px-5 py-2 text-sm font-semibold text-white shadow-sm disabled:cursor-not-allowed disabled:opacity-35 transition-all duration-200 hover:bg-gray-800"
          >
            <Send className="size-4" aria-hidden="true" />
            Send
          </button>
        </div>
        <p className="mt-2 text-center font-mono text-[9px] tracking-widest text-gray-400 uppercase">
          [enter] send · [shift+enter] new line
        </p>
      </form>
    </div>
  );
}
