"""Command-line interface for validation and deterministic offline builds."""

from __future__ import annotations

import argparse
from pathlib import Path

from datacenter_need.pipeline import build_dataset, canonical_json, load_dataset
from datacenter_need.schemas import InputDataset
from datacenter_need.sources.ssb import fetch_employee_snapshot

DEFAULT_INPUT = Path("data/examples/synthetic.yaml")
DEFAULT_OUTPUT = Path("build/example")
DEFAULT_SCHEMA = Path("build/input.schema.json")
DEFAULT_SSB_SNAPSHOT = Path("data/sources/ssb/11658-2512-2025K4")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="datacenter-need")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate")
    validate.add_argument("--input", type=Path, default=DEFAULT_INPUT)

    build = commands.add_parser("build")
    build.add_argument("--offline", action="store_true")
    build.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    build.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)

    schema = commands.add_parser("schema")
    schema.add_argument("--output", type=Path, default=DEFAULT_SCHEMA)

    fetch_ssb = commands.add_parser("fetch-ssb")
    fetch_ssb.add_argument("--output", type=Path, default=DEFAULT_SSB_SNAPSHOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    if args.command == "validate":
        dataset, _ = load_dataset(args.input)
        print(f"valid: {len(dataset.occupations)} occupations")
    elif args.command == "build":
        build_dataset(args.input, args.output, offline=True)
        print(args.output)
    elif args.command == "schema":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(canonical_json(InputDataset.model_json_schema()), encoding="utf-8")
        print(args.output)
    else:
        fetch_employee_snapshot(args.output)
        print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
