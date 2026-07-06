import type { SimulationPayload } from '../types/timeline';

/**
 * Three-branch simulation for the FlowState B2B pivot decision.
 * Probabilities sum to 1.0. Agent disagreement centers on runway adequacy.
 */
export const mockSimulationPayload = {
  metadata: {
    generatedAt: '2026-07-03T18:05:00.000Z',
    schemaVersion: '1.0.0',
    query:
      'Simulate outcomes if FlowState pivots from B2C to B2B Enterprise vs. staying the course',
    horizonMonths: 18,
  },

  recommendedTimelineId: 'timeline_hybrid_b2b2c',

  affectedNodeIds: [
    'node_decision_pivot_eval',
    'node_project_enterprise_pilot',
    'node_skill_enterprise_sales',
  ],

  timelines: [
    {
      id: 'timeline_aggressive_b2b',
      title: 'Aggressive B2B Pivot',
      description:
        'Sunset consumer paid tiers within 90 days, hire an enterprise AE, and pursue three $120K ACV design partners before runway ends.',
      probabilityScore: 0.38,
      expectedRegret: 0.81,
      status: 'active',
      anchorNodeIds: [
        'node_decision_pivot_eval',
        'node_project_enterprise_pilot',
        'node_outcome_runway',
        'node_skill_enterprise_sales',
      ],
      confidenceBreakdown: {
        evidenceStrength: 0.71,
        sourceReliability: 0.84,
        modelConsensus: 0.62,
        temporalRelevance: 0.88,
        causalCoherence: 0.79,
      },
      agentDisagreements: [
        {
          agentId: 'strategist',
          agentLabel: 'Strategist Agent',
          position:
            'Runway is sufficient if the team cuts B2C paid spend immediately and closes one pilot by month 8.',
          confidence: 0.77,
          rationale: [
            'Four inbound enterprise demos suggest latent demand not captured in CRM.',
            'B2C CAC/LTV gap frees $22K/month in ad spend for enterprise GTM.',
            'Comparable pivots (Notion, Airtable) closed first enterprise logos within 7 months.',
          ],
        },
        {
          agentId: 'risk_analyst',
          agentLabel: 'Risk Analyst Agent',
          position:
            '14 months runway is insufficient for a full pivot — 68% probability of cash-out before first enterprise invoice.',
          confidence: 0.83,
          rationale: [
            'Median enterprise sales cycle for seed-stage SaaS is 6–9 months with no existing AE.',
            'SOC 2 Type I alone consumes 3–4 months and ~$40K in audit costs.',
            'No enterprise sales skill node has verifiable evidence (hasGap: true).',
          ],
        },
      ],
      milestones: [
        {
          month: 0,
          event: 'Board approves full B2B pivot; B2C paid acquisition paused',
          type: 'decision_point',
          veracity: 'prediction',
          dataSparsity: 0.15,
          citations: [
            {
              nodeId: 'node_decision_pivot_eval',
              label: 'Pivot evaluation decision node',
            },
          ],
        },
        {
          month: 2,
          event: 'First enterprise AE hired (ex-Salesforce SMB)',
          type: 'skill_milestone',
          veracity: 'prediction',
          dataSparsity: 0.35,
          citations: [
            {
              nodeId: 'node_skill_enterprise_sales',
              label: 'Enterprise sales capability gap',
            },
          ],
        },
        {
          month: 5,
          event: 'SOC 2 Type I audit initiated; SSO shipped to staging',
          type: 'project_phase',
          veracity: 'prediction',
          dataSparsity: 0.42,
          citations: [
            {
              nodeId: 'node_project_enterprise_pilot',
              label: 'Enterprise pilot project spec',
            },
          ],
        },
        {
          month: 9,
          event: 'First signed enterprise pilot — Deloitte, $96K ACV',
          type: 'outcome_realized',
          veracity: 'prediction',
          dataSparsity: 0.55,
          citations: [
            {
              nodeId: 'node_outcome_enterprise_leads',
              label: 'Inbound enterprise demand signal',
            },
          ],
        },
        {
          month: 14,
          event: 'Series A term sheet at $18M valuation',
          type: 'outcome_realized',
          veracity: 'prediction',
          dataSparsity: 0.68,
          citations: [
            {
              nodeId: 'node_outcome_runway',
              label: 'Runway constraint node',
              excerpt: 'Pivot succeeds only if pilot revenue lands before month 10.',
            },
          ],
        },
      ],
    },
    {
      id: 'timeline_stay_b2c',
      title: 'Stay B2C',
      description:
        'Double down on consumer growth: optimize onboarding, launch a $9.99/mo Pro tier, and reduce blended CAC by 40% through referral loops.',
      probabilityScore: 0.27,
      expectedRegret: 0.29,
      status: 'archived',
      anchorNodeIds: [
        'node_outcome_50k_mau',
        'node_outcome_cac_ltv_gap',
        'node_outcome_growth_contradiction',
        'node_project_flowstate_mobile',
      ],
      confidenceBreakdown: {
        evidenceStrength: 0.58,
        sourceReliability: 0.67,
        modelConsensus: 0.54,
        temporalRelevance: 0.91,
        causalCoherence: 0.61,
      },
      agentDisagreements: [
        {
          agentId: 'strategist',
          agentLabel: 'Strategist Agent',
          position:
            'Staying B2C avoids execution risk but accepts a low-probability path to venture-scale outcomes.',
          confidence: 0.69,
          rationale: [
            'Team has proven mobile shipping velocity under Maya.',
            '50K MAU provides a distribution base for referral-based CAC reduction.',
          ],
        },
        {
          agentId: 'risk_analyst',
          agentLabel: 'Risk Analyst Agent',
          position:
            'Runway is adequate for B2C iteration — burn drops if paid ads are cut and no enterprise hire is made.',
          confidence: 0.81,
          rationale: [
            'Net burn falls to ~$62K/month without AE hire and SOC 2 costs.',
            'Lower execution risk preserves optionality for 18+ months.',
            'Conflicting retention data (hasContradiction) makes growth projections unreliable.',
          ],
        },
      ],
      milestones: [
        {
          month: 0,
          event: 'Reject B2B pivot; commit to B2C monetization sprint',
          type: 'decision_point',
          veracity: 'prediction',
          dataSparsity: 0.12,
          citations: [
            {
              nodeId: 'node_decision_pivot_eval',
              label: 'Pivot evaluation (rejected)',
            },
          ],
        },
        {
          month: 3,
          event: 'Pro tier launched; 4.2% free-to-paid conversion',
          type: 'project_phase',
          veracity: 'prediction',
          dataSparsity: 0.38,
          citations: [
            {
              nodeId: 'node_project_flowstate_mobile',
              label: 'FlowState mobile product',
            },
          ],
        },
        {
          month: 7,
          event: 'MAU plateaus at 62K; referral loop drives 18% of new signups',
          type: 'outcome_realized',
          veracity: 'prediction',
          dataSparsity: 0.45,
          citations: [
            {
              nodeId: 'node_outcome_50k_mau',
              label: 'Prior MAU growth baseline',
            },
          ],
        },
        {
          month: 12,
          event: 'CAC/LTV ratio improves to 1.8× — still below viability threshold',
          type: 'outcome_realized',
          veracity: 'prediction',
          dataSparsity: 0.52,
          citations: [
            {
              nodeId: 'node_outcome_cac_ltv_gap',
              label: 'Original unit economics failure',
            },
          ],
        },
        {
          month: 16,
          event: 'Modest acqui-hire exit at $4.2M',
          type: 'outcome_realized',
          veracity: 'prediction',
          dataSparsity: 0.71,
          citations: [
            {
              nodeId: 'node_outcome_growth_contradiction',
              label: 'Retention uncertainty caps valuation',
            },
          ],
        },
      ],
    },
    {
      id: 'timeline_hybrid_b2b2c',
      title: 'Hybrid B2B2C',
      description:
        'Maintain B2C as a product-led top-of-funnel while packaging a team tier with admin controls. Pursue enterprise pilots without sunsetting consumer revenue.',
      probabilityScore: 0.35,
      expectedRegret: 0.52,
      status: 'recommended',
      anchorNodeIds: [
        'node_decision_pivot_eval',
        'node_project_flowstate_mobile',
        'node_project_enterprise_pilot',
        'node_outcome_runway',
      ],
      confidenceBreakdown: {
        evidenceStrength: 0.78,
        sourceReliability: 0.86,
        modelConsensus: 0.74,
        temporalRelevance: 0.90,
        causalCoherence: 0.83,
      },
      agentDisagreements: [
        {
          agentId: 'strategist',
          agentLabel: 'Strategist Agent',
          position:
            'Hybrid preserves runway flexibility — B2C cash flow subsidizes enterprise R&D while inbound demos are worked.',
          confidence: 0.84,
          rationale: [
            'No need to kill $14K MRR from early Pro adopters during pivot.',
            'Enterprise inbound leads can be nurtured without a full GTM rebuild.',
            'Maya can ship team features incrementally on existing architecture.',
          ],
        },
        {
          agentId: 'risk_analyst',
          agentLabel: 'Risk Analyst Agent',
          position:
            'Runway is tight for a two-front strategy — split focus may delay both B2C fix and enterprise close.',
          confidence: 0.71,
          rationale: [
            'Engineering bandwidth split across SSO and consumer retention fixes.',
            '14-month runway assumes no major slip; hybrid adds 2–3 months to first enterprise revenue.',
            'Enterprise sales skill gap remains unaddressed in first 4 months.',
          ],
        },
      ],
      milestones: [
        {
          month: 0,
          event: 'Approve hybrid strategy: team tier roadmap + 2 enterprise pilots',
          type: 'decision_point',
          veracity: 'prediction',
          dataSparsity: 0.10,
          citations: [
            {
              nodeId: 'node_decision_pivot_eval',
              label: 'Pivot evaluation decision node',
            },
          ],
        },
        {
          month: 2,
          event: 'FlowState Teams beta — 5-seat plans at $49/mo',
          type: 'project_phase',
          veracity: 'prediction',
          dataSparsity: 0.28,
          citations: [
            {
              nodeId: 'node_project_flowstate_mobile',
              label: 'Existing mobile codebase',
            },
          ],
        },
        {
          month: 4,
          event: 'First enterprise design partner onboarded (Siemens)',
          type: 'outcome_realized',
          veracity: 'prediction',
          dataSparsity: 0.33,
          citations: [
            {
              nodeId: 'node_outcome_enterprise_leads',
              label: 'Inbound enterprise demand',
            },
          ],
        },
        {
          month: 8,
          event: 'Enterprise pilot converted — $72K ACV; B2C MRR grows to $28K',
          type: 'outcome_realized',
          veracity: 'prediction',
          dataSparsity: 0.40,
          citations: [
            {
              nodeId: 'node_project_enterprise_pilot',
              label: 'Enterprise pilot project',
            },
            {
              nodeId: 'node_outcome_cac_ltv_gap',
              label: 'B2C unit economics (partially improved)',
            },
          ],
        },
        {
          month: 13,
          event: 'Seed extension at $10M cap — enough runway for Series A prep',
          type: 'outcome_realized',
          veracity: 'prediction',
          dataSparsity: 0.48,
          citations: [
            {
              nodeId: 'node_outcome_runway',
              label: 'Runway constraint node',
              excerpt: 'Hybrid path preserves 4+ months buffer vs. aggressive pivot.',
            },
          ],
        },
      ],
    },
  ],
} satisfies SimulationPayload;
