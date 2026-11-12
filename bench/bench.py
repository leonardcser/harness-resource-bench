#!/usr/bin/env python3
"""Resource benchmark of coding agents. Run containers only on the measurement host.

bench.py run [AGENT ...] [--local-binary AGENT=PATH]
bench.py check [AGENT ...] [--local-binary AGENT=PATH]
bench.py transcript > transcript.json

README.md explains the commands.
"""

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

import host
from agents import AGENTS, VERSIONS
from case import MEMORY, execute, save
from images import InstallerCache, prepare
from plan import plan, warmups, work
from report import RESULTS, replay, report
from terminal import settings as terminal_settings
from workload import PROFILE_PATH, SEED

ROOT = Path(__file__).resolve().parent


def commit():
    """The commit of this code, if it has no changes. Else None."""
    git = ["git", "-C", str(ROOT)]
    if subprocess.check_output([*git, "status", "--porcelain", "."], text=True):
        return None
    return subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()


def folder(selected):
    """A new folder for a run: `results/DATE`, or `results/DATE-AGENTS` for some
    agents."""
    name = time.strftime("%Y-%m-%d")
    if len(selected) != len(AGENTS):
        name += "-" + "-".join(selected)
    out, number = RESULTS / name, 2
    while out.exists():
        out, number = RESULTS / f"{name}-{number}", number + 1
    return out


def build(selected, local, fetch):
    """The images of the agents, built with the frozen installers. With
    `fetch`, an installer of a new version is frozen first."""
    targets = [(agent, VERSIONS[agent]) for agent in selected]
    cache = InstallerCache(targets, fetch)
    try:
        base_id, records = prepare(targets, cache, local)
    finally:
        cache.close()
    return {"base_image_id": base_id, "agents": {r["agent"]: r for r in records}}


def run(out, selected, images, smoke, commit, keep_homes=False):
    """Every case of the plan, one at a time, into `out`, which holds no run. A run
    is one session: a measured case that fails stops it, and the setup check
    runs all its cases, then names the failed ones. `commit` is from `commit()`.
    With `keep_homes`, each case keeps the agent's HOME for analysis."""
    cases = plan(selected, smoke)
    config = {
        "smoke": smoke,
        "versions": {agent: VERSIONS[agent] for agent in selected},
        "images": images,
        "seed": SEED,
        "cpus": host.AGENT_CPUS,
        "memory": MEMORY,
        "terminal": terminal_settings(),
        "plan": cases,
    }
    if (out / "manifest.json").exists():
        raise RuntimeError(f"{out} already holds a run")
    out.mkdir(parents=True, exist_ok=True)
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    record = {"config": config, "machine": host.machine(), "started_utc": started}
    if commit:
        record["commit"] = commit
    save(out / "manifest.json", record)
    # The workload's shape, so the run stays readable after a new fit.
    shutil.copyfile(PROFILE_PATH, out / "profile.json")
    host.stay_on_harness_core()
    failed = []
    for case in ([] if smoke else warmups(selected)) + cases:
        print(f"START {case['id']}", flush=True)
        image_id = images["agents"][case["agent"]]["image_id"]
        path = out / "cases" / case["id"]
        result = execute(case, path, image_id, smoke, keep_homes)
        print(
            f"{result['status'].upper()} {case['id']} {result.get('error', '')}",
            flush=True,
        )
        report(out)
        if result["status"] != "ok":
            if not smoke:
                raise RuntimeError(f"Invalid sample; investigate: {path}")
            failed.append(case["id"])
    if failed:
        raise RuntimeError(f"Setup check failed: {', '.join(failed)}")
    if not replay(out):
        raise RuntimeError("Validation failed; inspect summary.json")
    print(f"DONE {out}", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="measure agents in a new run")
    check_parser = commands.add_parser(
        "check", help="build the images and run the short setup check only"
    )
    for bench in (run_parser, check_parser):
        bench.add_argument(
            "agents", nargs="*", metavar="AGENT", help=f"default: {' '.join(AGENTS)}"
        )
        bench.add_argument(
            "--local-binary",
            metavar="AGENT=PATH",
            help="install a local build of an agent that ships as one binary",
        )
        bench.add_argument(
            "--keep-homes",
            action="store_true",
            help="copy each case's HOME to cases/ID/home, for the recipes in RELEASE.md",
        )
    commands.add_parser("transcript", help="print the work that the model sends")
    args = parser.parse_args()
    if args.command == "transcript":
        print(json.dumps(work()))
        return
    unknown = set(args.agents) - AGENTS.keys()
    if unknown:
        parser.error(f"unknown agents {sorted(unknown)}; known: {' '.join(AGENTS)}")
    selected = [a for a in AGENTS if a in args.agents or not args.agents]
    local = None
    if args.local_binary:
        agent, _, path = args.local_binary.partition("=")
        if agent not in selected or not path:
            parser.error("--local-binary takes AGENT=PATH for a measured agent")
        local = (agent, Path(path).resolve())
    host.check()
    with host.exclusive():
        images = build(selected, local, fetch=args.command == "check")
        bench = {
            "selected": selected,
            "images": images,
            "commit": commit() if args.command == "run" else None,
            "keep_homes": args.keep_homes,
        }
        if args.command == "check":
            out = RESULTS / "check"
            shutil.rmtree(out, ignore_errors=True)
            run(out, smoke=True, **bench)
            return
        out = folder(selected)
        print(f"RUN {out}", flush=True)
        run(out / "smoke", smoke=True, **bench)
        run(out, smoke=False, **bench)


if __name__ == "__main__":
    main()
