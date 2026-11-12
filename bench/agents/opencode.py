import json

from agents import CONTEXT_WINDOW, KEY, MAX_TOKENS, Agent


def configure(home, url):
    config = {
        "model": "mock/mock-model",
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
        args = ["opencode", "run", "--format", "json", "--standalone", "--auto"]
        return args + prompt
    args = ["opencode", "--standalone", "--auto"]
    if prompt:
        args += ["--prompt", *prompt]
    return args


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


AGENT = Agent(
    name="opencode",
    version="2.2.6",
    installer="https://opencode.ai/v2/install",
    install="curl -fsSL @INSTALLER_BASE@/opencode.sh | bash -s -- --version @VERSION@",
    executable="opencode",
    configure=configure,
    command=command,
    call=call,
    summaries=(
        ("<conversation>\n", "Keep each section concise."),
        ("You MUST summarize the conversation above", "structured summary"),
        (
            "Update the existing checkpoint in the conversation above",
            "structured summary",
        ),
        ("The previous response did not fill in the required summary template.", ""),
    ),
    assets=(".local/share/opentui",),
)
