"""The agents. Each module in this package holds everything about one agent:
how to install it, how to point it at the mock model, the tool calls that run
each step of the work, and the texts of its auxiliary requests. The rest of
the harness has no knowledge of any agent.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTEXT_WINDOW = 200000
MAX_TOKENS = 32768
KEY = "benchmark-placeholder"
# The environment of every agent.
ENV = {
    "MOCK_KEY": KEY,
    "OPENAI_API_KEY": KEY,
    "ANTHROPIC_API_KEY": KEY,
    "DISABLE_AUTOUPDATER": "1",
    "OPENCODE_DISABLE_AUTOUPDATE": "1",
    "DISABLE_TELEMETRY": "1",
    # Not CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: it also turns off Claude
    # Code's session titles, which are model requests that users make.
    "DISABLE_ERROR_REPORTING": "1",
    "DISABLE_BUG_COMMAND": "1",
    "PI_OFFLINE": "1",
    "PI_TELEMETRY": "0",
}


@dataclass(frozen=True)
class Agent:
    """One agent.

    - `version` is the release that a run measures.
    - `installer` is the official install script. The installer cache saves it
      and serves it at @INSTALLER_BASE@. `install` gets the version at
      @VERSION@.
    - `configure(home, url)` writes the agent's config under `home`, once per
      case, and returns its extra environment. `url` is the mock model.
    - `command(frontend, prompt)` is the command that starts the agent in
      `frontend`, with the arguments of `prompt` if it takes them. The TUI
      command is the bare command, as a user types it each day: `configure`
      holds its settings. The headless command passes them as flags, as
      automation does.
    - `call(step, body, workspace)` is the tool call, as (name, arguments), that
      runs a step of the work. `body` is the request, `workspace` the host
      directory that the agent sees as /workspace.
    - `summaries` are the summary prompts of its compaction, as (start, mark):
      the last user message starts with `start` and contains `mark`.
    - `side_requests` are marks of requests that keep the tool schemas but must
      not call them, such as a session title.
    - `edit_retries` are marks of a refused edit that asks for the same edit
      again. The model retries such an edit once, as a real model would.
    - `reset` starts a new session in the TUI.
    - `typed_prompt` is for a TUI that takes no prompt argument. The harness
      types the first prompt.
    - `quit` is the tmux key that quits the TUI. The harness presses it twice,
      for agents that ask to confirm.
    - `background_setup` is what the agent's first launch writes into HOME in
      the background, after the prompt shows. The first launch waits for it.
    - `server` is for a TUI that starts a shared background server, which
      stays after quit. The warm startup first runs an earlier session, so the
      server runs and has served the workspace, as later in a user's day.
    """

    name: str
    version: str
    installer: str
    install: str
    executable: str
    configure: Callable
    command: Callable
    call: Callable
    summaries: tuple = ()
    side_requests: tuple = ()
    edit_retries: tuple = ()
    reset: str = "/new"
    typed_prompt: bool = False
    quit: str = "C-c"
    background_setup: str = ""
    server: bool = False


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


NAMES = ("smelt", "pi", "codex", "claude_code", "opencode", "fx", "omp")
AGENTS = {
    agent.name: agent
    for agent in (import_module(f"agents.{name}").AGENT for name in NAMES)
}
VERSIONS = {name: agent.version for name, agent in AGENTS.items()}
