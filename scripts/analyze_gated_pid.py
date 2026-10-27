#!/usr/bin/env python3
"""Run cross-fitted uncertainty-gate analysis on a saved PID experiment."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.experiments.common import finish_manifest
from src.experiments.gated_pid import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--primary-error-cap', type=float, default=.01)
    parser.add_argument('--sensitivity-caps', type=float, nargs='+', default=[.005, .01, .02])
    parser.add_argument('--bootstrap', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=2026)
    args = parser.parse_args()
    result = run(args.run, args.output, args.primary_error_cap,
                 tuple(args.sensitivity_caps), args.bootstrap, args.seed)
    finish_manifest(args.output)
    print(json.dumps({'status': result['status'], 'output': str(args.output.resolve())}, indent=2))


if __name__ == '__main__':
    main()
