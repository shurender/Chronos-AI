"""
Chronos safety policy: the guardrails the product commits to, plus helpers for
high-stakes decision handling (conservative confidence + professional-advice
warnings).
"""

from __future__ import annotations

from .safety_schema import SafetyLabel

# Product policy statements (surfaced via GET /safety/policy).
POLICY_STATEMENTS = [
    "Chronos explores plausible futures; it makes no deterministic claim of future certainty.",
    "Evidence-based claims must be grounded in the evidence snapshot — no unsupported market claims.",
    "Demo evidence is clearly labelled and never presented as live web data.",
    "High-stakes decisions carry a professional-advice warning and use conservative confidence.",
    "Ingested text is PII/secret-redacted before storage unless STORE_RAW_UNREDACTED=true.",
]

# Decision types treated as high-stakes (financial / life-critical).
HIGH_STAKES_TYPES = {"Financial", "Life"}
# Confidence multiplier applied to high-stakes branches (conservative).
HIGH_STAKES_CONFIDENCE_FACTOR = 0.85

_GENERAL_DISCLAIMER = (
    "This is a structured heuristic exploration of plausible futures — not a guaranteed "
    "prediction, and not medical, legal, or financial advice."
)


def build_safety_label(decision_type: str) -> SafetyLabel:
    high = decision_type in HIGH_STAKES_TYPES
    warning = None
    if high:
        warning = (
            f"'{decision_type}' is a high-stakes decision. Treat these projections as a thinking aid only, "
            "not professional advice — consult a licensed professional before acting."
        )
    return SafetyLabel(
        disclaimer=_GENERAL_DISCLAIMER,
        high_stakes=high,
        category=decision_type,
        professional_advice_warning=warning,
    )
