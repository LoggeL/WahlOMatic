"""Scoreboard generator for aggregating and displaying evaluation results."""
import json
import html
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .data_loader import DataLoader


def decode_html_entities(text: str) -> str:
    """Decode HTML entities in text (e.g., &#10; -> newline, &amp;#10; -> newline)."""
    if not text:
        return text
    text_str = str(text)
    # First unescape any double-escaped entities (e.g., &amp;#10; -> &#10;)
    # Then unescape the actual entities (e.g., &#10; -> newline)
    return html.unescape(html.unescape(text_str))


def get_jinja_env() -> Environment:
    """Get Jinja2 environment for template rendering."""
    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(['html', 'xml'])
    )
    env.filters['decode_html'] = decode_html_entities
    return env


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
        
        # Calculate consistency score for this model
        # Get all questions from all runs
        if data['runs']:
            # Use first run's questions as reference (they should all have same statement_ids)
            reference_questions = data['runs'][0]['questions']
            total_questions = len(reference_questions)
            fully_consistent_questions = 0
            
            for ref_question in reference_questions:
                statement_id = ref_question['statement_id']
                # Get answers for this statement across all runs
                answers_by_run = []
                for run in data['runs']:
                    for q in run['questions']:
                        if q['statement_id'] == statement_id:
                            answers_by_run.append(q['answer'])
                            break
                
                # Count how many runs gave the most common answer
                answer_counts = defaultdict(int)
                for answer in answers_by_run:
                    answer_counts[answer] += 1
                most_common_count = max(answer_counts.values()) if answer_counts else 0
                
                # Check if all runs gave the same answer
                if most_common_count == len(answers_by_run) and len(answers_by_run) > 0:
                    fully_consistent_questions += 1
            
            consistency_score = (fully_consistent_questions / total_questions * 100) if total_questions > 0 else 0
            
            # Calculate opinionated score: percentage of non-neutral answers
            # Count all answers across all runs
            total_answers = 0
            non_neutral_answers = 0
            for run in data['runs']:
                for question in run['questions']:
                    answer = question['answer']
                    total_answers += 1
                    if answer != 2:  # 2 is neutral, 0 and 1 are opinionated
                        non_neutral_answers += 1
            
            opinionated_score = (non_neutral_answers / total_answers * 100) if total_answers > 0 else 0
        else:
            consistency_score = 0
            opinionated_score = 0
        
        aggregated[model] = {
            'num_runs': len(data['runs']),
            'party_scores': avg_scores,
            'consistency': round(consistency_score, 1),
            'opinionated': round(opinionated_score, 1)
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
    election_info: Dict[str, Any],
    results: List[Dict[str, Any]]
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
    
    # Calculate average metrics across all models
    avg_consistency = sum(agg['consistency'] for agg in aggregated.values()) / len(models) if models else 0
    avg_opinionated = sum(agg['opinionated'] for agg in aggregated.values()) / len(models) if models else 0
    
    # Extract run dates from all results
    run_dates = []
    for result in results:
        if 'timestamp' in result:
            try:
                from datetime import datetime
                timestamp = datetime.fromisoformat(result['timestamp'])
                run_dates.append(timestamp.date())
            except (ValueError, TypeError):
                pass
    
    # Calculate date range
    if run_dates:
        earliest_date = min(run_dates)
        latest_date = max(run_dates)
        if earliest_date == latest_date:
            run_date_range = earliest_date.strftime('%d.%m.%Y')
        else:
            run_date_range = f"{earliest_date.strftime('%d.%m.%Y')} - {latest_date.strftime('%d.%m.%Y')}"
    else:
        run_date_range = None
    
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
        top_models_per_party=top_models_per_party,
        party_avg_scores=party_avg_scores,
        avg_consistency=avg_consistency,
        avg_opinionated=avg_opinionated,
        run_date_range=run_date_range
    )
    
    return html


def generate_about_page() -> str:
    """
    Generate the about page HTML.
    
    Returns:
        HTML string for the about page
    """
    env = get_jinja_env()
    template = env.get_template('about.html')
    html = template.render()
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
    
    # Calculate consistency score across runs
    # For each question, check how many runs gave the same answer
    consistency_data = []
    total_questions = len(questions)
    fully_consistent_questions = 0
    
    for question in questions:
        statement_id = question['statement_id']
        # Get answers for this statement across all runs
        answers_by_run = []
        for result in model_results:
            for q in result['questions']:
                if q['statement_id'] == statement_id:
                    answers_by_run.append(q['answer'])
                    break
        
        # Count how many runs gave the most common answer
        answer_counts = defaultdict(int)
        for answer in answers_by_run:
            answer_counts[answer] += 1
        most_common_answer = max(answer_counts.items(), key=lambda x: x[1])[0] if answer_counts else None
        most_common_count = answer_counts[most_common_answer] if most_common_answer is not None else 0
        consistency_ratio = most_common_count / len(answers_by_run) if answers_by_run else 0
        
        if consistency_ratio == 1.0:
            fully_consistent_questions += 1
        
        consistency_data.append({
            'statement_id': statement_id,
            'consistency_ratio': consistency_ratio,
            'consistent_runs': most_common_count,
            'total_runs': len(answers_by_run)
        })
    
    # Overall consistency score: percentage of questions where all runs agreed
    overall_consistency = (fully_consistent_questions / total_questions * 100) if total_questions > 0 else 0
    
    # Calculate opinionated score: percentage of non-neutral answers across all runs
    total_answers = 0
    non_neutral_answers = 0
    for result in model_results:
        for question in result['questions']:
            answer = question['answer']
            total_answers += 1
            if answer != 2:  # 2 is neutral, 0 and 1 are opinionated
                non_neutral_answers += 1
    
    neutral_answers = total_answers - non_neutral_answers
    overall_opinionated = (non_neutral_answers / total_answers * 100) if total_answers > 0 else 0
    
    # Calculate average party scores across all runs
    party_scores_dict = defaultdict(list)
    for result in model_results:
        for party_score in result['party_scores']:
            party_scores_dict[party_score['party_id']].append(party_score['score'])
    
    # Calculate averages and sort by score
    ranked_parties = []
    for party_id, scores in party_scores_dict.items():
        avg_score = sum(scores) / len(scores)
        # Get party name from first run
        party_name = None
        party_longname = None
        for ps in model_results[0]['party_scores']:
            if ps['party_id'] == party_id:
                party_name = ps['party_name']
                party_longname = ps.get('party_longname', '')
                break
        
        ranked_parties.append({
            'party_id': party_id,
            'party_name': party_name,
            'party_longname': party_longname,
            'score': round(avg_score, 2)
        })
    
    # Sort by score descending
    ranked_parties.sort(key=lambda x: x['score'], reverse=True)
    
    # Define main parties (SPD, CDU/CSU, GRÜNE, FDP, AfD, Die Linke, BSW)
    main_party_ids = {0, 1, 2, 3, 4, 5, 25}  # Based on 2025 party.json
    
    # Get model answers (use first run's answers, they should be the same)
    model_answers = {q['statement_id']: q['answer'] for q in questions}
    
    # For each party, get comparison data (model answer vs party answer for each statement)
    party_comparisons = {}
    for party in ranked_parties:
        party_id = party['party_id']
        comparisons = []
        for question in questions:
            statement_id = question['statement_id']
            model_answer = model_answers[statement_id]
            model_reasoning = question.get('reasoning', '')
            try:
                party_answer = data_loader.get_party_opinion(party_id, statement_id)
                party_reasoning = data_loader.get_party_comment(party_id, statement_id)
            except ValueError:
                # Skip if party doesn't have an answer for this statement
                continue
            
            comparisons.append({
                'statement_id': statement_id,
                'question_text': question['text'],
                'model_answer': model_answer,
                'model_reasoning': model_reasoning,
                'party_answer': party_answer,
                'party_reasoning': party_reasoning
            })
        party_comparisons[party_id] = comparisons
    
    # Extract and format run dates for this model
    model_run_dates = []
    for result in model_results:
        if 'timestamp' in result:
            try:
                from datetime import datetime
                timestamp = datetime.fromisoformat(result['timestamp'])
                model_run_dates.append({
                    'run_id': result.get('run_id', 0),
                    'date': timestamp.date(),
                    'datetime': timestamp
                })
            except (ValueError, TypeError):
                pass
    
    # Sort by run_id
    model_run_dates.sort(key=lambda x: x['run_id'])
    
    # Calculate date range for this model
    if model_run_dates:
        earliest_date = min(rd['date'] for rd in model_run_dates)
        latest_date = max(rd['date'] for rd in model_run_dates)
        if earliest_date == latest_date:
            model_run_date_range = earliest_date.strftime('%d.%m.%Y')
        else:
            model_run_date_range = f"{earliest_date.strftime('%d.%m.%Y')} - {latest_date.strftime('%d.%m.%Y')}"
    else:
        model_run_date_range = None
    
    # Render template
    env = get_jinja_env()
    template = env.get_template('model_detail.html')
    
    # Render template
    html = template.render(
        model_name=model_name,
        model_results=model_results,
        election_info=election_info,
        election_slug=election_slug,
        questions=questions,
        ranked_parties=ranked_parties,
        main_party_ids=main_party_ids,
        party_comparisons=party_comparisons,
        overall_consistency=round(overall_consistency, 1),
        overall_opinionated=round(overall_opinionated, 1),
        consistency_data=consistency_data,
        total_answers=total_answers,
        neutral_answers=neutral_answers,
        non_neutral_answers=non_neutral_answers,
        model_run_date_range=model_run_date_range,
        model_run_dates=model_run_dates
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
        data_loader.overview,
        results
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
    
    # Generate about page in docs root
    print("Generating about page...")
    docs_root = Path(docs_path)
    about_html = generate_about_page()
    about_output_file = docs_root / "about.html"
    with open(about_output_file, 'w', encoding='utf-8') as f:
        f.write(about_html)
    print(f"About page saved to {about_output_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate scoreboard HTML")
    parser.add_argument(
        "--results-path",
        type=str,
        default="results",
        help="Path to results directory"
    )
    parser.add_argument(
        "--docs-path",
        type=str,
        default="docs",
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
        default="data/2025/deutschland",
        help="Path to WahlOMat data directory"
    )
    
    args = parser.parse_args()
    
    generate_scoreboard(
        results_path=args.results_path,
        docs_path=args.docs_path,
        election_slug=args.election,
        data_path=args.data_path
    )

