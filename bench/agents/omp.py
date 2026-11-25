"""omp's edit is a hashline patch, which a template cannot build."""

import re

from model.requests import history, strings


def hashline_patch(step, body, workspace):
    """An edit as a hashline patch: the newest `[PATH#TAG]` header of the file in
    the conversation, then the replacement of the lines of `old` in the file on
    the host."""
    relative = step.path.removeprefix("/workspace/")
    header = re.compile(rf"\[((?:/workspace/)?{re.escape(relative)})#([0-9A-F]{{4}})\]")
    found = [
        m.groups() for text in strings(history(body)) for m in header.finditer(text)
    ]
    if not found:
        raise ValueError(f"No hashline header for {step.path}")
    path, tag = found[-1]
    rows = (workspace / relative).read_text().split("\n")
    old = step.old.split("\n")
    start = next(i for i in range(len(rows)) if rows[i : i + len(old)] == old) + 1
    end = start + len(old) - 1
    new = step.new.split("\n")
    # omp rejects a body that opens with the line above the range. The range
    # then also covers that line, which the body keeps.
    while start > 1 and new[0] == rows[start - 2]:
        start -= 1
        new.insert(0, rows[start - 1])
    return f"[{path}#{tag}]\nPUT {start}.={end}:\n" + "\n".join(
        "+" + row for row in new
    )


PLACEHOLDERS = {"hashline_patch": hashline_patch}
