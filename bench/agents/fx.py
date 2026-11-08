from agents import CONTEXT_WINDOW, MAX_TOKENS, Agent, write_json


def configure(frontend, home, url, prompt):
    settings = home / ".fx/settings.json"
    write_json(
        settings,
        {
            "provider": "mock",
            "models": {"mock": "mock-model"},
            "providers": {
                "mock": {
                    "protocol": "openai-chat-completions",
                    # fx accepts plain HTTP only on loopback.
                    "base_url": url + "/v1",
                    "auth": {"type": "bearer", "env": "MOCK_KEY"},
                    "model_metadata": {
                        "mock-model": {
                            "context_window": CONTEXT_WINDOW,
                            "max_output_tokens": MAX_TOKENS,
                            "supports_tool_use": True,
                        }
                    },
                }
            },
            "permission_mode": "full-access",
            "yolo_acknowledged": True,
            "auto_upgrade": False,
        },
    )
    settings.parent.chmod(0o700)
    settings.chmod(0o600)
    if frontend == "headless":
        return {}, ["fx", "ask", "--full-access", "--json", *prompt]
    return {}, ["fx"]


def call(step, body, workspace):
    match step.kind:
        case "read":
            return "read_file", {"path": step.path}
        case "edit":
            return "edit_file", {
                "path": step.path,
                "old_string": step.old,
                "new_string": step.new,
            }
        case "write":
            return "write_file", {"path": step.path, "content": step.output}
        case "search":
            return "grep_files", {
                "pattern": step.pattern,
                "path": step.path,
                "mode": "matches",
            }
        case _:
            return "shell", {"action": "run", "command": step.command}


AGENT = Agent(
    name="fx",
    version="0.0.16",
    installer="https://fx.sh/setup.sh",
    install="curl -fsSL @INSTALLER_BASE@/fx.sh | bash -s -- v@VERSION@",
    executable="fx",
    configure=configure,
    call=call,
    # fx asks for its notes under exact turn headings, and asks again if one is
    # missing. The model's summary has a heading for each turn that it names.
    summaries=(
        ("", "Write the compaction notes for the"),
        ("", "Your notes on the turns above left some out."),
        ("", "Your notes left out the summary of the earlier"),
    ),
    typed_prompt=True,
)
