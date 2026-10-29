"""Run a reproducible local demo or small synthetic benchmark."""

import argparse

from .examples import examples
from .simulator import run_solver


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("demo", "benchmark"))
    args = parser.parse_args()
    cases = examples()[:1] if args.command == "demo" else examples()
    results = [(case, run_solver(case.values)) for case in cases]
    for case, result in results:
        print(f"{case.name}: target={result.target_index} park={result.final_index} "
              f"score={result.score} reads={result.query_count} travel={result.travel} "
              f"reversals={result.reversal_count} overshoot={result.overshoot}")
        if args.command == "demo":
            print("motor path:", ", ".join(map(str, result.trace)))
    if args.command == "benchmark":
        print(f"synthetic mean score: {sum(result.score for _, result in results) / len(results):.2f}")


if __name__ == "__main__":
    main()
