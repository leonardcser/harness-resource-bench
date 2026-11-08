#!/usr/bin/env python3
"""Resource benchmark of coding agents. Run containers only on the measurement host.

bench.py run [AGENT ...] [--local-binary AGENT=PATH]
bench.py check [AGENT ...] [--local-binary AGENT=PATH]
bench.py publish
bench.py transcript > transcript.json

README.md explains the commands.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

import host
from agents import AGENTS, VERSIONS
from case import MEMORY, execute, save
from images import InstallerCache, image, prepare
from plan import plan, warmups, work
from report import RESULTS, publish, replay, report
from terminal import settings as terminal_settings
from workload import PROFILE_PATH, SEED

ROOT = Path(__file__).resolve().parent


def source_digest():
    """A checksum of the code and data that decide what the numbers mean."""
    checksum = hashlib.sha256()
    names = ["workload/profile.json", "pyproject.toml", "uv.lock", ".python-version"]
    paths = sorted(p for p in ROOT.rglob("*.py") if ".venv" not in p.parts)
    for path in paths + [ROOT / name for name in names]:
        checksum.update(str(path.relative_to(ROOT)).encode())
        checksum.update(path.read_bytes())
    return checksum.hexdigest()


def folder(selected, local):
    """Where to run: the newest unfinished run of these agents if it can resume,
    else a new folder `results/DATE`, or `results/DATE-AGENTS` for some agents.
    A run can resume when its versions, local build and code are the same."""
    versions = {agent: VERSIONS[agent] for agent in selected}
    digest = source_digest()
    found = sorted(
        RESULTS.glob("*/images.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    for path in found:
        out = path.parent
        built = json.loads(path.read_text())["agents"]
        if {agent: r["version"] for agent, r in built.items()} != versions:
            continue
        local_agent = local[0] if local else None
        if any(
            r["install_command"].startswith("COPY ") != (agent == local_agent)
            for agent, r in built.items()
        ):
            continue
        manifests = {
            m: json.loads(m.read_text())
            for m in (out / "manifest.json", out / "smoke" / "manifest.json")
            if m.exists()
        }
        if any(m["config"]["source_sha256"] != digest for m in manifests.values()):
            continue
        # The replay is the last step of a run, so a run with one is finished.
        if "replay" in manifests.get(out / "manifest.json", {}):
            continue
        return out
    name = time.strftime("%Y-%m-%d")
    if len(selected) != len(AGENTS):
        name += "-" + "-".join(selected)
    out, number = RESULTS / name, 2
    while out.exists():
        out, number = RESULTS / f"{name}-{number}", number + 1
    return out


def images_of(out, selected, local):
    """The images of the run, built with the run's own frozen installers on
    first use."""
    path = out / "images.json"
    if not path.exists():
        out.mkdir(parents=True, exist_ok=True)
        targets = [(agent, VERSIONS[agent]) for agent in selected]
        cache = InstallerCache(out / "installers", targets)
        try:
            base_id, records = prepare(targets, cache, local)
        finally:
            cache.close()
        save(
            path,
            {"base_image_id": base_id, "agents": {r["agent"]: r for r in records}},
        )
    images = json.loads(path.read_text())
    for record in images["agents"].values():
        tag = image(record["agent"], record["version"])
        actual = json.loads(
            subprocess.check_output(["podman", "image", "inspect", tag])
        )
        if record["image_id"] != actual[0]["Id"]:
            raise RuntimeError(f"Image mismatch for {tag}; prepare a new run")
    return images


def run(out, selected, images, smoke):
    """Every case of the plan in `out`, one at a time, resuming finished ones."""
    cases = plan(selected, smoke)
    config = {
        "smoke": smoke,
        "source_sha256": source_digest(),
        "versions": {agent: VERSIONS[agent] for agent in selected},
        "images": images,
        "seed": SEED,
        "cpus": host.AGENT_CPUS,
        "memory": MEMORY,
        "terminal": terminal_settings(),
        "plan": cases,
    }
    out.mkdir(parents=True, exist_ok=True)
    manifest = out / "manifest.json"
    if manifest.exists():
        if json.loads(manifest.read_text())["config"] != config:
            raise RuntimeError(
                "Cannot resume with changed code, versions, images, or plan"
            )
    else:
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save(
            manifest,
            {"config": config, "machine": host.machine(), "started_utc": started},
        )
        # The workload's shape, so the run stays readable after a new fit.
        shutil.copyfile(PROFILE_PATH, out / "profile.json")
    host.stay_on_harness_core()
    failed = []
    for case in ([] if smoke else warmups(selected)) + cases:
        path = out / "cases" / case["id"] / "result.json"
        saved = json.loads(path.read_text()) if path.exists() else None
        # A setup check runs its failed cases again.
        if saved and (saved["status"] == "ok" or not smoke):
            result = saved
        else:
            print(f"START {case['id']}", flush=True)
            image_id = images["agents"][case["agent"]]["image_id"]
            result = execute(case, path.parent, image_id, smoke)
            print(
                f"{result['status'].upper()} {case['id']} {result.get('error', '')}",
                flush=True,
            )
        report(out)
        if result["status"] != "ok":
            if not smoke:
                raise RuntimeError(
                    f"Invalid sample saved; investigate before rerunning: {case['id']}"
                )
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
    run_parser = commands.add_parser(
        "run", help="measure agents, resume an unfinished run and publish"
    )
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
    commands.add_parser("publish", help="publish the newest complete run")
    commands.add_parser("transcript", help="print the work that the model sends")
    args = parser.parse_args()
    if args.command == "transcript":
        print(json.dumps(work()))
        return
    if args.command == "publish":
        publish()
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
        out = folder(selected, local)
        print(f"{'RESUME' if out.exists() else 'NEW'} {out}", flush=True)
        images = images_of(out, selected, local)
        run(out / "smoke", selected, images, smoke=True)
        if args.command == "check":
            return
        run(out, selected, images, smoke=False)
        if len(selected) == len(AGENTS):
            publish()


if __name__ == "__main__":
    main()
