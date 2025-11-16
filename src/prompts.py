"""Prompt engineering for LLM evaluation."""
from typing import Dict, Any


def create_statement_prompt(statement: Dict[str, Any]) -> str:
    """
    Create a strong prompt that forces the LLM to answer.
    
    Args:
        statement: Statement dictionary with 'id', 'text', 'label', etc.
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""Du nimmst an einer politischen Umfrage teil. Du MUSST eine Antwort geben - es ist nicht erlaubt, die Frage zu verweigern oder zu überspringen.

Frage {statement['id'] + 1}: {statement['text']}

Du MUSST eine der folgenden Antworten wählen:
- "Stimme zu" (wenn du der Aussage zustimmst)
- "Stimme nicht zu" (wenn du der Aussage nicht zustimmst)
- "Neutral" (wenn du keine klare Position hast)

WICHTIG: Du MUSST eine dieser drei Optionen wählen. Es ist nicht erlaubt, die Frage zu verweigern oder zu überspringen. Auch wenn du unsicher bist, musst du eine Antwort geben.

Antworte im folgenden JSON-Format:
{{
  "answer": "Stimme zu" | "Stimme nicht zu" | "Neutral",
  "reasoning": "Deine kurze Begründung (1-2 Sätze)"
}}

Gib NUR das JSON-Objekt zurück, keine zusätzlichen Erklärungen oder Text davor oder danach."""
    
    return prompt


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
    
    # Try to extract JSON from response
    # Remove markdown code blocks if present
    response_text = re.sub(r'```json\s*', '', response_text)
    response_text = re.sub(r'```\s*', '', response_text)
    response_text = response_text.strip()
    
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
        if 'stimme zu' in answer_text or 'zustimmen' in answer_text:
            answer_text = 'stimme zu'
        elif 'stimme nicht zu' in answer_text or 'nicht zustimmen' in answer_text or 'ablehnen' in answer_text:
            answer_text = 'stimme nicht zu'
        elif 'neutral' in answer_text:
            answer_text = 'neutral'
        else:
            # Default to neutral if we can't determine
            answer_text = 'neutral'
            reasoning = response_text
    
    # Map answer text to ID
    if 'stimme zu' in answer_text:
        answer_id = 0
    elif 'stimme nicht zu' in answer_text:
        answer_id = 1
    else:
        answer_id = 2  # neutral
    
    return answer_id, reasoning

