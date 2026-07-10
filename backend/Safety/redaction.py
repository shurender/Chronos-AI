"""
PII / secret redaction.

Detects and redacts emails, phone numbers, API keys/secret-prefixed tokens,
private keys, and obvious street addresses. Deterministic, no network, and — by
design — never logs the raw matched values.
"""

from __future__ import annotations

import re

_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----"
)
# Secret/token prefixes: OpenAI, Groq, GitHub (PAT/OAuth), GitLab, Slack, AWS,
# Google, Stripe, Shopify.
_SECRET_RE = re.compile(
    r"\b(?:sk-|gsk_|ghp_|gho_|ghs_|github_pat_|glpat-|xox[baprs]-|AKIA|ASIA|AIza|pk_live_|sk_live_|shpat_)"
    r"[A-Za-z0-9_\-]{8,}\b"
)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+(?:[A-Za-z0-9.'-]+\s){0,4}"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way)\b\.?",
    re.IGNORECASE,
)
# Phone-like: optional +, then 10+ digits allowing common separators.
_PHONE_RE = re.compile(r"(?<!\w)\+?\d(?:[\d\s().-]{8,})\d(?!\w)")


def _looks_like_phone(match: str) -> bool:
    return sum(c.isdigit() for c in match) >= 10


def redact(text: str) -> tuple[str, list[str], int]:
    """Return (redacted_text, sorted_categories_detected, redaction_count)."""
    if not text:
        return text, [], 0

    categories: set[str] = set()
    count = 0

    def _apply(pattern: re.Pattern, replacement: str, category: str, guard=None) -> None:
        nonlocal text, count

        def _sub(m: re.Match) -> str:
            nonlocal count
            if guard is not None and not guard(m.group(0)):
                return m.group(0)
            count += 1
            categories.add(category)
            return replacement

        text = pattern.sub(_sub, text)

    # Order matters: multi-line private keys and prefixed secrets first, then
    # emails, then addresses, then phone (with a digit-count guard) last.
    _apply(_PRIVATE_KEY_RE, "[redacted-private-key]", "private_key")
    _apply(_SECRET_RE, "[redacted-secret]", "api_key")
    _apply(_EMAIL_RE, "[redacted-email]", "email")
    _apply(_ADDRESS_RE, "[redacted-address]", "address")
    _apply(_PHONE_RE, "[redacted-phone]", "phone", guard=_looks_like_phone)

    return text, sorted(categories), count
