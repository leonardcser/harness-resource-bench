import json
import re

from agents import CONTEXT_WINDOW, KEY, MAX_TOKENS, Agent
from model.requests import history


def configure(home, url):
    config = {
        "model": "mock/mock-model",
        "permissions": [{"action": "*", "resource": "*", "effect": "allow"}],
        "providers": {
            "mock": {
                "package": "@opencode/ai/providers/openai-compatible",
                "settings": {"baseURL": url + "/v1", "apiKey": KEY},
                "models": {
                    "mock-model": {
                        "limit": {"context": CONTEXT_WINDOW, "output": MAX_TOKENS},
                        "capabilities": {
                            "tools": True,
                            "reasoning": {"supported": True},
                        },
                    }
                },
            }
        },
    }
    return {"OPENCODE_CONFIG_CONTENT": json.dumps(config)}


def command(frontend, prompt):
    if frontend == "headless":
        return [
            "opencode",
            "run",
            "--format",
            "json",
            "--standalone",
            "--auto",
            *prompt,
        ]
    return ["opencode", "--prompt", *prompt] if prompt else ["opencode"]


def call(step, body, workspace):
    match step.kind:
        case "read":
            return "read", {"path": step.path}
        case "edit":
            return "edit", {
                "path": step.path,
                "oldString": step.old,
                "newString": step.new,
            }
        case "write":
            return "write", {"path": step.path, "content": step.output}
        case "search":
            return "grep", {"pattern": step.pattern, "path": step.path, "literal": True}
        case _:
            return "shell", {"command": step.command}


def checkpoint_results(body, name, args):
    """The results of a call that OpenCode keeps as text beside its summary.

    OpenCode writes the summary in the background and applies it later,
    without a new compaction request. The checkpoint can then hold the only
    copy of the latest result."""
    prefix = f"[Assistant tool call]: {name}("
    returned = []
    for message in history(body):
        text = message.get("content")
        if (
            message.get("role") != "user"
            or not isinstance(text, str)
            or not text.startswith("<conversation-checkpoint>\n")
            or not text.endswith("\n</conversation-checkpoint>")
        ):
            continue
        recent = text.partition("\n</summary>\n\n<recent-context>\n")[2]
        recent = recent.removesuffix("\n</recent-context>\n</conversation-checkpoint>")
        blocks = re.split(
            r"(?m)^(?=\[(?:Assistant tool call|Assistant|User|Shell|Synthetic context)\]: )",
            recent,
        )
        for block in blocks:
            header, _, result = block.partition("\n")
            if not header.startswith(prefix) or not header.endswith(")"):
                continue
            try:
                actual = json.loads(header[len(prefix) : -1])
            except json.JSONDecodeError:
                continue
            if actual != args:
                continue
            label, _, content = result.partition(": ")
            if label in ("[Tool result]", "[Tool error]"):
                returned.append(
                    {"content": content, "is_error": label == "[Tool error]"}
                )
    return returned


AGENT = Agent(
    name="opencode",
    version="2.3.2",
    installer="https://opencode.ai/v2/install",
    install="curl -fsSL @INSTALLER_BASE@/opencode.sh | bash -s -- --version @VERSION@",
    executable="opencode",
    configure=configure,
    server=True,
    command=command,
    call=call,
    checkpoint_results=checkpoint_results,
    summaries=(
        ("<conversation>\n", "Keep each section concise."),
        ("You MUST summarize the conversation above", "structured summary"),
        (
            "Update the existing checkpoint in the conversation above",
            "structured summary",
        ),
        ("The previous response did not fill in the required summary template.", ""),
    ),
)
