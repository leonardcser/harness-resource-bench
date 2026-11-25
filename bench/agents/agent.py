"""An agent, loaded from its recipe: a TOML file, with a Python file of the
same name beside it for what a template cannot say. `omp.toml` and
`opencode.toml` show every field.

Strings hold `${name}` placeholders. A string that is only a placeholder keeps
its type. The names that each part takes:

- `install`: `installers` (the installer cache), `version`
- `files` and `environment`: `url` (the mock model), `context_window`,
  `max_tokens`, `key`, `key_hint`
- `tools`: the step's `kind`, `path`, `old`, `new`, `output`, `command`,
  `pattern`, and the functions of `PLACEHOLDERS` in the Python file, called
  with (step, body, workspace). The Python file may also define
  `checkpoint_results`.

`tools.shell` runs every kind that has no tool of its own. A table in
`environment` becomes JSON. The TUI command takes `tui_prompt` before a prompt.
`summaries` are (start, mark) of a compaction prompt, `side_requests` and
`edit_retries` are marks, `reset` starts a new session, `background_setup` is
a file in HOME that a first launch writes later, and `server` means that the
TUI leaves a background server.
"""

import importlib.util
import json
import re
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTEXT_WINDOW = 200000
MAX_TOKENS = 32768
KEY = "benchmark-placeholder"
# The environment of every agent: the key under common names, and common
# opt-outs. A recipe's `environment` adds its own.
ENV = {
    "MOCK_KEY": KEY,
    "OPENAI_API_KEY": KEY,
    "ANTHROPIC_API_KEY": KEY,
    "DISABLE_AUTOUPDATER": "1",
    "DISABLE_TELEMETRY": "1",
    "DISABLE_ERROR_REPORTING": "1",
}
CONFIG_VALUES = {"url", "context_window", "max_tokens", "key", "key_hint"}
STEP_VALUES = {"kind", "path", "old", "new", "output", "command", "pattern"}
PLACEHOLDER = re.compile(r"\$\{(\w+)\}")


def render(value, lookup):
    """`value` with each placeholder replaced by `lookup(name)`."""
    if isinstance(value, str):
        whole = PLACEHOLDER.fullmatch(value)
        if whole:
            return lookup(whole[1])
        return PLACEHOLDER.sub(lambda m: str(lookup(m[1])), value)
    if isinstance(value, list):
        return [render(item, lookup) for item in value]
    if isinstance(value, dict):
        return {key: render(item, lookup) for key, item in value.items()}
    return value


def names(value):
    """The placeholders in `value`."""
    found = set()
    render(value, lambda name: found.add(name) or "")
    return found


@dataclass(frozen=True)
class Agent:
    name: str
    version: str
    executable: str
    install: dict  # `installer`, `command`, and more `files` and `probes`.
    commands: dict  # `headless`, `tui` and `tui_prompt`: the start of the command.
    tools: dict
    files: list = field(default_factory=list)
    environment: dict = field(default_factory=dict)
    summaries: list = field(default_factory=list)
    side_requests: list = field(default_factory=list)
    edit_retries: list = field(default_factory=list)
    reset: str = "/new"
    background_setup: str = ""
    server: bool = False
    placeholders: dict = field(default_factory=dict)
    checkpoint_results: Callable | None = None

    @classmethod
    def load(cls, path):
        path = Path(path)
        data = tomllib.loads(path.read_text())
        source = path.with_suffix(".py")
        if source.exists():
            spec = importlib.util.spec_from_file_location(f"recipe_{path.stem}", source)
            hooks = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(hooks)
            data["placeholders"] = getattr(hooks, "PLACEHOLDERS", {})
            data["checkpoint_results"] = getattr(hooks, "checkpoint_results", None)
        agent = cls(**data)
        allowed = {
            "install": (agent.install, {"installers", "version"}),
            "files": (agent.files, CONFIG_VALUES),
            "environment": (agent.environment, CONFIG_VALUES),
            "commands": (agent.commands, set()),
            "tools": (agent.tools, STEP_VALUES | agent.placeholders.keys()),
        }
        for section, (value, known) in allowed.items():
            if unknown := names(value) - known:
                raise ValueError(
                    f"{path}: unknown placeholders in {section}: {unknown}"
                )
        return agent

    def install_command(self, installers):
        """The command that installs the agent, from the cache at `installers`."""
        values = {"installers": installers, "version": self.version}
        command = self.install["command"]
        if isinstance(command, list):
            command = " && ".join(command)
        return render(command, values.__getitem__)

    def installer_files(self):
        """The files that the installer cache freezes, as name: url."""
        version = {"version": self.version}.__getitem__
        files = self.install.get("files", {})
        return {self.name + ".sh": self.install["installer"]} | {
            render(name, version): render(url, version) for name, url in files.items()
        }

    def configure(self, home, url):
        """Write the config under `home`. Return the extra environment."""
        values = {
            "url": url,
            "context_window": CONTEXT_WINDOW,
            "max_tokens": MAX_TOKENS,
            "key": KEY,
            "key_hint": KEY[-20:],
        }
        for entry in self.files:
            target = home / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            if "json" in entry:
                target.write_text(json.dumps(render(entry["json"], values.__getitem__)))
            else:
                target.write_text(render(entry["text"], values.__getitem__))
            if "dir_mode" in entry:
                target.parent.chmod(entry["dir_mode"])
            if "mode" in entry:
                target.chmod(entry["mode"])
        env = render(self.environment, values.__getitem__)
        return {
            name: json.dumps(value) if isinstance(value, dict) else value
            for name, value in env.items()
        }

    def command(self, frontend, prompt):
        """The command that starts the agent, with `prompt` after its flags."""
        if frontend == "headless":
            return [*self.commands["headless"], *prompt]
        flags = self.commands.get("tui_prompt", []) if prompt else []
        return [*self.commands["tui"], *flags, *prompt]

    def call(self, step, body, workspace):
        """The tool call, as (name, arguments), that runs `step`. `body` is the
        request, `workspace` the host directory of /workspace."""
        tool = self.tools.get(step.kind, self.tools["shell"])

        def lookup(name):
            if name in self.placeholders:
                return self.placeholders[name](step, body, workspace)
            return getattr(step, name)

        return tool["name"], render(tool["arguments"], lookup)
