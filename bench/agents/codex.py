from agents import CONTEXT_WINDOW, Agent, write_json


def configure(home, url):
    # Codex cuts tool output at 10 KB for a model it does not know. Its own
    # models cut at 10,000 tokens, so the mock model gets that limit.
    (home / ".codex").mkdir()
    (home / ".codex/config.toml").write_text(f'''model_provider = "mock"
model = "mock-model"
model_context_window = {CONTEXT_WINDOW}
tool_output_token_limit = 10000
check_for_update_on_startup = false
approval_policy = "never"
sandbox_mode = "danger-full-access"
[model_providers.mock]
name = "benchmark"
base_url = "{url}/v1"
wire_api = "responses"
env_key = "OPENAI_API_KEY"
supports_websockets = false
[analytics]
enabled = false
[feedback]
enabled = false
''')
    # Its shared server has its own updater.
    write_json(
        home / ".codex/app-server-daemon/settings.json",
        {"updater": {"autoUpdateEnabled": False}},
    )
    return {}


def command(frontend, prompt):
    if frontend == "headless":
        return [
            "codex",
            "exec",
            "--json",
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            *prompt,
        ]
    return ["codex", *prompt]


def call(step, body, workspace):
    """Codex runs every step in its shell. An edit is an apply_patch command."""
    return "exec_command", {"cmd": step.command}


AGENT = Agent(
    name="codex",
    version="0.167.2",
    installer="https://chatgpt.com/codex/install.sh",
    install="curl -fsSL @INSTALLER_BASE@/codex.sh"
    " | CODEX_NON_INTERACTIVE=1 sh -s -- --release @VERSION@",
    executable="codex",
    configure=configure,
    command=command,
    call=call,
    summaries=(
        ("You are performing a CONTEXT CHECKPOINT COMPACTION.", "handoff summary"),
    ),
    # It clones its plugin repository to a temporary folder, then renames it.
    background_setup=".codex/.tmp/plugins",
    server=True,
)
