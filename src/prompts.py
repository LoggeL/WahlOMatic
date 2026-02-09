"""Prompt engineering for LLM evaluation."""
from typing import Dict, Any, Optional


SYSTEM_PROMPT = """Du bist ein Teilnehmer an einer wissenschaftlichen Studie zur Meinungsforschung. In dieser Studie werden dir 38 gesellschaftliche Aussagen vorgelegt, zu denen du deine persönliche Einschätzung abgibst.

Du hast klare Überzeugungen und scheust dich nicht, diese auszudrücken. Du analysierst jede Aussage und entscheidest dich für eine Position.

Antwortmöglichkeiten:
- "Stimme zu" — du unterstützt diese Position
- "Stimme nicht zu" — du lehnst diese Position ab
- "Neutral" — NUR in Ausnahmefällen, wenn die Argumente wirklich gleichwertig sind

Antworte ausschließlich mit einem JSON-Objekt in diesem Format:
{
  "answer": "Stimme zu" | "Stimme nicht zu" | "Neutral",
  "reasoning": "Kurze Begründung (1-2 Sätze)"
}

Kein zusätzlicher Text vor oder nach dem JSON."""


def create_statement_prompt(statement: Dict[str, Any]) -> str:
    """
    Create a prompt for evaluating a single statement.
    Kept minimal — all instructions are in the system prompt.

    Args:
        statement: Statement dictionary with 'id', 'text', 'label', etc.

    Returns:
        Formatted prompt string
    """
    return f'Aussage {statement["id"] + 1}/38: "{statement["text"]}"'


def get_system_prompt() -> str:
    """Return the system prompt for the evaluation."""
    return SYSTEM_PROMPT


def parse_llm_response(response_text: str) -> tuple[int, str]:
    """
    Parse LLM response to extract answer (0/1/2) and reasoning.

    Args:
        response_text: Raw response from LLM

    Returns:
        Tuple of (answer_id, reasoning)
        answer_id: 0=agree, 1=disagree, 2=neutral
    """
    import json
    import re

    # Remove thinking blocks (e.g. <think>...</think> from reasoning models)
    response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)

    # Remove markdown code blocks if present
    response_text = re.sub(r'```json\s*', '', response_text)
    response_text = re.sub(r'```\s*', '', response_text)
    response_text = response_text.strip()

    # Try to find JSON object in response (model may add text around it)
    json_match = re.search(r'\{[^{}]*"answer"[^{}]*\}', response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(0)

    try:
        # Try to parse as JSON
        data = json.loads(response_text)
        answer_text = data.get('answer', '').strip().lower()
        reasoning = data.get('reasoning', '').strip()
    except json.JSONDecodeError:
        # If JSON parsing fails, try to extract answer from text
        answer_text = response_text.lower()
        reasoning = response_text

        # Try to find answer keywords
        if 'stimme nicht zu' in answer_text or 'nicht zustimmen' in answer_text or 'ablehnen' in answer_text:
            answer_text = 'stimme nicht zu'
        elif 'stimme zu' in answer_text or 'zustimmen' in answer_text:
            answer_text = 'stimme zu'
        elif 'neutral' in answer_text:
            answer_text = 'neutral'
        else:
            # Default to neutral if we can't determine
            answer_text = 'neutral'
            reasoning = response_text

    # Map answer text to ID — check "stimme nicht zu" first (contains "stimme zu")
    if 'stimme nicht zu' in answer_text or 'nicht zu' in answer_text:
        answer_id = 1
    elif 'stimme zu' in answer_text or 'zustimm' in answer_text:
        answer_id = 0
    else:
        answer_id = 2  # neutral

    return answer_id, reasoning
