import type { GraphPayload } from '../types/graph';

/**
 * Chronos Engine knowledge graph for FlowState — a B2C productivity startup
 * evaluating an enterprise pivot. 12 nodes, 15 edges, full ID integrity.
 */
export const mockGraphPayload = {
  metadata: {
    generatedAt: '2026-07-03T18:00:00.000Z',
    schemaVersion: '1.0.0',
    query:
      'Map decision history for FlowState founder evaluating B2C → B2B enterprise pivot',
  },

  nodes: [
    {
      id: 'node_founder_alex',
      type: 'person',
      label: 'Alex Rivera — Co-Founder & CEO',
      veracity: 'fact',
      confidence: 1.0,
      source: 'user_input',
      citations: [
        {
          nodeId: 'node_founder_alex',
          label: 'Founder intake interview',
          excerpt:
            'Led GTM strategy and raised $1.2M seed from Horizon Ventures in March 2025.',
        },
      ],
      hasGap: false,
      hasContradiction: false,
      summaryText:
        'Former Stripe PM. Owns fundraising, positioning, and the pivot decision.',
    },
    {
      id: 'node_cto_maya',
      type: 'person',
      label: 'Maya Chen — Co-Founder & CTO',
      veracity: 'fact',
      confidence: 1.0,
      source: 'user_input',
      citations: [
        {
          nodeId: 'node_cto_maya',
          label: 'Founder intake interview',
          excerpt:
            'Built the original FlowState mobile stack; skeptical of premature enterprise complexity.',
        },
      ],
      hasGap: false,
      hasContradiction: false,
      summaryText:
        'Ex-Notion infra engineer. Controls architecture trade-offs for any B2B SSO/RBAC work.',
    },
    {
      id: 'node_decision_b2c_launch',
      type: 'decision',
      label: 'Launched B2C App "FlowState" (Jan 2025)',
      veracity: 'fact',
      confidence: 1.0,
      source: 'document_ingest',
      citations: [
        {
          nodeId: 'node_decision_b2c_launch',
          label: 'App Store launch record',
          url: 'https://apps.apple.com/app/flowstate',
          excerpt: 'Version 1.0 shipped January 14, 2025.',
        },
      ],
      hasGap: false,
      hasContradiction: false,
      summaryText:
        'Bet on viral productivity loops for individual knowledge workers instead of team sales.',
    },
    {
      id: 'node_project_flowstate_mobile',
      type: 'project',
      label: 'FlowState Mobile (iOS & Android)',
      veracity: 'fact',
      confidence: 0.97,
      source: 'document_ingest',
      citations: [
        {
          nodeId: 'node_project_flowstate_mobile',
          label: 'GitHub release tags',
          excerpt: '247 commits across v1.0–v2.3 between Jan–Jun 2026.',
        },
      ],
      hasGap: false,
      hasContradiction: false,
      summaryText:
        'Core product surface: habit tracking, focus timers, and AI daily planning for individuals.',
    },
    {
      id: 'node_outcome_50k_mau',
      type: 'outcome',
      label: 'Reached 50K MAU via Organic + Paid Social',
      veracity: 'fact',
      confidence: 0.94,
      source: 'external_api',
      citations: [
        {
          nodeId: 'node_outcome_50k_mau',
          label: 'Mixpanel dashboard export',
          excerpt: '50,412 MAU peak in May 2026; 62% iOS, 38% Android.',
        },
      ],
      hasGap: false,
      hasContradiction: false,
      summaryText:
        'Growth looked healthy on the surface but masked deteriorating paid channel efficiency.',
    },
    {
      id: 'node_outcome_cac_ltv_gap',
      type: 'outcome',
      label: 'Unit Economics Failed: CAC 3.2× LTV',
      veracity: 'fact',
      confidence: 0.91,
      source: 'document_ingest',
      citations: [
        {
          nodeId: 'node_outcome_cac_ltv_gap',
          label: 'Q2 2026 board deck',
          excerpt: 'Blended CAC $47 vs. 12-month LTV $14.70 across paid channels.',
        },
      ],
      hasGap: false,
      hasContradiction: false,
      summaryText:
        'Primary trigger for strategic reassessment. B2C monetization could not sustain paid acquisition.',
    },
    {
      id: 'node_outcome_enterprise_leads',
      type: 'outcome',
      label: '4 Fortune-500 Inbound Demos (Never Assigned)',
      veracity: 'inference',
      confidence: 0.68,
      source: 'agent_inference',
      citations: [
        {
          nodeId: 'node_outcome_enterprise_leads',
          label: 'Support inbox scan',
          excerpt:
            'Emails from Deloitte, Siemens, and two anonymized @fortune500 domains requesting team pricing.',
        },
      ],
      hasGap: true,
      hasContradiction: false,
      summaryText:
        'Inbound interest detected but no CRM records, call notes, or loss reasons exist. Demand signal strength is unknown.',
    },
    {
      id: 'node_skill_enterprise_sales',
      type: 'skill',
      label: 'Enterprise Sales Motion (Nascent)',
      veracity: 'inference',
      confidence: 0.55,
      source: 'agent_inference',
      citations: [
        {
          nodeId: 'node_skill_enterprise_sales',
          label: 'Team skills self-assessment',
          excerpt:
            'No dedicated AE, no MEDDIC playbook, no security questionnaire template on file.',
        },
      ],
      hasGap: true,
      hasContradiction: false,
      summaryText:
        'Critical capability gap for B2B pivot. Chronos cannot verify whether founders can close six-figure contracts.',
    },
    {
      id: 'node_decision_pivot_eval',
      type: 'decision',
      label: 'Formal B2B Pivot Evaluation (Q3 2026)',
      veracity: 'fact',
      confidence: 1.0,
      source: 'user_input',
      citations: [
        {
          nodeId: 'node_decision_pivot_eval',
          label: 'Founder decision log',
          excerpt:
            'Explicit go/no-go review scheduled for September 2026 with board observers.',
        },
      ],
      hasGap: false,
      hasContradiction: false,
      summaryText:
        'The present decision point. All simulated timelines branch from this evaluation.',
    },
    {
      id: 'node_outcome_runway',
      type: 'outcome',
      label: '$1.2M Raised — 14 Months Runway Remaining',
      veracity: 'fact',
      confidence: 0.96,
      source: 'document_ingest',
      citations: [
        {
          nodeId: 'node_outcome_runway',
          label: 'Burn rate model (Jul 2026)',
          excerpt: '$86K net burn/month at current headcount of 8 FTE.',
        },
      ],
      hasGap: false,
      hasContradiction: false,
      summaryText:
        'Runway is the binding constraint. Enterprise sales cycles may consume 6–9 months before first revenue.',
    },
    {
      id: 'node_outcome_growth_contradiction',
      type: 'outcome',
      label: 'Conflicting Retention Reports (D30: 18% vs. 34%)',
      veracity: 'inference',
      confidence: 0.72,
      source: 'agent_inference',
      citations: [
        {
          nodeId: 'node_outcome_growth_contradiction',
          label: 'Mixpanel vs. investor update',
          excerpt:
            'Board deck cites 34% D30 retention; raw Mixpanel cohort export shows 18.1%.',
        },
        {
          nodeId: 'node_outcome_50k_mau',
          label: 'Cross-reference: MAU growth',
          excerpt: 'MAU growth rate assumptions depend on which retention figure is accurate.',
        },
      ],
      hasGap: false,
      hasContradiction: true,
      summaryText:
        'Material contradiction undermines confidence in the Stay B2C branch. UI should flag for founder clarification.',
    },
    {
      id: 'node_project_enterprise_pilot',
      type: 'project',
      label: 'Chronos Enterprise Pilot (Proposed)',
      veracity: 'prediction',
      confidence: 0.61,
      source: 'agent_inference',
      citations: [
        {
          nodeId: 'node_project_enterprise_pilot',
          label: 'Simulation draft spec',
          excerpt:
            'SSO, admin console, usage analytics, and SOC 2 readiness roadmap for 3 design partners.',
        },
      ],
      hasGap: false,
      hasContradiction: false,
      summaryText:
        'Projected artifact if pivot proceeds. Estimated 4-month eng lift before first paid pilot.',
    },
  ],

  edges: [
    {
      id: 'edge_alex_b2c_launch',
      source: 'node_founder_alex',
      target: 'node_decision_b2c_launch',
      type: 'contributory',
      confidence: 0.95,
      veracity: 'fact',
      label: 'authored strategy',
    },
    {
      id: 'edge_maya_mobile',
      source: 'node_cto_maya',
      target: 'node_project_flowstate_mobile',
      type: 'contributory',
      confidence: 0.98,
      veracity: 'fact',
      label: 'built product',
    },
    {
      id: 'edge_launch_mobile',
      source: 'node_decision_b2c_launch',
      target: 'node_project_flowstate_mobile',
      type: 'temporal',
      confidence: 1.0,
      veracity: 'fact',
      label: 'followed by',
    },
    {
      id: 'edge_mobile_mau',
      source: 'node_project_flowstate_mobile',
      target: 'node_outcome_50k_mau',
      type: 'causal',
      confidence: 0.89,
      veracity: 'inference',
      label: 'drove growth',
    },
    {
      id: 'edge_mau_cac',
      source: 'node_outcome_50k_mau',
      target: 'node_outcome_cac_ltv_gap',
      type: 'causal',
      confidence: 0.87,
      veracity: 'inference',
      label: 'exposed weakness',
    },
    {
      id: 'edge_mobile_leads',
      source: 'node_project_flowstate_mobile',
      target: 'node_outcome_enterprise_leads',
      type: 'contributory',
      confidence: 0.64,
      veracity: 'inference',
      label: 'attracted inbound',
    },
    {
      id: 'edge_leads_pivot',
      source: 'node_outcome_enterprise_leads',
      target: 'node_decision_pivot_eval',
      type: 'causal',
      confidence: 0.71,
      veracity: 'inference',
      label: 'triggered review',
    },
    {
      id: 'edge_cac_pivot',
      source: 'node_outcome_cac_ltv_gap',
      target: 'node_decision_pivot_eval',
      type: 'causal',
      confidence: 0.93,
      veracity: 'fact',
      label: 'forced reassessment',
    },
    {
      id: 'edge_alex_pivot',
      source: 'node_founder_alex',
      target: 'node_decision_pivot_eval',
      type: 'contributory',
      confidence: 0.97,
      veracity: 'fact',
      label: 'owns decision',
    },
    {
      id: 'edge_runway_pivot',
      source: 'node_outcome_runway',
      target: 'node_decision_pivot_eval',
      type: 'contributory',
      confidence: 0.94,
      veracity: 'fact',
      label: 'constrains options',
    },
    {
      id: 'edge_contradiction_pivot',
      source: 'node_outcome_growth_contradiction',
      target: 'node_decision_pivot_eval',
      type: 'contributory',
      confidence: 0.76,
      veracity: 'inference',
      label: 'adds uncertainty',
    },
    {
      id: 'edge_skill_pilot',
      source: 'node_skill_enterprise_sales',
      target: 'node_project_enterprise_pilot',
      type: 'contributory',
      confidence: 0.58,
      veracity: 'prediction',
      label: 'capability prerequisite',
    },
    {
      id: 'edge_pivot_pilot',
      source: 'node_decision_pivot_eval',
      target: 'node_project_enterprise_pilot',
      type: 'temporal',
      confidence: 0.65,
      veracity: 'prediction',
      label: 'may initiate',
    },
    {
      id: 'edge_maya_pilot',
      source: 'node_cto_maya',
      target: 'node_project_enterprise_pilot',
      type: 'contributory',
      confidence: 0.82,
      veracity: 'prediction',
      label: 'would lead eng',
    },
    {
      id: 'edge_runway_pilot',
      source: 'node_outcome_runway',
      target: 'node_project_enterprise_pilot',
      type: 'causal',
      confidence: 0.88,
      veracity: 'inference',
      label: 'funds or blocks',
    },
  ],
} satisfies GraphPayload;
