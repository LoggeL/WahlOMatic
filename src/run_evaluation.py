"""Main evaluation runner for LLM evaluation."""
import json
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from tqdm import tqdm

from .data_loader import DataLoader
from .openrouter_client import OpenRouterClient
from .prompts import create_statement_prompt, parse_llm_response
from .evaluator import calculate_party_scores


def evaluate_single_statement(
    statement: Dict[str, Any],
    client: OpenRouterClient,
    statement_index: int,
    total_statements: int
) -> Dict[str, Any]:
    """
    Evaluate a single statement with an LLM.
    
    Args:
        statement: Statement dictionary
        client: OpenRouterClient instance
        statement_index: Index of statement (for progress tracking)
        total_statements: Total number of statements
        
    Returns:
        Dictionary with statement_id, text, answer, and reasoning
    """
    prompt = create_statement_prompt(statement)
    
    try:
        response = client.get_completion(prompt)
        answer_id, reasoning = parse_llm_response(response)
    except Exception as e:
        # If parsing fails, default to neutral
        print(f"Warning: Failed to parse response for statement {statement['id']}: {e}")
        answer_id = 2
        reasoning = f"Error: {str(e)}"
    
    return {
        'statement_id': statement['id'],
        'text': statement['text'],
        'label': statement.get('label', ''),
        'answer': answer_id,
        'reasoning': reasoning
    }


def run_single_evaluation(
    run_id: int,
    model_name: str,
    data_loader: DataLoader,
    client: OpenRouterClient,
    election_slug: str
) -> Dict[str, Any]:
    """
    Run a single evaluation pass.
    
    Args:
        run_id: Run identifier (1-5)
        model_name: Name of the model being evaluated
        data_loader: DataLoader instance
        client: OpenRouterClient instance
        election_slug: Election identifier
        
    Returns:
        Complete evaluation result dictionary
    """
    questions = []
    llm_answers = []
    
    # Process all statements with progress bar
    with tqdm(
        total=len(data_loader.statements),
        desc=f"Run {run_id}",
        position=run_id - 1,
        leave=True
    ) as pbar:
        for statement in data_loader.statements:
            result = evaluate_single_statement(
                statement,
                client,
                statement['id'],
                len(data_loader.statements)
            )
            questions.append(result)
            llm_answers.append(result['answer'])
            pbar.update(1)
    
    # Calculate party scores
    party_scores = calculate_party_scores(llm_answers, data_loader)
    
    # Build result dictionary
    result = {
        'model': model_name,
        'election': election_slug,
        'timestamp': datetime.now().isoformat(),
        'run_id': run_id,
        'questions': questions,
        'party_scores': party_scores
    }
    
    return result


def save_result(result: Dict[str, Any], output_dir: Path):
    """
    Save evaluation result to JSON file.
    
    Args:
        result: Evaluation result dictionary
        output_dir: Directory to save results
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename: model_name_timestamp_runid.json
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{result['model'].replace('/', '_')}_{timestamp}_run{result['run_id']}.json"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return filepath


def run_evaluation(
    model_name: str,
    data_path: str,
    results_path: str,
    election_slug: str = "bundestagswahl2025",
    num_runs: int = 5
) -> List[Dict[str, Any]]:
    """
    Run evaluation with multiple parallel runs.
    
    Args:
        model_name: Model name (e.g., "openai/gpt-4o")
        data_path: Path to WahlOMat data directory
        results_path: Path to results directory
        election_slug: Election identifier
        num_runs: Number of parallel runs (default: 5)
        
    Returns:
        List of evaluation result dictionaries
    """
    # Load data
    print(f"Loading WahlOMat data from {data_path}...")
    data_loader = DataLoader(data_path)
    data_loader.load_all()
    print(f"Loaded {len(data_loader.statements)} statements and {len(data_loader.parties)} parties")
    
    # Initialize client
    client = OpenRouterClient(model=model_name)
    print(f"Using model: {model_name}")
    
    # Prepare output directory
    output_dir = Path(results_path) / election_slug
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run evaluations in parallel
    print(f"\nRunning {num_runs} parallel evaluations...")
    results = []
    
    with ThreadPoolExecutor(max_workers=num_runs) as executor:
        futures = {
            executor.submit(
                run_single_evaluation,
                run_id,
                model_name,
                data_loader,
                OpenRouterClient(model=model_name),  # Create new client for each thread
                election_slug
            ): run_id
            for run_id in range(1, num_runs + 1)
        }
        
        for future in as_completed(futures):
            run_id = futures[future]
            try:
                result = future.result()
                results.append(result)
                
                # Save result immediately
                filepath = save_result(result, output_dir)
                print(f"\nRun {run_id} completed. Saved to {filepath}")
            except Exception as e:
                print(f"\nError in run {run_id}: {e}")
    
    # Sort results by run_id
    results.sort(key=lambda x: x['run_id'])
    
    print(f"\nEvaluation complete! {len(results)} runs completed.")
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run LLM evaluation against WahlOMat")
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Model name (e.g., 'openai/gpt-4o')"
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default="data/2025/deutschland",
        help="Path to WahlOMat data directory"
    )
    parser.add_argument(
        "--results-path",
        type=str,
        default="results",
        help="Path to results directory"
    )
    parser.add_argument(
        "--election",
        type=str,
        default="bundestagswahl2025",
        help="Election slug"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of parallel runs"
    )
    
    args = parser.parse_args()
    
    run_evaluation(
        model_name=args.model,
        data_path=args.data_path,
        results_path=args.results_path,
        election_slug=args.election,
        num_runs=args.runs
    )

