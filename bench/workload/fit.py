#!/usr/bin/env python3
"""Fit the workload profile to a local smelt session store, read-only.

    uv run --group fit workload/fit.py [~/.local/state/smelt/smelt.db] > workload/profile.json

Reads the history that the model saw in every top-level session. Writes only
aggregates, which are quantiles of sizes and counts, and shares. No session text
leaves the store.

A turn runs from one user message to the next. Each tool call is one step,
because the benchmark's model serves one call per response. So a response with
several parallel calls becomes several steps, and its reasoning and text go on
the first. The response that ends a turn without a call is the final answer of
the turn. Sizes are UTF-8 bytes of what the model saw. This is the visible
reasoning, the assistant text, the argument JSON of the call and the result.
"""

import json
import math
import sqlite3
import sys
from pathlib import Path

import zstandard

STORE = Path("~/.local/state/smelt/smelt.db").expanduser()
# Points of every quantile table. The workload samples between them. So the
# few largest values do not set the tail.
POINTS = (0, 0.01, 0.025, 0.05, *(i / 10 for i in range(1, 10)))
POINTS += (0.95, 0.975, 0.99, 0.995, 0.999)
# Tool kinds that the workload knows. Any other tool counts as a shell command.
KINDS = {
    "read_file": "read",
    "edit_file": "edit",
    "write_file": "write",
    "grep": "search",
    "glob": "search",
}

decompressor = zstandard.ZstdDecompressor()


def unpack(cell):
    """The bytes of a cell. The first byte is 0 for raw bytes and 1 for zstd."""
    return decompressor.decompress(cell[1:]) if cell[0] == 1 else cell[1:]


def varint(data, at):
    value, shift = 0, 0
    while True:
        byte = data[at]
        value |= (byte & 0x7F) << shift
        at, shift = at + 1, shift + 7
        if byte < 0x80:
            return value, at


def decode(db, body):
    """A history body as JSON. A body that starts with 2 keeps its large strings
    in `blobs`: a count, then pairs of offset delta and blob id that say where
    each goes back into the skeleton that follows."""
    if body[0] != 2:
        return json.loads(unpack(body))
    count, at = varint(body, 1)
    parts = []
    for _ in range(count):
        delta, at = varint(body, at)
        blob, at = varint(body, at)
        parts.append((delta, blob))
    skeleton = unpack(body[at:])
    out, start = [], 0
    for delta, blob in parts:
        out.append(skeleton[start : start + delta])
        (data,) = db.execute("select data from blobs where id = ?", (blob,)).fetchone()
        out.append(unpack(data))
        start += delta
    out.append(skeleton[start:])
    return json.loads(b"".join(out))


def size(value):
    return len((value or "").encode())


def quantiles(values):
    values = sorted(values)
    if not values:
        return []
    table = []
    for p in POINTS:
        at = p * (len(values) - 1)
        low, high = values[math.floor(at)], values[math.ceil(at)]
        table.append(round(low + (high - low) * (at - math.floor(at)), 1))
    return table


def turns(store):
    """Every turn of every top-level session, as steps and a final answer.

    ({"reasoning", "text", "kind", "arguments", "result"}, ...), {"reasoning", "text"}
    """
    db = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
    top = {
        sid for (sid,) in db.execute("select sid from sessions where parent_id is null")
    }
    rows = db.execute("select sid, body from history order by sid, idx")
    current, steps, pending = None, [], {"reasoning": 0, "text": 0}
    for sid, body in rows:
        if sid not in top:
            continue
        message = decode(db, body)
        kind = message["kind"]
        if kind == "user" or sid != current:
            if current is not None and (steps or any(pending.values())):
                yield steps, pending
            current, steps, pending = sid, [], {"reasoning": 0, "text": 0}
            continue
        if kind != "assistant":
            continue
        pending["reasoning"] += size(message.get("reasoning"))
        pending["text"] += size(message.get("content"))
        for call in message.get("invocations", []):
            result = call.get("result") or {}
            steps.append(
                dict(
                    pending,
                    kind=KINDS.get(call["name"], "shell"),
                    arguments=size(call.get("arguments")),
                    result=size(result.get("content")),
                )
            )
            pending = {"reasoning": 0, "text": 0}
    if current is not None and (steps or any(pending.values())):
        yield steps, pending


def share(part, whole):
    return round(part / whole, 4) if whole else 0


def fit(store):
    calls, reasoning, text, final_reasoning, final_text = [], [], [], [], []
    tools = {}
    all_steps = []
    for steps, final in turns(store):
        calls.append(len(steps))
        all_steps += steps
        reasoning += [s["reasoning"] for s in steps if s["reasoning"]]
        text += [s["text"] for s in steps if s["text"]]
        final_reasoning.append(final["reasoning"])
        final_text.append(final["text"])
        for step in steps:
            tools.setdefault(step["kind"], []).append(step)
    count = len(all_steps)
    return {
        "source": {"turns": len(calls), "steps": count},
        "points": POINTS,
        "turn": {"calls": quantiles(calls)},
        "step": {
            "reasoning": share(len(reasoning), count),
            "reasoning_bytes": quantiles(reasoning),
            "text": share(len(text), count),
            "text_bytes": quantiles(text),
        },
        "final": {
            "reasoning": share(sum(1 for v in final_reasoning if v), len(calls)),
            "reasoning_bytes": quantiles([v for v in final_reasoning if v]),
            "text": share(sum(1 for v in final_text if v), len(calls)),
            "text_bytes": quantiles([v for v in final_text if v]),
        },
        "tools": {
            kind: {
                "share": share(len(steps), count),
                "arguments_bytes": quantiles([s["arguments"] for s in steps]),
                "result_bytes": quantiles([s["result"] for s in steps]),
            }
            for kind, steps in sorted(tools.items(), key=lambda kv: -len(kv[1]))
        },
    }


def main():
    store = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else STORE
    json.dump(fit(store), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
