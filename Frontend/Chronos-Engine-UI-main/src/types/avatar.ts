/**
 * @file avatar.ts
 * @description Domain contracts for the Chronos conversational avatar interface.
 * Cross-references graph entities for grounded, citation-aware responses.
 */

import type { Citation, GraphNodeId } from './graph';

// ---------------------------------------------------------------------------
// Primitive unions
// ---------------------------------------------------------------------------

/**
 * Speaker role in the avatar chat transcript.
 */
export type ChatRole = 'user' | 'assistant' | 'system';

/**
 * Processing lifecycle of an avatar turn.
 */
export type AvatarResponseStatus = 'complete' | 'partial' | 'error';

/**
 * Conversational intent classification returned by the avatar engine.
 */
export type AvatarIntent =
  | 'clarification'
  | 'recommendation'
  | 'explanation'
  | 'challenge'
  | 'summarization';

// ---------------------------------------------------------------------------
// Chat entities
// ---------------------------------------------------------------------------

/**
 * A single message in the avatar conversation transcript.
 */
export interface ChatMessage {
  readonly id: string;

  readonly role: ChatRole;

  /** Markdown-safe message body. */
  readonly content: string;

  /** ISO-8601 timestamp of message creation. */
  readonly timestamp: string;

  /**
   * Graph nodes referenced inline in this message.
   * Enables click-to-highlight in the knowledge graph panel.
   */
  readonly referencedNodeIds: readonly GraphNodeId[];

  /**
   * Structured citations grounding this message in the knowledge graph.
   * Present on assistant messages; empty on user/system messages.
   */
  readonly citations: readonly Citation[];
}

/**
 * Suggested follow-up action rendered as quick-reply chips in the UI.
 */
export interface AvatarSuggestedAction {
  readonly id: string;

  readonly label: string;

  /** Pre-filled prompt sent when the user selects this action. */
  readonly prompt: string;
}

/**
 * Root JSON contract for `POST /avatar/chat` (or equivalent) responses.
 */
export interface AvatarResponse {
  readonly status: AvatarResponseStatus;

  /** Primary assistant reply appended to the transcript. */
  readonly message: ChatMessage;

  readonly intent: AvatarIntent;

  /**
   * Model confidence in the response grounding and relevance.
   * Range: 0.0–1.0.
   */
  readonly confidence: number;

  /** Optional quick-reply suggestions for the user. */
  readonly suggestedActions: readonly AvatarSuggestedAction[];

  /**
   * When true, the UI SHOULD prompt the user to supply missing context
   * before proceeding with a simulation or graph mutation.
   */
  readonly requiresUserInput: boolean;

  /**
   * Optional error detail when {@link status} is `'error'`.
   * MUST be omitted on successful responses.
   */
  readonly errorMessage?: string;
}
