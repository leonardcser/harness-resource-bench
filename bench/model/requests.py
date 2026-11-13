"""What a request to the mock model holds, in any of the three API formats."""

import json
import re

# The context window of every agent. Like a provider, the model counts 4 request
# bytes as one token and rejects larger requests.
CONTEXT_TOKENS = 200_000


def strings(value):
    if isinstance(value, str):
        yield value
        if value.startswith(("{", "[")):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return
            yield from strings(decoded)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)


SUMMARY_SECTIONS = "\n".join(
    f"{heading}\nFixture workflow state."
    for heading in (
        "# Goal",
        "# Current focus",
        "# Constraints",
        "# Progress",
        "# Decisions",
        "# Next steps",
        "# Critical context",
        "# Relevant files",
        "## Objective",
        "## Requirements",
        "## Decisions",
        "## Work State",
        "### Completed",
        "### Active",
        "### Blocked",
        "## Next Move",
        "## Relevant Files",
        "## Important Context",
    )
)


def history(body):
    """The messages of a request, in any of the three API formats."""
    return body.get("messages", body.get("input", []))


def tail(body):
    """The user messages after the agent's last answer, newest first. System
    notes between them, such as a reminder, do not end the tail."""
    messages = history(body)
    found = []
    for message in reversed(messages if isinstance(messages, list) else []):
        role = message.get("role") if isinstance(message, dict) else None
        if role == "system":
            continue
        if role != "user":
            break
        found.append(message)
    return found


def instruction(body):
    """The texts of the last user message."""
    last = tail(body)[:1]
    return [text for message in last for text in strings(message.get("content", []))]


def is_side_request(body, agent):
    """Whether the user messages after the last answer carry one of the agent's
    side request marks."""
    return any(
        mark in text for text in strings(tail(body)) for mark in agent.side_requests
    )


def is_compaction(body, agent):
    """Whether the last user message is one of the agent's summary prompts."""
    return any(
        text.startswith(start) and mark in text
        for text in instruction(body)
        for start, mark in agent.summaries
    )


def summary(body, turn):
    # fx asks for its notes under exact turn headings.
    headings = [
        f"{heading}\nIn between: none."
        for text in instruction(body)
        for heading in re.findall(r"^Turn (?:\d+|in progress)", text, re.MULTILINE)
    ]
    return "\n".join(
        [
            "<summary>",
            SUMMARY_SECTIONS,
            *headings,
            f"Resume at BENCH_TURN_{turn:06d}.",
            "</summary>",
        ]
    )


def describe(path, body):
    """What a side request is, in short: where it went, the model, the tools
    it offered, and the start of its system prompt and of its last message."""
    messages = history(body)
    system = body.get("system", body.get("instructions")) or [
        m for m in messages if isinstance(m, dict) and m.get("role") == "system"
    ]
    last = messages[-1] if isinstance(messages, list) and messages else messages
    return {
        "path": path,
        "model": body.get("model"),
        "tools": len(body.get("tools") or []),
        "system": " ".join(strings(system))[:160],
        "last": " ".join(strings(last))[:240],
    }


def request_details(body, turn, matches):
    """What a request held, to diagnose a failure: its newest messages."""
    messages = history(body)
    return {
        "turn": turn,
        "markers": matches[-12:],
        "request_bytes": len(json.dumps(body).encode()),
        "last_messages": [
            {
                "role": m.get("role", m.get("type")),
                "keys": sorted(m),
                "text": " ".join(strings(m))[:400],
            }
            for m in messages[-6:]
            if isinstance(m, dict)
        ],
    }


def results(value):
    if isinstance(value, list):
        for child in value:
            yield from results(child)
    elif isinstance(value, dict):
        if (
            value.get("type") in ("tool_result", "function_call_output")
            or value.get("role") == "tool"
        ):
            yield value
        else:
            for child in value.values():
                yield from results(child)


def results_of(body, call_id):
    """The tool results in a request that answer `call_id`."""
    return [
        result
        for result in results(body)
        if result.get("tool_use_id", result.get("tool_call_id", result.get("call_id")))
        == call_id
    ]
