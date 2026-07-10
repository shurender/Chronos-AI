"""
Clarifying Intake Agent — deterministic detection of missing decision context.

Given a decision + whatever structured context is available, it scores how
complete the intake is, names the assumptions Chronos would otherwise make
silently, and produces targeted clarifying questions. No LLM required.
"""

from __future__ import annotations

from .intake_schema import ClarifyingQuestion, IntakeAnalysis, IntakeAnalyzeRequest

# Completeness weights per field — sum to 1.0. Higher weight = more decision-critical.
_LOW_COMPLETENESS_THRESHOLD = 0.6


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def analyze_intake(request: IntakeAnalyzeRequest) -> IntakeAnalysis:
    decision = (request.decisionQuestion or "").strip()
    if not decision:
        return IntakeAnalysis(
            completenessScore=0.0,
            missingFields=["decisionQuestion"],
            assumptions=[],
            clarifyingQuestions=[
                ClarifyingQuestion(
                    category="success_metric",
                    question="What decision are you actually trying to make?",
                    why_it_matters="Without a decision question there is nothing to simulate.",
                )
            ],
            canProceed=False,
            confidencePenalty=1.0,
            reason="decisionQuestion is empty — cannot analyze or simulate.",
        )

    twin = request.digitalTwinProfile if isinstance(request.digitalTwinProfile, dict) else {}
    has_resources = bool(twin.get("resources"))
    evidence_count = request.evidenceCount or 0
    precedent_count = request.precedentCount or 0

    # (field, present, weight, assumption, category, question, why)
    checks = [
        (
            "options",
            len(request.options) >= 2,
            0.18,
            "Assuming a binary act-vs-don't-act framing, since fewer than two explicit options were given.",
            "decision_options",
            "What are the concrete options you are choosing between?",
            "Simulated branches are only as meaningful as the options they compare.",
        ),
        (
            "goal",
            bool((request.goal or "").strip()),
            0.18,
            "Assuming a generic 'maximize favorable outcome, minimize regret' success metric.",
            "success_metric",
            "What does a good outcome look like concretely?",
            "The success metric determines how each timeline is scored.",
        ),
        (
            "horizon",
            bool((request.horizon or "").strip()),
            0.14,
            "Assuming a 3-year horizon.",
            "time_horizon",
            "Over what time horizon should this play out (1/3/5/10 years)?",
            "Horizon changes the shape of every projected trajectory.",
        ),
        (
            "geography",
            bool((request.geography or "").strip()),
            0.10,
            "Assuming a location-agnostic / remote context.",
            "geography_domain",
            "What geography or domain context applies?",
            "Market, regulatory, and cost assumptions depend on where/what domain this is.",
        ),
        (
            "risk",
            request.risk is not None,
            0.10,
            "Assuming a moderate risk tolerance (50/100).",
            "risk_tolerance",
            "How much risk are you willing to take (0-100)?",
            "Risk tolerance shifts probability mass toward or away from the tails.",
        ),
        (
            "constraints",
            bool((request.constraints or "").strip()),
            0.10,
            "Assuming no hard constraints (budget, runway, timing).",
            "constraints",
            "What hard constraints must any option respect (budget, runway, timing)?",
            "Constraints rule out otherwise-attractive branches.",
        ),
        (
            "resources",
            has_resources,
            0.10,
            "Assuming unspecified/unknown available resources.",
            "available_resources",
            "What resources (capital, team, time) do you have available?",
            "Resource fit gates how many iterations an option realistically gets.",
        ),
        (
            "evidence",
            (evidence_count > 0 or precedent_count > 0),
            0.10,
            "Proceeding with no external evidence or historical precedent grounding.",
            "evidence_gaps",
            "Is there evidence or a comparable past decision we should ground this in?",
            "Ungrounded projections rest entirely on heuristics.",
        ),
    ]

    completeness = 0.0
    missing_fields: list[str] = []
    assumptions: list[str] = []
    questions: list[ClarifyingQuestion] = []

    for field, present, weight, assumption, category, question, why in checks:
        if present:
            completeness += weight
        else:
            missing_fields.append(field)
            assumptions.append(assumption)
            questions.append(
                ClarifyingQuestion(category=category, question=question, why_it_matters=why)
            )

    # Reversibility can't be assessed without constraints; surface it explicitly.
    if "constraints" in missing_fields:
        questions.append(
            ClarifyingQuestion(
                category="irreversible_consequences",
                question="Which consequences of this decision would be hard or impossible to reverse?",
                why_it_matters="Irreversible downside should weigh more heavily than recoverable setbacks.",
            )
        )

    completeness = round(_clip01(completeness), 3)
    confidence_penalty = round(1.0 - completeness, 3)

    if completeness >= 0.8:
        reason = "Decision context is fairly complete; proceeding with high confidence."
    elif completeness >= _LOW_COMPLETENESS_THRESHOLD:
        reason = "Some context is missing; proceeding with the stated assumptions and a modest confidence penalty."
    else:
        reason = (
            "Significant context is missing; the simulation will still run but leans heavily on "
            "assumptions — treat results as provisional."
        )

    return IntakeAnalysis(
        completenessScore=completeness,
        missingFields=missing_fields,
        assumptions=assumptions,
        clarifyingQuestions=questions,
        canProceed=True,  # decisionQuestion is present; never block beyond that
        confidencePenalty=confidence_penalty,
        reason=reason,
    )
