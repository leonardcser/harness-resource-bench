from agents import CONTEXT_WINDOW, KEY, MAX_TOKENS, Agent, write_json

NODE_VERSION = "22.23.4"
NODE_ARCHIVE = f"node-v{NODE_VERSION}-linux-x64.tar.xz"
NODE = (
    f"curl -fsSL https://nodejs.org/dist/v{NODE_VERSION}/{NODE_ARCHIVE} -o /tmp/{NODE_ARCHIVE}"
    f" && curl -fsSL https://nodejs.org/dist/v{NODE_VERSION}/SHASUMS256.txt -o /tmp/node-sums"
    f" && (cd /tmp && grep ' {NODE_ARCHIVE}$' node-sums | sha256sum -c -)"
    f" && tar -xJf /tmp/{NODE_ARCHIVE} -C /usr/local --strip-components=1"
    f" && rm /tmp/{NODE_ARCHIVE} /tmp/node-sums"
)


def configure(frontend, home, url, prompt):
    write_json(home / ".pi/agent/settings.json", {"defaultProjectTrust": "always"})
    write_json(
        home / ".pi/agent/models.json",
        {
            "providers": {
                "mock": {
                    "baseUrl": url + "/v1",
                    "api": "openai-completions",
                    "apiKey": KEY,
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
    args = ["pi", "--provider", "mock", "--model", "mock-model"]
    if frontend == "headless":
        args += ["--mode", "json", "-p"]
    return {}, args + prompt


def call(step, body, workspace):
    """pi has no search tool, so a search runs in the shell."""
    match step.kind:
        case "read":
            return "read", {"path": step.path}
        case "edit":
            return "edit", {
                "path": step.path,
                "edits": [{"oldText": step.old, "newText": step.new}],
            }
        case "write":
            return "write", {"path": step.path, "content": step.output}
        case _:
            return "bash", {"command": step.command}


AGENT = Agent(
    name="pi",
    version="1.5.0",
    installer="https://pi.dev/install.sh",
    install=f"{NODE} && curl -fsSL @INSTALLER_BASE@/pi.sh"
    " | PI_INSTALLER_API_BASE=@INSTALLER_BASE@/pi sh",
    executable="pi",
    configure=configure,
    call=call,
    summaries=(
        ("<conversation>\n", "Keep each section concise."),
        ("# Conversation\n", "Create a concise checkpoint of the user's request"),
    ),
)
