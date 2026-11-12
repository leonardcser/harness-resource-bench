import json

from agents import CONTEXT_WINDOW, MAX_TOKENS, Agent


def configure(home, url):
    config = home / ".config/smelt/init.lua"
    config.parent.mkdir(parents=True)
    config.write_text(
        'smelt.provider.register("mock", { type = "openai-compatible", api_base = '
        + json.dumps(url + "/v1")
        + ', api_key_env = "MOCK_KEY", models = { { name = "mock-model",'
        f" context_window = {CONTEXT_WINDOW}, max_tokens = {MAX_TOKENS},"
        " supports_reasoning = true } } })\n"
        'smelt.defaults.set({ model = "mock/mock-model" })\n'
        'smelt.settings.autoupgrade = "off"\n'
    )
    return {}


def command(frontend, prompt):
    args = ["smelt", "--model", "mock/mock-model", "--mode", "yolo"]
    if frontend == "headless":
        args += ["--headless", "--format", "json"]
    return args + prompt


def call(step, body, workspace):
    match step.kind:
        case "read":
            return "read_file", {"file_path": step.path}
        case "edit":
            return "edit_file", {
                "file_path": step.path,
                "old_string": step.old,
                "new_string": step.new,
            }
        case "write":
            return "write_file", {"file_path": step.path, "content": step.output}
        case "search":
            return "grep", {
                "pattern": step.pattern,
                "path": step.path,
                "output_mode": "content",
                "-n": True,
            }
        case _:
            return "bash", {"command": step.command}


AGENT = Agent(
    name="smelt",
    version="0.8.0",
    installer="https://smeltagent.dev/install.sh",
    install="curl -fsSL @INSTALLER_BASE@/smelt.sh | SMELT_VERSION=v@VERSION@ sh",
    executable="smelt",
    configure=configure,
    command=command,
    call=call,
    summaries=(
        ("The conversation above is becoming long.", "CONTEXT CHECKPOINT COMPACTION"),
        ("You are performing a CONTEXT CHECKPOINT COMPACTION.", "handoff summary"),
    ),
)
