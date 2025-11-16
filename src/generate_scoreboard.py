"""Scoreboard generator for aggregating and displaying evaluation results."""
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .data_loader import DataLoader


def get_jinja_env() -> Environment:
    """Get Jinja2 environment for template rendering."""
    template_dir = Path(__file__).parent.parent / "templates"
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(['html', 'xml'])
    )


def load_all_results(results_dir: Path) -> List[Dict[str, Any]]:
    """
    Load all result JSON files from a directory.
    
    Args:
        results_dir: Directory containing result JSON files
        
    Returns:
        List of result dictionaries
    """
    results = []
    if not results_dir.exists():
        return results
    
    for filepath in results_dir.glob("*.json"):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                result = json.load(f)
                results.append(result)
        except Exception as e:
            print(f"Warning: Failed to load {filepath}: {e}")
    
    return results


def aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate results by model and calculate averages.
    
    Args:
        results: List of result dictionaries
        
    Returns:
        Aggregated data dictionary
    """
    # Group by model
    model_data = defaultdict(lambda: {
        'runs': [],
        'party_scores': defaultdict(list),  # party_id -> list of scores
        'avg_party_scores': {}  # party_id -> average score
    })
    
    for result in results:
        model = result['model']
        model_data[model]['runs'].append(result)
        
        # Collect party scores
        for party_score in result['party_scores']:
            party_id = party_score['party_id']
            model_data[model]['party_scores'][party_id].append(party_score['score'])
    
    # Calculate averages
    aggregated = {}
    for model, data in model_data.items():
        avg_scores = []
        for party_id, scores in data['party_scores'].items():
            avg_score = sum(scores) / len(scores)
            # Get party name from first run
            party_name = None
            party_longname = None
            if data['runs']:
                for ps in data['runs'][0]['party_scores']:
                    if ps['party_id'] == party_id:
                        party_name = ps['party_name']
                        party_longname = ps.get('party_longname', '')
                        break
            
            avg_scores.append({
                'party_id': party_id,
                'party_name': party_name,
                'party_longname': party_longname,
                'avg_score': round(avg_score, 2),
                'num_runs': len(scores)
            })
        
        # Sort by average score descending
        avg_scores.sort(key=lambda x: x['avg_score'], reverse=True)
        
        aggregated[model] = {
            'num_runs': len(data['runs']),
            'party_scores': avg_scores
        }
    
    return aggregated


def get_top_models_per_party(
    aggregated: Dict[str, Any],
    data_loader: DataLoader
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Get top models for each party.
    
    Args:
        aggregated: Aggregated results dictionary
        data_loader: DataLoader instance
        
    Returns:
        Dictionary mapping party_id to list of top models with scores
    """
    party_models = defaultdict(list)
    
    for model, data in aggregated.items():
        for party_score in data['party_scores']:
            party_id = party_score['party_id']
            party_models[party_id].append({
                'model': model,
                'score': party_score['avg_score']
            })
    
    # Sort by score descending for each party
    for party_id in party_models:
        party_models[party_id].sort(key=lambda x: x['score'], reverse=True)
    
    return dict(party_models)


def generate_scoreboard_html(
    aggregated: Dict[str, Any],
    top_models_per_party: Dict[int, List[Dict[str, Any]]],
    data_loader: DataLoader,
    election_slug: str,
    election_info: Dict[str, Any]
) -> str:
    """
    Generate HTML scoreboard page.
    
    Args:
        aggregated: Aggregated results dictionary
        top_models_per_party: Top models per party dictionary
        data_loader: DataLoader instance
        election_slug: Election identifier
        election_info: Election overview information
        
    Returns:
        HTML string
    """
    models = list(aggregated.keys())
    parties = data_loader.parties
    
    # Calculate average approval per party across all models
    party_avg_scores = {}
    for party in parties:
        party_id = party['id']
        scores = []
        for model, data in aggregated.items():
            for ps in data['party_scores']:
                if ps['party_id'] == party_id:
                    scores.append(ps['avg_score'])
                    break
        party_avg_scores[party_id] = sum(scores) / len(scores) if scores else 0
    
    # Sort parties by average approval (highest first)
    parties_sorted = sorted(parties, key=lambda p: party_avg_scores[p['id']], reverse=True)
    
    # Define main parties (SPD, CDU/CSU, GRÜNE, FDP, AfD, Die Linke, BSW)
    main_party_ids = {0, 1, 2, 3, 4, 5, 25}  # Based on 2025 party.json
    
    # Create score lookups for each model
    score_lookups = {}
    for model in models:
        data = aggregated[model]
        score_lookups[model] = {ps['party_id']: ps['avg_score'] for ps in data['party_scores']}
    
    # Calculate total runs
    total_runs = sum(agg['num_runs'] for agg in aggregated.values())
    
    # Render template
    env = get_jinja_env()
    template = env.get_template('scoreboard.html')
    html = template.render(
        election_info=election_info,
        election_slug=election_slug,
        models=models,
        parties=parties,
        parties_sorted=parties_sorted,
        total_runs=total_runs,
        aggregated=aggregated,
        score_lookups=score_lookups,
        main_party_ids=main_party_ids,
        top_models_per_party=top_models_per_party
    )
    
    return html


def generate_model_detail_page(
    model_name: str,
    model_results: List[Dict[str, Any]],
    data_loader: DataLoader,
    election_slug: str,
    election_info: Dict[str, Any]
) -> str:
    """
    Generate HTML page for a specific model showing all questions, answers, and reasoning.
    
    Args:
        model_name: Name of the model
        model_results: List of result dictionaries for this model
        data_loader: DataLoader instance
        election_slug: Election identifier
        election_info: Election overview information
        
    Returns:
        HTML string
    """
    # Use the first run's questions (they should be the same across runs)
    questions = model_results[0]['questions']
    
    # Render template
    env = get_jinja_env()
    template = env.get_template('model_detail.html')
    
    # Render template
    html = template.render(
        model_name=model_name,
        model_results=model_results,
        election_info=election_info,
        election_slug=election_slug,
        questions=questions
    )
    
    return html


def generate_scoreboard(
    results_path: str,
    docs_path: str,
    election_slug: str,
    data_path: str
):
    """
    Generate scoreboard HTML for an election.
    
    Args:
        results_path: Path to results directory
        docs_path: Path to docs directory
        election_slug: Election identifier
        data_path: Path to WahlOMat data directory
    """
    results_dir = Path(results_path) / election_slug
    docs_dir = Path(docs_path) / election_slug
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    data_loader = DataLoader(data_path)
    data_loader.load_all()
    
    # Load results
    print(f"Loading results from {results_dir}...")
    results = load_all_results(results_dir)
    
    if not results:
        print(f"No results found in {results_dir}")
        return
    
    print(f"Loaded {len(results)} result files")
    
    # Aggregate results
    print("Aggregating results...")
    aggregated = aggregate_results(results)
    
    # Get top models per party
    top_models_per_party = get_top_models_per_party(aggregated, data_loader)
    
    # Generate HTML
    print("Generating HTML scoreboard...")
    html = generate_scoreboard_html(
        aggregated,
        top_models_per_party,
        data_loader,
        election_slug,
        data_loader.overview
    )
    
    # Save HTML
    output_file = docs_dir / "index.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Scoreboard saved to {output_file}")
    
    # Generate individual model pages
    print("Generating individual model pages...")
    for model in aggregated.keys():
        # Get all runs for this model
        model_results = [r for r in results if r['model'] == model]
        if model_results:
            model_html = generate_model_detail_page(
                model,
                model_results,
                data_loader,
                election_slug,
                data_loader.overview
            )
            model_filename = model.replace('/', '_') + '.html'
            model_output_file = docs_dir / model_filename
            with open(model_output_file, 'w', encoding='utf-8') as f:
                f.write(model_html)
            print(f"Model page saved to {model_output_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate scoreboard HTML")
    parser.add_argument(
        "--results-path",
        type=str,
        default=os.getenv("RESULTS_PATH", "results"),
        help="Path to results directory"
    )
    parser.add_argument(
        "--docs-path",
        type=str,
        default=os.getenv("DOCS_PATH", "docs"),
        help="Path to docs directory"
    )
    parser.add_argument(
        "--election",
        type=str,
        default="bundestagswahl2025",
        help="Election slug"
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default=os.getenv("DATA_PATH", "data/2025/deutschland"),
        help="Path to WahlOMat data directory"
    )
    
    args = parser.parse_args()
    
    generate_scoreboard(
        results_path=args.results_path,
        docs_path=args.docs_path,
        election_slug=args.election,
        data_path=args.data_path
    )

