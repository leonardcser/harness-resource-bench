"""OpenCode keeps results in its checkpoint, which a template cannot read."""

import json
import re

from model.requests import history


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
