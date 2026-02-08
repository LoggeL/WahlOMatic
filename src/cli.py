"""Unified CLI entry point for WahlOMatic."""
import argparse
import sys


def cmd_evaluate(args):
    """Run LLM evaluation."""
    from .openrouter_client import OpenRouterClient
    from .run_evaluation import run_evaluation

    # Validate API key before starting
    print("Validating API key...")
    client = OpenRouterClient(model=args.model)
    if not client.validate_key():
        print("Error: Invalid API key. Please check your OPENROUTER_API_KEY in .env file.", file=sys.stderr)
        sys.exit(1)
    print("API key is valid.")

    results = run_evaluation(
        model_name=args.model,
        data_path=args.data_path,
        results_path=args.results_path,
        election_slug=args.election,
        num_runs=args.runs,
    )

    if args.generate:
        print("\nGenerating scoreboard...")
        from .generate_scoreboard import generate_scoreboard
        generate_scoreboard(
            results_path=args.results_path,
            docs_path=args.docs_path,
            election_slug=args.election,
            data_path=args.data_path,
        )

    return results


def cmd_generate(args):
    """Generate scoreboard HTML."""
    from .generate_scoreboard import generate_scoreboard
    generate_scoreboard(
        results_path=args.results_path,
        docs_path=args.docs_path,
        election_slug=args.election,
        data_path=args.data_path,
    )


def cmd_run(args):
    """Run evaluation and then generate scoreboard."""
    args.generate = True
    cmd_evaluate(args)


def main():
    parser = argparse.ArgumentParser(
        prog="wahlomatic",
        description="WahlOMatic - LLM political bias evaluation tool",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Shared arguments
    def add_common_args(sub):
        sub.add_argument("--data-path", type=str, default="data/2025/deutschland",
                         help="Path to WahlOMat data directory")
        sub.add_argument("--results-path", type=str, default="results",
                         help="Path to results directory")
        sub.add_argument("--docs-path", type=str, default="docs",
                         help="Path to docs directory")
        sub.add_argument("--election", type=str, default="bundestagswahl2025",
                         help="Election slug")

    # evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Run LLM evaluation")
    eval_parser.add_argument("--model", type=str, required=True,
                             help="Model name (e.g. 'openai/gpt-4o')")
    eval_parser.add_argument("--runs", type=int, default=5,
                             help="Number of parallel runs")
    eval_parser.add_argument("--generate", action="store_true",
                             help="Auto-generate scoreboard after evaluation")
    add_common_args(eval_parser)

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate scoreboard HTML")
    add_common_args(gen_parser)

    # run (evaluate + generate)
    run_parser = subparsers.add_parser("run", help="Run evaluation then generate scoreboard")
    run_parser.add_argument("--model", type=str, required=True,
                            help="Model name (e.g. 'openai/gpt-4o')")
    run_parser.add_argument("--runs", type=int, default=5,
                            help="Number of parallel runs")
    add_common_args(run_parser)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "evaluate":
        cmd_evaluate(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "run":
        cmd_run(args)


if __name__ == "__main__":
    main()
