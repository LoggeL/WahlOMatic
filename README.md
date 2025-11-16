# WahlOMat LLM Evaluation Engine

A system for evaluating Large Language Models (LLMs) against German WahlOMat political quiz data. Tests how well different LLMs align with German political party positions and generates interactive visual scoreboards.

## Features

- Evaluate LLMs against WahlOMat statements using OpenRouter API
- Calculate agreement scores (0-100%) with each political party
- Run multiple parallel evaluations for consistency testing
- Generate interactive HTML scoreboards with sorting and filtering
- Template-based architecture for easy customization

## Installation

```bash
git clone <repository-url>
cd WahlOMatic
pip install -r requirements.txt
```

Create a `.env` file:

```env
OPENROUTER_API_KEY=your_api_key_here
```

## Usage

### Run Evaluation

```bash
python3 -m src.run_evaluation --model openai/gpt-4o
```

Options:
- `--model`: Model name (required)
- `--data-path`: Path to WahlOMat data directory
- `--results-path`: Path to results directory
- `--election`: Election slug (default: `bundestagswahl2025`)
- `--runs`: Number of parallel runs (default: 5)

Examples:
```bash
# Use default election
python3 -m src.run_evaluation --model openai/gpt-4o

# Specify a different election
python3 -m src.run_evaluation --model openai/gpt-4o --election landtagswahl2024

# Custom paths and election
python3 -m src.run_evaluation --model openai/gpt-4o --election bundestagswahl2025 --data-path data/2025/deutschland
```

### Generate Scoreboard

```bash
python3 -m src.generate_scoreboard --election bundestagswahl2025
```

Options:
- `--election`: Election slug (default: `bundestagswahl2025`)
- `--results-path`: Path to results directory
- `--docs-path`: Path to docs directory
- `--data-path`: Path to WahlOMat data directory

Generates HTML files in `docs/bundestagswahl2025/`:
- `index.html` - Main scoreboard with all models
- `{model_name}.html` - Individual model detail pages

## Scoring Algorithm

Each statement is scored on a 0-2 point system:
- **2 points**: Complete agreement (same answer)
- **1 point**: Partial agreement (neutral vs yes/no)
- **0 points**: Complete disagreement (yes vs no)

Party scores: `(sum of agreement scores / (total_statements * 2)) * 100`

## Project Structure

```
WahlOMatic/
├── src/                    # Python source code
├── templates/              # Jinja2 HTML templates
├── docs/                   # Generated HTML scoreboards
├── results/                # JSON evaluation results
├── data/                   # WahlOMat data files
└── requirements.txt        # Python dependencies
```

## Data Format

Results are saved as JSON with model responses, party scores, and reasoning for each statement.

## GitHub Pages Deployment

1. Generate scoreboards: `python3 -m src.generate_scoreboard`
2. Commit and push `docs/` directory
3. Enable GitHub Pages pointing to `/docs` folder

## License

MIT License

## Data Source

WahlOMat data from [qual-o-mat-data](https://github.com/gockelhahn/qual-o-mat-data)
