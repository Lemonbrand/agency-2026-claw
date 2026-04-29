from __future__ import annotations

import argparse
import sys

from . import correlate as correlate_mod
from . import dashboard, dataset, detectors, execution_proof, hackathon, judge_app, ledger, neotoma, paths, public_export
from .disconfirm import disconfirm
from .planner import create_plan
from .resolution import resolve_entities
from .reviewer import review
from .runner import run_plan
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


def cmd_hackathon_onboard(_: argparse.Namespace) -> int:
    out = hackathon.onboard()
    print(f"materialized {len(out['manifest'])} hackathon tables from Postgres")
    for profile in out["profiles"]:
        print(f"- {profile['table']}: {profile['row_count']:,} rows, {len(profile['columns'])} columns")
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


def cmd_plan(args: argparse.Namespace) -> int:
    plan = create_plan(brain_name=args.brain)
    print(
        f"plan ({plan.get('brain')}): selected {len(plan.get('selected', []))}, rejected {len(plan.get('rejected', []))}"
    )
    for item in plan.get("selected", []):
        print(f"- run {item.get('skill')}: {item.get('reason')}")
    for item in plan.get("rejected", [])[:8]:
        print(f"- reject {item.get('skill')}: {item.get('reason')}")
    return 0


def cmd_run_plan(args: argparse.Namespace) -> int:
    out = run_plan(limit=args.limit)
    print(f"ran {len(out['runs'])} planned skill(s)")
    for run in out["runs"]:
        print(f"- {run.get('skill')}: {run.get('status')} ({run.get('finding_count', 0)} findings)")
    return 0


def cmd_disconfirm(args: argparse.Namespace) -> int:
    out = disconfirm(brain_name=args.brain)
    summary = out["summary"]
    print(
        f"disconfirm ({out.get('brain')}): {summary['total']} checks, {summary['supported']} supported, {summary['contested']} contested, {summary['inconclusive']} inconclusive"
    )
    return 0


def cmd_resolve_entities(args: argparse.Namespace) -> int:
    out = resolve_entities(brain_name=args.brain)
    print(f"entity resolution ({out.get('brain')}): {len(out.get('clusters', []))} cluster(s)")
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


def cmd_review(args: argparse.Namespace) -> int:
    out = review(reviewer_name=args.reviewer)
    print(f"review ({out.get('reviewer')}): {len(out.get('issues', []))} issue(s)")
    print(out.get("recommended_language", ""))
    return 0


def cmd_ui(_: argparse.Namespace) -> int:
    out = dashboard.write_dashboard()
    print(out)
    return 0


def cmd_execution_proof(args: argparse.Namespace) -> int:
    out = execution_proof.run_execution_proof(max_rows=args.max_rows, timeout_s=args.timeout)
    ok = sum(1 for proof in out.get("proofs", []) if proof.get("result", {}).get("ok"))
    print(f"execution proof: {ok}/{out.get('count', 0)} probes executed")
    print(paths.findings_dir() / "execution-proof.json")
    return 0


def cmd_public_export(_: argparse.Namespace) -> int:
    out = public_export.public_export()
    print(f"public export: {out['artifact_count']} artifacts")
    print(out["manifest"])
    return 0


def cmd_judge_bundle(args: argparse.Namespace) -> int:
    proof = execution_proof.run_execution_proof(max_rows=args.max_rows, timeout_s=args.timeout)
    ok = sum(1 for item in proof.get("proofs", []) if item.get("result", {}).get("ok"))
    export = public_export.public_export()
    print(f"judge bundle: {ok}/{proof.get('count', 0)} probes executed, {export['artifact_count']} artifacts")
    print(export["manifest"])
    return 0


def cmd_judge_app_init(_: argparse.Namespace) -> int:
    out = judge_app.init_shared_runtime()
    print(out["runtime"])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agency")
    sub = parser.add_subparsers(required=True)

    doctor = sub.add_parser("doctor")
    doctor.set_defaults(func=cmd_doctor)

    onboard = sub.add_parser("onboard")
    onboard.set_defaults(func=cmd_onboard)

    hackathon_onboard = sub.add_parser("hackathon-onboard")
    hackathon_onboard.set_defaults(func=cmd_hackathon_onboard)

    plan = sub.add_parser("plan")
    plan.add_argument("--brain", choices=["heuristic", "codex"], default="heuristic")
    plan.set_defaults(func=cmd_plan)

    run = sub.add_parser("run")
    run.add_argument("skill", choices=["vendor-concentration", "amendment-creep", "related-parties"])
    run.add_argument("--limit", type=int, default=20)
    run.set_defaults(func=cmd_run)

    run_plan_parser = sub.add_parser("run-plan")
    run_plan_parser.add_argument("--limit", type=int, default=20)
    run_plan_parser.set_defaults(func=cmd_run_plan)

    correlate = sub.add_parser("correlate")
    correlate.set_defaults(func=cmd_correlate)

    verify = sub.add_parser("verify")
    verify.set_defaults(func=cmd_verify)

    disconfirm_parser = sub.add_parser("disconfirm")
    disconfirm_parser.add_argument("--brain", choices=["heuristic", "codex"], default="heuristic")
    disconfirm_parser.set_defaults(func=cmd_disconfirm)

    resolve_parser = sub.add_parser("resolve-entities")
    resolve_parser.add_argument("--brain", choices=["heuristic", "codex"], default="heuristic")
    resolve_parser.set_defaults(func=cmd_resolve_entities)

    review_parser = sub.add_parser("review")
    review_parser.add_argument("--reviewer", choices=["heuristic", "claude"], default="heuristic")
    review_parser.set_defaults(func=cmd_review)

    promote = sub.add_parser("promote")
    promote.set_defaults(func=cmd_promote)

    ui = sub.add_parser("ui")
    ui.set_defaults(func=cmd_ui)

    proof = sub.add_parser("execution-proof")
    proof.add_argument("--max-rows", type=int, default=25)
    proof.add_argument("--timeout", type=int, default=8)
    proof.set_defaults(func=cmd_execution_proof)

    export = sub.add_parser("public-export")
    export.set_defaults(func=cmd_public_export)

    bundle = sub.add_parser("judge-bundle")
    bundle.add_argument("--max-rows", type=int, default=25)
    bundle.add_argument("--timeout", type=int, default=8)
    bundle.set_defaults(func=cmd_judge_bundle)

    shared = sub.add_parser("judge-app-init")
    shared.set_defaults(func=cmd_judge_app_init)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
