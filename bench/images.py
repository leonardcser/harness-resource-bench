"""Freeze the official installers and build one versioned image per agent.

The scripts are served without changes. Pi has no version flag. So its
documented installer API override points to a fixed copy of its public release
metadata.
"""

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from agents import AGENTS

BASE = "harness-bench-base"
BASE_DOCKERFILE = """\
FROM docker.io/library/ubuntu:26.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl ca-certificates bash git build-essential procps ripgrep xz-utils python3 tmux \\
    && rm -rf /var/lib/apt/lists/*
"""
# Install size is what the install adds to these directories.
INSTALL_DIRS = ("/root", "/usr/local", "/opt")
AGENT_DOCKERFILE = """\
FROM {base}
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
{install}
RUN useradd -m -o -u 1000 bench && mkdir -p /workspace && chown bench:bench /workspace && chmod 755 /root
RUN for f in /root/.local/bin/* /root/.opencode/bin/* /root/.pi/agent/bin/*; do [ ! -e "$f" ] || ln -sf "$f" /usr/local/bin/$(basename "$f"); done
ENV HOME=/home/bench USER=bench LOGNAME=bench TERM=xterm-256color COLORTERM=truecolor
WORKDIR /workspace
USER bench
"""


def fetch_url(url):
    return subprocess.check_output(
        ["curl", "--fail", "--silent", "--show-error", "--location"]
        + ["--retry", "3", "--max-time", "120", url]
    )


def image(agent, version):
    return f"harness-bench-{agent}:{version}"


INSTALLERS = Path(__file__).resolve().parent / "installers"


class InstallerCache:
    """Serve the frozen installer scripts of `installers/` on the host
    loopback. The repository holds them, so a run of an old commit installs as
    that run did. With `fetch`, an installer that is not frozen at its version
    is downloaded; without it, that stops the run."""

    def __init__(self, targets, fetch=False):
        """`targets` lists the (agent, version) pairs that the cache serves."""
        manifest = INSTALLERS / "manifest.json"
        self.manifest = (
            json.loads(manifest.read_text()) if manifest.exists() else {"agents": {}}
        )
        frozen = self.manifest["agents"]
        for agent, version in targets:
            if frozen.get(agent, {}).get("version") != version:
                if not fetch:
                    raise ValueError(
                        f"No frozen installer for {agent} {version}: run"
                        f" `bench.py check {agent}`, then commit installers/"
                    )
                self.freeze(agent, version)
                manifest.write_text(json.dumps(self.manifest, indent=2) + "\n")
            for name, record in frozen[agent]["files"].items():
                data = (INSTALLERS / name).read_bytes()
                if hashlib.sha256(data).hexdigest() != record["sha256"]:
                    raise ValueError(f"Installer cache integrity failure: {name}")

        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, *_):
                pass

        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(Handler, directory=str(INSTALLERS))
        )
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def freeze(self, agent, version):
        """Download the installer of `agent` at `version`, in place of the one
        of an earlier version."""
        for name in self.manifest["agents"].get(agent, {}).get("files", {}):
            (INSTALLERS / name).unlink(missing_ok=True)
        files = {agent + ".sh": AGENTS[agent].installer}
        if agent == "pi":
            releases = "https://pi.dev/api/installer/releases"
            latest = json.loads(fetch_url(releases + "/latest"))
            if latest["version"] != version:
                raise ValueError("Pi installer latest release differs from the pin")
            files["pi/latest"] = releases + "/latest"
            for name in ("package.json", "package-lock.json"):
                files[f"pi/{version}/{name}"] = f"{releases}/{version}/{name}"
        records = {}
        for name, url in files.items():
            data = fetch_url(url)
            path = INSTALLERS / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            records[name] = {
                "url": url,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        self.manifest["agents"][agent] = {"version": version, "files": records}

    def installer_sha256(self, agent):
        return self.manifest["agents"][agent]["files"][agent + ".sh"]["sha256"]

    def url(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def build(tag, dockerfile, binary=None):
    """Build `dockerfile` without the layer cache, so an image holds what the
    installers serve now and not what an earlier build downloaded."""
    with tempfile.TemporaryDirectory() as context:
        Path(context, "Dockerfile").write_text(dockerfile)
        if binary:
            shutil.copy(binary, Path(context, "binary"))
        subprocess.run(
            [
                "podman",
                "build",
                "--format=docker",
                "--network=host",
                "--no-cache",
                "-q",
                "-t",
                tag,
                context,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    return json.loads(subprocess.check_output(["podman", "image", "inspect", tag]))[0][
        "Id"
    ]


def run(tag, *command):
    return subprocess.check_output(
        ["podman", "run", "--rm", "--user", "root", tag, *command], text=True
    ).strip()


def installed_bytes(tag):
    output = run(tag, "du", "-sk", "--total", *INSTALL_DIRS)
    return int(output.splitlines()[-1].split()[0]) * 1024


def prepare(targets, cache, local=None):
    """Build an image for each (agent, version) in `targets` and record what it
    installed. `local` is an (agent, path) pair. The binary at path replaces the
    release of that agent."""
    base_id = build(BASE, BASE_DOCKERFILE)
    base_bytes = installed_bytes(base_id)
    records = []
    for agent, version in targets:
        spec = AGENTS[agent]
        binary = local[1] if local and local[0] == agent else None
        install = (
            f"COPY binary /usr/local/bin/{spec.executable}"
            if binary
            else "RUN "
            + spec.install.replace("@INSTALLER_BASE@", cache.url()).replace(
                "@VERSION@", version
            )
        )
        dockerfile = AGENT_DOCKERFILE.format(base=BASE, install=install)
        image_id = build(image(agent, version), dockerfile, binary)
        reported = run(image_id, spec.executable, "--version")
        if not re.search(rf"(?<![\d.]){re.escape(version)}(?![\d.])", reported):
            raise RuntimeError(f"Expected {agent} {version}, got {reported}")
        path = run(
            image_id, "sh", "-c", f'readlink -f "$(command -v {spec.executable})"'
        )
        record = {
            "agent": agent,
            "version": version,
            "measured_version": reported,
            "executable_sha256": run(image_id, "sha256sum", path).split()[0],
            "install_bytes": installed_bytes(image_id) - base_bytes,
            "image_id": image_id,
            "install_command": install,
            "installer_sha256": None if binary else cache.installer_sha256(agent),
            "dockerfile_sha256": hashlib.sha256(dockerfile.encode()).hexdigest(),
        }
        if agent == "pi":
            record["node_version"] = run(image_id, "node", "--version")
        records.append(record)
    return base_id, records
