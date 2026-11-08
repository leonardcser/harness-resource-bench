from agents import CONTEXT_WINDOW, Agent


def configure(frontend, home, url, prompt):
    # Codex cuts tool output at 10 KB for a model it does not know. Its own
    # models cut at 10,000 tokens, so the mock model gets that limit.
    (home / ".codex").mkdir()
    (home / ".codex/config.toml").write_text(f'''model_provider = "mock"
model = "mock-model"
model_context_window = {CONTEXT_WINDOW}
tool_output_token_limit = 10000
check_for_update_on_startup = false
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
    args = ["codex"]
    if frontend == "headless":
        args += ["exec", "--skip-git-repo-check", "--json"]
    else:
        args += ["--no-daemon"]
    return {}, [*args, "--dangerously-bypass-approvals-and-sandbox", *prompt]


def call(step, body, workspace):
    """Codex runs every step in its shell. An edit is an apply_patch command."""
    return "exec_command", {"cmd": step.command}


AGENT = Agent(
    name="codex",
    version="0.167.0",
    installer="https://chatgpt.com/codex/install.sh",
    install="curl -fsSL @INSTALLER_BASE@/codex.sh"
    " | CODEX_NON_INTERACTIVE=1 sh -s -- --release @VERSION@",
    executable="codex",
    configure=configure,
    call=call,
    summaries=(
        ("You are performing a CONTEXT CHECKPOINT COMPACTION.", "handoff summary"),
    ),
    assets=(".codex/.tmp", ".codex/skills/.system"),
)
