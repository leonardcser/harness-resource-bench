from agents import KEY, Agent, write_json


def configure(home, url):
    write_json(
        home / ".claude.json",
        {
            "hasCompletedOnboarding": True,
            "projects": {"/workspace": {"hasTrustDialogAccepted": True}},
            "theme": "dark",
            "customApiKeyResponses": {"approved": [KEY[-20:]], "rejected": []},
            "bypassPermissionsModeAccepted": True,
            "hasSeenAutoDefaultNudge": True,
            "hasSeenAutoDefaultNotice": True,
            "hasResetAutoModeOptInForDefaultOffer": True,
        },
    )
    write_json(
        home / ".claude/settings.json",
        {"permissions": {"defaultMode": "bypassPermissions"}, "enabledPlugins": {}},
    )
    return {"ANTHROPIC_BASE_URL": url}


def command(frontend, prompt):
    args = ["claude", "--model", "claude-sonnet-4-6", "--dangerously-skip-permissions"]
    if frontend == "headless":
        args += ["--print", "--output-format", "stream-json", "--verbose"]
    return args + prompt


def call(step, body, workspace):
    """Claude Code offers no search tool to this model, so a search runs in the
    shell."""
    match step.kind:
        case "read":
            return "Read", {"file_path": step.path}
        case "edit":
            return "Edit", {
                "file_path": step.path,
                "old_string": step.old,
                "new_string": step.new,
            }
        case "write":
            return "Write", {"file_path": step.path, "content": step.output}
        case _:
            return "Bash", {"command": step.command}


AGENT = Agent(
    name="claude-code",
    version="2.1.322",
    installer="https://claude.ai/install.sh",
    install="curl -fsSL @INSTALLER_BASE@/claude-code.sh | bash -s -- @VERSION@",
    executable="claude",
    configure=configure,
    command=command,
    call=call,
    summaries=(
        (
            "CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.",
            "Your task is to create a detailed summary of the conversation so far",
        ),
    ),
    reset="/clear",
    # It clones the official plugin marketplace, then lists it in this file.
    background_setup=".claude/plugins/known_marketplaces.json",
)
