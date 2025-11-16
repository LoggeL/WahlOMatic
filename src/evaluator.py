"""Evaluation engine for calculating agreement scores."""
from typing import List, Dict, Any
from .data_loader import DataLoader


def calculate_agreement_score(llm_answer: int, party_answer: int) -> int:
    """
    Calculate agreement score (0-2) based on answer difference.
    
    Scoring:
    - 2 points: Same answer (difference = 0)
    - 1 point: Difference of 1 step (neutral vs yes/no, or yes/no vs neutral)
    - 0 points: Difference of 2 steps (yes vs no, or no vs yes)
    
    Args:
        llm_answer: LLM's answer (0=agree, 1=disagree, 2=neutral)
        party_answer: Party's answer (0=agree, 1=disagree, 2=neutral)
        
    Returns:
        Agreement score (0, 1, or 2)
    """
    if llm_answer == party_answer:
        return 2
    
    # Calculate absolute difference
    diff = abs(llm_answer - party_answer)
    
    if diff == 1:
        return 1  # One step difference (neutral vs yes/no)
    elif diff == 2:
        return 0  # Two steps difference (yes vs no)
    
    # Should not reach here, but handle edge case
    return 0


def calculate_party_scores(
    llm_answers: List[int],
    data_loader: DataLoader
) -> List[Dict[str, Any]]:
    """
    Calculate agreement scores for all parties.
    
    Args:
        llm_answers: List of LLM answers (one per statement, in order)
        data_loader: DataLoader instance with loaded data
        
    Returns:
        List of party scores with party_id, party_name, and score (0-100)
    """
    if len(llm_answers) != len(data_loader.statements):
        raise ValueError(
            f"Number of LLM answers ({len(llm_answers)}) "
            f"does not match number of statements ({len(data_loader.statements)})"
        )
    
    party_scores = []
    total_statements = len(data_loader.statements)
    
    for party in data_loader.parties:
        party_id = party['id']
        total_score = 0
        
        for statement_id, llm_answer in enumerate(llm_answers):
            party_answer = data_loader.get_party_opinion(party_id, statement_id)
            agreement_score = calculate_agreement_score(llm_answer, party_answer)
            total_score += agreement_score
        
        # Calculate percentage: (sum / (total * 2)) * 100
        percentage_score = (total_score / (total_statements * 2)) * 100
        
        party_scores.append({
            'party_id': party_id,
            'party_name': party['name'],
            'party_longname': party['longname'],
            'score': round(percentage_score, 2)
        })
    
    # Sort by score descending
    party_scores.sort(key=lambda x: x['score'], reverse=True)
    
    return party_scores


