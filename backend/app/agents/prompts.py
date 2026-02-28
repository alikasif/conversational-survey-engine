"""System prompts and prompt builders for the generator agent."""

from typing import List, Tuple

GENERATOR_SYSTEM_PROMPT = """You are an expert survey researcher and conversational interviewer.

Your role is to generate exactly ONE focused, open-ended survey question based on the provided context, goal, and conversation history.

Rules:
1. Generate exactly ONE question — never multiple questions.
2. Do NOT ask compound questions (no "and" joining two separate inquiries).
3. Do NOT ask leading questions that suggest a particular answer.
4. Stay strictly within the survey context — do not drift to unrelated topics.
5. Build on previous answers to go deeper, but do not repeat questions already asked.
6. Keep questions conversational and natural.
7. If constraints are provided, respect them absolutely.
8. Return ONLY the question text — no numbering, no prefixes, no explanation.
"""


def build_generator_prompt(
    survey_context: str,
    goal: str,
    constraints: List[str],
    conversation_history: List[Tuple[str, str]],
    rejection_feedback: str = "",
) -> str:
    """Build the full prompt for the generator agent.

    Args:
        survey_context: The survey's background context.
        goal: The research goal.
        constraints: List of constraint strings.
        conversation_history: List of (question, answer) tuples.
        rejection_feedback: Optional feedback from validator on why the previous
            question was rejected.

    Returns:
        The formatted prompt string.
    """
    parts = []

    parts.append(f"## Survey Context\n{survey_context}")
    parts.append(f"## Research Goal\n{goal}")

    if constraints:
        constraints_text = "\n".join(f"- {c}" for c in constraints)
        parts.append(f"## Constraints\n{constraints_text}")

    if conversation_history:
        history_text = ""
        for i, (q, a) in enumerate(conversation_history, 1):
            history_text += f"Q{i}: {q}\nA{i}: {a}\n\n"
        parts.append(f"## Conversation So Far\n{history_text.strip()}")
    else:
        parts.append("## Conversation So Far\nThis is the first question. Start by exploring the main topic.")

    if rejection_feedback:
        parts.append(
            f"## Important: Previous Question Rejected\n"
            f"Your previous question was rejected for this reason: {rejection_feedback}\n"
            f"Generate a different question that avoids this issue."
        )

    parts.append("## Task\nGenerate exactly one focused survey question.")

    return "\n\n".join(parts)
