"""Generated coding work with the shape of real sessions, from a seed. It uses
no session content. `profile.json` holds only size quantiles and shares, which
`fit.py` makes."""

import functools
import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

SEED = 20261103
PROFILE_PATH = Path(__file__).parent / "profile.json"
PROFILE = json.loads(PROFILE_PATH.read_text())
# Streamed bytes per delta. Four bytes is one reference token.
CHUNK_BYTES = 32
PROMPT = "BENCH_TURN_{turn:06d}: inspect the fixture, apply the requested update, and explain the result."
# Where the agent finds the read-only output that shell commands print, and the
# sources that it reads, searches, edits and writes.
FIXTURES = "/workspace/fixtures"
SOURCES = "/workspace/src"
SENTENCES = (
    "The parser retains a partial record until the next chunk arrives.",
    "Check the cursor boundary before replacing text in the buffer.",
    "This update preserves the existing session history and cache entries.",
    "The fixture covers an empty input, a normal result, and a missing key.",
    "Use the request index to associate each tool result with its caller.",
    "The expected output is deterministic and does not require network access.",
    "The layout wraps long rows at the cell width and keeps the cursor visible.",
    "A stale frame redraws only the rows whose cells changed.",
)
NAMES = (
    "buffer", "cursor", "frame", "render", "session", "history", "cache",
    "index", "layout", "width", "row", "cell", "state", "event", "request",
    "chunk", "theme", "scroll",
)  # fmt: skip
TYPES = ("Buffer", "Frame", "Session", "Cursor", "Layout", "Request", "Cell")
PATHS = (
    "src/render/frame.rs",
    "src/session/store.rs",
    "src/input/cursor.rs",
    "src/layout/wrap.rs",
    "src/model/request.rs",
    "tests/render.rs",
)
HEX = "0123456789abcdef"


def sample(rng, table):
    """A random value from a quantile table of `PROFILE["points"]`, between its
    points in log space. A draw above the last point gets the last value."""
    points = PROFILE["points"]
    u = rng.random()
    if u >= points[-1]:
        return table[-1]
    i = next(i for i in range(1, len(points)) if u < points[i])
    t = (u - points[i - 1]) / (points[i] - points[i - 1])
    low, high = math.log1p(table[i - 1]), math.log1p(table[i])
    return math.expm1(low + (high - low) * t)


def code(rng):
    a, b, c = rng.sample(NAMES, 3)
    kind = rng.choice(TYPES)
    indent = "    " * rng.choice((0, 1, 1, 2, 2, 3))
    return indent + rng.choice(
        (
            f"let {a} = self.{b}.{c}({a}_{b});",
            f"if {a}.is_empty() {{ return None; }}",
            f"fn {a}_{b}(&mut self, {c}: usize) -> Option<{kind}> {{",
            f"// Keep the {a} in sync with the {b}.",
            f"self.{a}.push({kind}::new({b}, {c}));",
            "}",
            f"match self.{a} {{ Some({b}) => {b}.{c}(), None => {kind}::default() }}",
        )
    )


def shell(rng):
    a, b = rng.sample(NAMES, 2)
    rows = (
        lambda: f"   Compiling {a}-core v1.4.0",
        lambda: f"test {a}::{b}_keeps_{rng.choice(NAMES)} ... ok",
        lambda: (
            "".join(rng.choice(HEX) for _ in range(9)) + f" fix({a}): keep {b} in sync"
        ),
        lambda: (
            f"{rng.choice(PATHS)} | {rng.randint(1, 90)} {'+' * rng.randint(1, 20)}"
        ),
        lambda: code(rng),
    )
    return rng.choice(rows)()


def lines(rng, size, line):
    """Whole `line(rng, number)` rows, numbered from a random line, until
    they hold `size` bytes."""
    rows, total, number = [], 0, rng.randint(1, 400)
    while total < size:
        rows.append(line(rng, number))
        total += len(rows[-1]) + 1
        number += 1
    return "\n".join(rows)


def prose(rng, size):
    """Assistant text: paragraphs and bullet lists with inline code."""
    parts, total = [], 0
    while total < size:
        if rng.random() < 0.3:
            part = "\n".join(
                f"- `{rng.choice(NAMES)}`: {rng.choice(SENTENCES)}"
                for _ in range(rng.randint(2, 4))
            )
        else:
            part = " ".join(rng.choice(SENTENCES) for _ in range(rng.randint(1, 3)))
        parts.append(part)
        total += len(part) + 2
    return "\n\n".join(parts)[:size].rstrip()


def answer(rng, size):
    """A final answer: prose, sometimes with a code block."""
    if size < 300 or rng.random() < 0.7:
        return prose(rng, size)
    block = "```rust\n" + lines(rng, size // 3, lambda r, _: code(r)) + "\n```"
    return prose(rng, size - len(block) - 2) + "\n\n" + block


def thinking(rng, size):
    return " ".join(rng.choice(SENTENCES) for _ in range(size // 60 + 1))[:size]


def tagged(rng, size, tag):
    """Code rows that each name `tag`, as a search for it finds them."""
    return lines(rng, size, lambda r, _: f"{code(r).strip()}  // {tag}")


def shell_command(rng, path, size):
    """A shell command of about `size` bytes that prints the fixture at
    `path`. The rest is a script body that the shell ignores."""
    head = f"cat {path}"
    rest = size - len(head)
    if rest < 120:
        comment = ""
        while len(comment) < rest - 4:
            comment += " " + rng.choice(SENTENCES)
        return f"{head}  # {comment.strip()}"[:size].rstrip() if rest > 4 else head
    return f"{head}\n: <<'EOF'\n{lines(rng, rest - 12, lambda r, _: shell(r))}\nEOF"


def patch(body):
    return f"apply_patch <<'PATCH'\n*** Begin Patch\n{body}\n*** End Patch\nPATCH"


def prefixed(mark, text):
    return "\n".join(mark + row for row in text.split("\n"))


@dataclass(frozen=True)
class Step:
    """One tool call.

    `path` is the file that it reads, searches, edits or writes. `output` is
    what it prints, or the content that a write creates. An edit replaces `old`
    with `new`, in the file of an earlier read. `command` does the same through
    the shell, for an agent without its own tool for the kind.
    """

    kind: str
    thinking: str
    answer: str
    path: str
    command: str
    output: str = ""
    old: str = ""
    new: str = ""

    @property
    def pattern(self):
        """What a search looks for: the first line that it prints."""
        return self.output.split("\n", 1)[0]


def tag(turn, index):
    return f"fixture-{turn:06d}-{index:03d}"


@functools.cache
def steps(turn, calls=None, seed=SEED):
    """The tool calls of one turn. There are `calls` calls, or as many as a
    real turn has when `calls` is None. An edit changes the file of the last
    read in the turn, because agents edit only files that they read. With no
    earlier read, an edit becomes a read."""
    rng = random.Random(seed + turn)
    profile, tools = PROFILE["step"], PROFILE["tools"]
    if calls is None:
        calls = round(sample(rng, PROFILE["turn"]["calls"]))
    kinds = list(tools)
    drawn, read = [], None
    for index in range(calls):
        kind = rng.choices(kinds, [tools[k]["share"] for k in kinds])[0]
        if kind == "edit" and read is None:
            kind = "read"
        if kind == "read":
            read = index
        drawn.append(
            {
                "kind": kind,
                "target": read,
                "result": round(sample(rng, tools[kind]["result_bytes"])),
                "arguments": round(sample(rng, tools[kind]["arguments_bytes"])),
                "thinking": thinking(
                    rng, round(sample(rng, profile["reasoning_bytes"]))
                )
                if rng.random() < profile["reasoning"]
                else "",
                "answer": prose(rng, round(sample(rng, profile["text_bytes"])))
                if rng.random() < profile["text"]
                else "",
            }
        )
    paths = [
        f"{FIXTURES}/{tag(turn, i)}.txt"
        if d["kind"] == "shell"
        else f"{SOURCES}/{rng.choice(NAMES)}_{turn:06d}_{i:03d}.rs"
        for i, d in enumerate(drawn)
    ]
    # Each edit replaces a block that only this edit names. So the replacement is
    # unique and the host sees that it changed the file. Its read prints the block.
    edits = {}
    for index, d in enumerate(drawn):
        if d["kind"] == "edit":
            payload = max(80, d["arguments"] - len(paths[d["target"]]) - 40)
            old = f"// {tag(turn, index)}\n" + lines(
                rng, payload * 2 // 5, lambda r, _: code(r)
            )
            new = lines(rng, payload * 3 // 5, lambda r, _: code(r))
            edits.setdefault(d["target"], []).append(
                (index, old.rstrip(), new.rstrip())
            )
    result = []
    for index, d in enumerate(drawn):
        kind, path, header = d["kind"], paths[index], tag(turn, index)
        size = max(0, d["result"] - len(header) - 1)
        common = {
            "kind": kind,
            "thinking": d["thinking"],
            "answer": d["answer"],
            "path": path,
        }
        if kind == "shell":
            output = f"{header}\n" + lines(rng, size, lambda r, _: shell(r))
            command = shell_command(rng, path, d["arguments"])
            result.append(Step(**common, command=command, output=output))
        elif kind == "read":
            rows = lines(rng, size, lambda r, _: code(r)).split("\n")
            for _, old, _ in edits.get(index, []):
                rows.insert(rng.randint(0, len(rows)), old)
            output = f"{header}\n" + "\n".join(rows)
            result.append(Step(**common, command=f"cat -n {path}", output=output))
        elif kind == "search":
            output = f"{header}\n" + tagged(rng, size, header)
            command = f"grep -n '{header}' {path}"
            result.append(Step(**common, command=command, output=output))
        elif kind == "edit":
            target = paths[d["target"]]
            old, new = next((o, n) for i, o, n in edits[d["target"]] if i == index)
            hunk = f"*** Update File: {target}\n@@\n{prefixed('-', old)}\n{prefixed('+', new)}"
            common["path"] = target
            result.append(Step(**common, command=patch(hunk), old=old, new=new))
        else:
            content = lines(
                rng, max(1, d["arguments"] - len(path) - 40), lambda r, _: code(r)
            )
            hunk = f"*** Add File: {path}\n{prefixed('+', content)}"
            result.append(Step(**common, command=patch(hunk), output=content))
    return tuple(result)


def files(turn, calls=None, seed=SEED):
    """The files to prepare for one turn, by path under the root of the case.
    These are the fixtures that shell commands print, mounted at `FIXTURES`,
    and the sources in the workspace that reads and searches find."""
    prepared = {}
    for step in steps(turn, calls, seed):
        if step.kind == "shell":
            prepared[step.path.removeprefix("/workspace/")] = step.output
        elif step.kind in ("read", "search"):
            prepared[step.path.removeprefix("/")] = step.output
    return prepared


def marker(turn):
    return f"BENCH_DONE_{turn:06d}"


@functools.cache
def final_answer(turn, seed=SEED):
    """The reasoning and text that end a turn; the text ends with its marker."""
    rng = random.Random(seed + 1_000_000 + turn)
    final = PROFILE["final"]
    reasoning = (
        thinking(rng, round(sample(rng, final["reasoning_bytes"])))
        if rng.random() < final["reasoning"]
        else ""
    )
    text = (
        answer(rng, round(sample(rng, final["text_bytes"])))
        if rng.random() < final["text"]
        else ""
    )
    return reasoning, f"{text}\n{marker(turn)}" if text else marker(turn)


def transcript(turns, calls=None, seed=SEED):
    """What the model sends over `turns` turns. Each turn has the prompt, its
    tool calls and the final answer."""
    return [
        {
            "prompt": PROMPT.format(turn=t),
            "steps": [vars(s) for s in steps(t, calls, seed)],
            "final": dict(zip(("thinking", "answer"), final_answer(t, seed))),
        }
        for t in range(turns)
    ]


def text_bytes(turns, calls=None, seed=SEED):
    """Bytes of the tool calls, tool output and answers over `turns` turns."""
    return sum(
        len(value.encode())
        for turn in transcript(turns, calls, seed)
        for part in (*turn["steps"], turn["final"])
        for key, value in part.items()
        if key != "kind" and isinstance(value, str)
    )


def digest(turns, calls):
    payload = json.dumps(transcript(turns, calls), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def chunks(value):
    # Generated content is ASCII, so byte and character boundaries agree.
    return [value[i : i + CHUNK_BYTES] for i in range(0, len(value), CHUNK_BYTES)]
