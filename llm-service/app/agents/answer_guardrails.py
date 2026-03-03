"""Answer guardrails — gibberish detection and injection pre-filter."""

import json
import re
from dataclasses import dataclass, field

CHAR_REPEAT_RE = re.compile(r"^(.)\1{9,}$")
NON_ALPHA_RE = re.compile(r"^[^a-zA-Z0-9]+$")

INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\[/?INST\]",
        r"<\|im_(start|end)\|>",
        r"<</?SYS>>",
        r"^SYSTEM:",
        r"ignore\s+(all\s+|your\s+|the\s+)?(previous\s+|prior\s+|above\s+)?instructions",
        r"reveal\s+(your\s+|the\s+)?(system\s+|internal\s+)?prompt",
        r"you\s+are\s+now",
        r"act\s+as\s+if",
        r"pretend\s+you\s+are",
        r"what\s+(are|is)\s+your\s+(system\s+|original\s+)?prompt",
        r"repeat\s+(your\s+|the\s+|back\s+)?(system\s+)?prompt",
    ]
]


@dataclass
class GuardrailResult:
    """Result of running answer guardrails."""

    is_flagged: bool = False
    flags: list[str] = field(default_factory=list)
    rejection_hint: str | None = None


def check_answer(answer: str) -> GuardrailResult:
    """Run all guardrail checks on *answer* and return a result."""
    stripped = answer.strip()
    flags: list[str] = []
    hint: str | None = None

    if CHAR_REPEAT_RE.match(stripped):
        flags.append("char_repeat")
        hint = (
            "The participant's last answer was unclear. "
            "Please ask a clarifying question about the same topic."
        )

    if NON_ALPHA_RE.match(stripped):
        flags.append("no_alphanumeric")
        hint = (
            "The participant's last answer was unclear. "
            "Please ask a clarifying question about the same topic."
        )

    for pattern in INJECTION_PATTERNS:
        if pattern.search(stripped):
            flags.append("injection_attempt")
            break

    return GuardrailResult(is_flagged=len(flags) > 0, flags=flags, rejection_hint=hint)


def flags_to_json(flags: list[str]) -> str | None:
    """Serialize *flags* to a JSON string, or ``None`` if empty."""
    return json.dumps(flags) if flags else None
