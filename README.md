# WahlOMat LLM Evaluation Engine

A comprehensive system for evaluating Large Language Models (LLMs) against German WahlOMat political quiz data. This tool tests how well different LLMs align with German political party positions and generates interactive visual scoreboards.

## Overview

[WahlOMat](https://www.wahl-o-mat.de/) is a popular German political quiz tool that helps voters find which political party aligns best with their views. This evaluation engine uses WahlOMat data to assess how well various LLMs match the positions of German political parties across multiple policy statements.

## Features

- 🎯 **Multi-Model Evaluation**: Test any LLM available through OpenRouter API
- 📊 **Comprehensive Scoring**: Calculate agreement scores (0-100%) with each political party
- 🔄 **Consistency Testing**: Run multiple parallel evaluations to test model consistency
- 📈 **Interactive Scoreboards**: Generate beautiful, interactive HTML scoreboards with sorting and filtering
- 📝 **Detailed Results**: JSON output with full question-answer pairs and reasoning
- 🎨 **Template-Based**: Clean separation of HTML templates from Python logic
- 🌐 **GitHub Pages Ready**: Static HTML output perfect for GitHub Pages deployment

## Installation

### Prerequisites

- Python 3.8 or higher
- An OpenRouter API key ([get one here](https://openrouter.ai/))

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd WahlOMatic
   ```

2. **Install dependencies:**
   
   Using `pip`:
   ```bash
   pip install -r requirements.txt
   ```
   
   Or using `uv` (recommended):
   ```bash
   uv pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   
   Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenRouter API key
   ```

## Configuration

Create a `.env` file with the following variables:

```env
OPENROUTER_API_KEY=your_api_key_here
DEFAULT_MODEL=openai/gpt-4o
DATA_PATH=data/2025/deutschland
RESULTS_PATH=results
DOCS_PATH=docs
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key (required) | - |
| `DEFAULT_MODEL` | Default model to use | `openai/gpt-4o` |
| `DATA_PATH` | Path to WahlOMat data directory | `data/2025/deutschland` |
| `RESULTS_PATH` | Path to store JSON results | `results` |
| `DOCS_PATH` | Path to store generated HTML | `docs` |

## Usage

### Running an Evaluation

Evaluate a model against the WahlOMat data:

```bash
python3 -m src.run_evaluation --model openai/gpt-4o
```

Or using `uv`:
```bash
uv run python -m src.run_evaluation --model openai/gpt-4o
```

#### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--model` | Model name (e.g., `openai/gpt-4o`, `anthropic/claude-3-opus`) | Required |
| `--data-path` | Path to WahlOMat data directory | From `.env` |
| `--results-path` | Path to results directory | From `.env` |
| `--election` | Election slug | `bundestagswahl2025` |
| `--runs` | Number of parallel runs for consistency testing | `5` |

#### Example: Evaluating Multiple Models

```bash
# Evaluate GPT-4
python3 -m src.run_evaluation --model openai/gpt-4o

# Evaluate Claude
python3 -m src.run_evaluation --model anthropic/claude-3-opus

# Evaluate with custom settings
python3 -m src.run_evaluation \
  --model openai/gpt-4o \
  --runs 10 \
  --election bundestagswahl2025
```

### Generating Scoreboards

After running evaluations, generate the HTML scoreboard:

```bash
python3 -m src.generate_scoreboard --election bundestagswahl2025
```

Or using `uv`:
```bash
uv run python -m src.generate_scoreboard --election bundestagswahl2025
```

#### Scoreboard Generation Options

| Option | Description | Default |
|--------|-------------|---------|
| `--election` | Election slug | `bundestagswahl2025` |
| `--results-path` | Path to results directory | From `.env` |
| `--docs-path` | Path to docs directory | From `.env` |
| `--data-path` | Path to WahlOMat data directory | From `.env` |

This will create:
- `docs/bundestagswahl2025/index.html` - Main scoreboard with all models
- `docs/bundestagswahl2025/{model_name}.html` - Individual model detail pages

## Scoring Algorithm

The evaluation uses a nuanced 0-2 point system per statement:

- **2 points**: Complete agreement
  - Both agree (yes/yes)
  - Both disagree (no/no)
  - Both neutral (neutral/neutral)

- **1 point**: Partial agreement
  - Neutral vs. Yes/No
  - Yes/No vs. Neutral

- **0 points**: Complete disagreement
  - Yes vs. No
  - No vs. Yes

### Score Calculation

Party scores are calculated as:

```
score = (sum of agreement scores / (total_statements * 2)) * 100
```

This gives a percentage from 0-100% where:
- **100%** = Perfect alignment on all statements
- **50%** = Neutral alignment (neither agree nor disagree)
- **0%** = Complete disagreement on all statements

## Project Structure

```
WahlOMatic/
├── src/
│   ├── data_loader.py          # Loads WahlOMat JSON data
│   ├── evaluator.py            # Scoring functions and algorithms
│   ├── openrouter_client.py    # OpenRouter API client
│   ├── prompts.py              # Prompt engineering for LLMs
│   ├── run_evaluation.py       # Main evaluation runner
│   └── generate_scoreboard.py  # Scoreboard HTML generator
├── templates/
│   ├── scoreboard.html         # Main scoreboard template
│   └── model_detail.html       # Individual model detail template
├── docs/                       # Generated static website (GitHub Pages)
│   └── bundestagswahl2025/
│       ├── index.html          # Main scoreboard
│       └── *.html              # Individual model pages
├── results/                    # JSON results from evaluations
│   └── bundestagswahl2025/
│       └── *.json              # Result files
├── data/                       # WahlOMat data files
│   └── 2025/
│       └── deutschland/
│           ├── statement.json
│           ├── party.json
│           ├── answer.json
│           └── ...
├── .env                        # Configuration (not in git)
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Data Format

### Input: WahlOMat Data

The system expects WahlOMat data in JSON format:
- `statement.json` - Political statements/questions
- `party.json` - Political parties and their metadata
- `answer.json` - Party answers to statements
- `overview.json` - Election overview information

### Output: Result JSON

Results are saved as JSON files with the following structure:

```json
{
  "model": "openai/gpt-4o",
  "election": "bundestagswahl2025",
  "timestamp": "2025-01-16T12:34:56.789Z",
  "run_id": 1,
  "questions": [
    {
      "statement_id": 0,
      "text": "Deutschland soll die Ukraine weiterhin militärisch unterstützen.",
      "answer": 0,
      "reasoning": "I agree with this statement because..."
    }
  ],
  "party_scores": [
    {
      "party_id": 0,
      "party_name": "SPD",
      "party_longname": "Sozialdemokratische Partei Deutschlands",
      "score": 75.5
    }
  ]
}
```

### Answer Values

- `0` = Stimme zu (Agree)
- `1` = Stimme nicht zu (Disagree)
- `2` = Neutral

## GitHub Pages Deployment

1. **Generate scoreboards:**
   ```bash
   python3 -m src.generate_scoreboard --election bundestagswahl2025
   ```

2. **Commit and push:**
   ```bash
   git add docs/
   git commit -m "Update scoreboards"
   git push
   ```

3. **Enable GitHub Pages:**
   - Go to repository Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main` (or your default branch)
   - Folder: `/docs`
   - Save

Your scoreboards will be available at `https://yourusername.github.io/WahlOMatic/`

## Development

### Running Tests

```bash
# Run evaluation
python3 -m src.run_evaluation --model openai/gpt-4o --runs 1

# Generate scoreboard
python3 -m src.generate_scoreboard --election bundestagswahl2025
```

### Modifying Templates

Templates are located in `templates/`:
- `scoreboard.html` - Main scoreboard with comparison table
- `model_detail.html` - Individual model question-answer pages

Templates use Jinja2 syntax. After modifying templates, regenerate the scoreboards.

### Adding New Features

1. Evaluation logic: Modify `src/evaluator.py`
2. Prompts: Modify `src/prompts.py`
3. Scoreboard generation: Modify `src/generate_scoreboard.py`
4. Templates: Modify files in `templates/`

## Troubleshooting

### Common Issues

**Issue**: `python` command not found
- **Solution**: Use `python3` instead, or install `python-is-python3` package

**Issue**: OpenRouter API errors
- **Solution**: Check your API key in `.env` file and ensure you have credits

**Issue**: No results found when generating scoreboard
- **Solution**: Make sure you've run evaluations first and results are in `results/{election}/`

**Issue**: Template not found
- **Solution**: Ensure `templates/` directory exists with `scoreboard.html` and `model_detail.html`

## License

MIT License

## Data Source

WahlOMat data from [qual-o-mat-data](https://github.com/gockelhahn/qual-o-mat-data) by [gockelhahn](https://github.com/gockelhahn).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- [WahlOMat](https://www.wahl-o-mat.de/) for the political quiz concept
- [OpenRouter](https://openrouter.ai/) for LLM API access
- [qual-o-mat-data](https://github.com/gockelhahn/qual-o-mat-data) for the data
