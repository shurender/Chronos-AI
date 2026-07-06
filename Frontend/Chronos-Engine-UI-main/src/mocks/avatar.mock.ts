import type { ChatMessage } from '../types/avatar';

/**
 * Avatar conversation transcript for the FlowState runway anxiety scenario.
 * Assistant response is grounded in graph node citations.
 */
export const mockChatHistory: readonly ChatMessage[] = [
  {
    id: 'msg_system_session_start',
    role: 'system',
    content:
      'Chronos Avatar session initialized. Context loaded: FlowState B2B pivot evaluation (12 nodes, 15 edges).',
    timestamp: '2026-07-03T18:10:00.000Z',
    referencedNodeIds: [],
    citations: [],
  },
  {
    id: 'msg_user_runway_fear',
    role: 'user',
    content: 'What if we run out of money?',
    timestamp: '2026-07-03T18:10:42.000Z',
    referencedNodeIds: [],
    citations: [],
  },
  {
    id: 'msg_assistant_runway_analysis',
    role: 'assistant',
    content: `Based on your decision graph, cash runway is your **binding constraint** right now.

**Current position:** You have **$1.2M raised** with approximately **14 months of runway** at $86K/month net burn across 8 FTE. This is a verified fact from your burn model — not a projection.

**Where the risk concentrates:**
- An **aggressive B2B pivot** compresses your margin for error. The Risk Analyst Agent estimates a **68% probability of cash-out before your first enterprise invoice**, because median seed-stage enterprise cycles run 6–9 months and you have no dedicated AE yet.
- Your **Enterprise Sales Motion** node is flagged with a **data gap** — I cannot verify your team's ability to close six-figure contracts. That uncertainty directly amplifies runway risk on any B2B path.
- However, four **Fortune-500 inbound demos** went unanswered. That is a latent demand signal worth exploiting — but the evidence chain is incomplete (also flagged as a gap).

**What the simulations suggest:**
- *Stay B2C* carries the **lowest expected regret (0.29)** but also the lowest upside — likely an acqui-hire at ~$4.2M by month 16.
- *Hybrid B2B2C* is the **recommended path** (regret: 0.52) because it preserves your $14K MRR while pursuing enterprise pilots, keeping a 4-month runway buffer vs. a full pivot.
- *Aggressive B2B* has the **highest upside** (Series A at $18M valuation) but the **highest regret (0.81)** if the enterprise cycle slips.

**My recommendation:** Do not commit to sunsetting B2C until you have closed one paid design partner. That single milestone de-risks the runway scenario more than any cost cut.

Would you like me to model a specific burn reduction scenario?`,
    timestamp: '2026-07-03T18:10:47.000Z',
    referencedNodeIds: [
      'node_outcome_runway',
      'node_skill_enterprise_sales',
      'node_outcome_enterprise_leads',
      'node_decision_pivot_eval',
      'node_outcome_cac_ltv_gap',
    ],
    citations: [
      {
        nodeId: 'node_outcome_runway',
        label: '$1.2M Raised — 14 Months Runway',
        excerpt: '$86K net burn/month at current headcount of 8 FTE.',
      },
      {
        nodeId: 'node_skill_enterprise_sales',
        label: 'Enterprise Sales Motion (Nascent)',
        excerpt:
          'No dedicated AE, no MEDDIC playbook, no security questionnaire template on file.',
      },
      {
        nodeId: 'node_outcome_enterprise_leads',
        label: '4 Fortune-500 Inbound Demos (Never Assigned)',
        excerpt:
          'Emails from Deloitte, Siemens, and two anonymized @fortune500 domains.',
      },
      {
        nodeId: 'node_decision_pivot_eval',
        label: 'Formal B2B Pivot Evaluation (Q3 2026)',
        excerpt: 'Present decision point — all timelines branch from here.',
      },
      {
        nodeId: 'node_outcome_cac_ltv_gap',
        label: 'Unit Economics Failed: CAC 3.2× LTV',
        excerpt: 'B2C paid spend can be reallocated to extend runway if ads are paused.',
      },
    ],
  },
];
