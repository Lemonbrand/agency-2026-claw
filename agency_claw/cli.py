from __future__ import annotations

import argparse
import sys

from . import correlate as correlate_mod
from . import dashboard, dataset, detectors, ledger, neotoma, paths
from .verify import verify_findings


def cmd_doctor(_: argparse.Namespace) -> int:
    paths.ensure_dirs()
    print(f"root: {paths.root()}")
    print(f"raw: {paths.raw_dir()}")
    print(f"duckdb: {paths.duckdb_path()}")
    print(f"findings: {paths.findings_dir()}")
    print(f"local neotoma: {paths.root() / '.neotoma' / 'data'}")
    return 0


def cmd_onboard(_: argparse.Namespace) -> int:
    out = dataset.onboard()
    ledger.event("onboard", {"tables": [row["table"] for row in out["manifest"]]})
    print(f"loaded {len(out['manifest'])} files")
    for profile in out["profiles"]:
        print(f"- {profile['table']}: {profile['row_count']} rows, {len(profile['columns'])} columns")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if args.skill == "vendor-concentration":
        findings = detectors.vendor_concentration(limit=args.limit)
    elif args.skill == "amendment-creep":
        findings = detectors.amendment_creep(limit=args.limit)
    elif args.skill == "related-parties":
        findings = detectors.related_parties(limit=args.limit)
    else:
        raise SystemExit(f"unknown skill: {args.skill}")
    print(f"{args.skill}: {len(findings)} findings")
    return 0


def cmd_correlate(_: argparse.Namespace) -> int:
    out = correlate_mod.correlate()
    print(f"correlated {len(out['entities'])} entities")
    return 0


def cmd_verify(_: argparse.Namespace) -> int:
    findings = verify_findings()
    replayed = sum(1 for row in findings if row.get("verification", {}).get("replayed"))
    print(f"verified {replayed}/{len(findings)} findings")
    return 0


def cmd_promote(_: argparse.Namespace) -> int:
    result = neotoma.promote()
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def cmd_ui(_: argparse.Namespace) -> int:
    out = dashboard.write_dashboard()
    print(out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agency")
    sub = parser.add_subparsers(required=True)

    doctor = sub.add_parser("doctor")
    doctor.set_defaults(func=cmd_doctor)

    onboard = sub.add_parser("onboard")
    onboard.set_defaults(func=cmd_onboard)

    run = sub.add_parser("run")
    run.add_argument("skill", choices=["vendor-concentration", "amendment-creep", "related-parties"])
    run.add_argument("--limit", type=int, default=20)
    run.set_defaults(func=cmd_run)

    correlate = sub.add_parser("correlate")
    correlate.set_defaults(func=cmd_correlate)

    verify = sub.add_parser("verify")
    verify.set_defaults(func=cmd_verify)

    promote = sub.add_parser("promote")
    promote.set_defaults(func=cmd_promote)

    ui = sub.add_parser("ui")
    ui.set_defaults(func=cmd_ui)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
