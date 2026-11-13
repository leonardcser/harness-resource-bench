import re

from agents import CONTEXT_WINDOW, MAX_TOKENS, Agent, write_json
from model.requests import history, strings


def configure(home, url):
    # YAML reads JSON.
    write_json(
        home / ".omp/agent/config.yml",
        {
            "startup": {"setupWizard": False, "checkUpdate": False},
            "marketplace": {"autoUpdate": "off"},
            "modelRoles": {"default": "mock/mock-model"},
            "tools": {"approvalMode": "yolo"},
        },
    )
    write_json(
        home / ".omp/agent/models.yml",
        {
            "providers": {
                "mock": {
                    "baseUrl": url + "/v1",
                    "api": "openai-completions",
                    "auth": "apiKey",
                    "apiKey": "MOCK_KEY",
                    "models": [
                        {
                            "id": "mock-model",
                            "reasoning": True,
                            "contextWindow": CONTEXT_WINDOW,
                            "maxTokens": MAX_TOKENS,
                        }
                    ],
                }
            }
        },
    )
    return {}


def command(frontend, prompt):
    if frontend == "headless":
        return [
            "omp",
            "--mode",
            "json",
            "-p",
            "--model",
            "mock/mock-model",
            "--approval-mode",
            "yolo",
            *prompt,
        ]
    return ["omp", *prompt]


def hashline_patch(step, body, workspace):
    """An edit as a hashline patch: the newest `[PATH#TAG]` header of the file in
    the conversation, then the replacement of the lines of `old` in the file on
    the host."""
    relative = step.path.removeprefix("/workspace/")
    header = re.compile(rf"\[((?:/workspace/)?{re.escape(relative)})#([0-9A-F]{{4}})\]")
    found = [
        m.groups() for text in strings(history(body)) for m in header.finditer(text)
    ]
    if not found:
        raise ValueError(f"No hashline header for {step.path}")
    path, tag = found[-1]
    rows = (workspace / relative).read_text().split("\n")
    old = step.old.split("\n")
    start = next(i for i in range(len(rows)) if rows[i : i + len(old)] == old) + 1
    end = start + len(old) - 1
    new = step.new.split("\n")
    # omp rejects a body that opens with the line above the range. The range
    # then also covers that line, which the body keeps.
    while start > 1 and new[0] == rows[start - 2]:
        start -= 1
        new.insert(0, rows[start - 1])
    return f"[{path}#{tag}]\nPUT {start}.={end}:\n" + "\n".join(
        "+" + row for row in new
    )


def call(step, body, workspace):
    """Every omp tool takes `i`, a short note of what the call is for."""
    note = {"i": f"Run the {step.kind} fixture"}
    match step.kind:
        case "read":
            return "read", note | {"path": step.path}
        case "edit":
            return "edit", note | {"input": hashline_patch(step, body, workspace)}
        case "write":
            return "write", note | {"path": step.path, "content": step.output}
        case "search":
            return "grep", note | {"pattern": step.pattern, "path": step.path}
        case _:
            return "bash", note | {"command": step.command}


AGENT = Agent(
    name="omp",
    version="18.19.0",
    installer="https://omp.sh/install",
    install="curl -fsSL @INSTALLER_BASE@/omp.sh | sh -s -- --binary --ref v@VERSION@",
    executable="omp",
    configure=configure,
    command=command,
    call=call,
    summaries=(
        ("You MUST summarize the conversation above", "structured summary"),
        ("<conversation>\n", "into a structured handoff summary"),
        ("<conversation>\n", "Update existing handoff summary"),
        ("<conversation>\n", "MUST summarize prefix for retained suffix"),
        ("<conversation>\n", "Summarize conversation changes as a pull request"),
        ("", "Write a handoff document for another instance of yourself."),
    ),
    side_requests=(
        "Ephemeral side-channel turn; reuses current conversation context.",
    ),
    # omp refuses an edit of lines that it has not shown under the file's
    # current tag.
    edit_retries=("a straight retry now succeeds",),
)
