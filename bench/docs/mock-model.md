# Mock model

**Protocol**

- It streams the Chat Completions, Responses or Anthropic Messages format, 32
  bytes per delta.
- One token is 4 bytes, not a provider's tokenizer count. Usage reports this
  count.
- It rejects a request over 200k tokens with the protocol's context-length
  error.

**Checks** on every tool result, call ID, turn history and request count:

- A missing, failed or unrelated result fails the run.
- The host checks that every edit and write changed the file.
- An agent can cut a large result in its history if it keeps the first line.
  `shortened_tool_results` counts these.
- In new sessions, the first request of each session must hold no earlier turn.

**Side requests and compaction**

- Side requests, such as session titles, get a short fixed answer.
- The model knows each agent's compaction prompts (`summaries` in its file) and
  gives every agent the same summary. So the long session measures how the agent
  compacts, not the quality of the summary.
- The model checks the tool output in a compaction request before it can replace
  the original.
- An agent can compact before it sends a result. `compacted_tool_results` counts
  these.
- A side request with results from several turns but no known compaction prompt
  fails the run.

**Records** per case: each side request in short (path, model, tools, start of
its prompts), the rejected requests under `auxiliary_requests`, and a count of
all requests by path.

## Agent quirks

These live in each agent's recipe in `agents/`.

- **omp** edits with hashline patches.
  - The file tag comes from the newest read or edit result. The line numbers
    come from the file on the host.
  - omp refuses a body that starts with the line above the range. The range then
    covers that line too, and the body keeps it.
  - When omp refuses an edit and asks for a retry, the model sends it once more
    (`retried_edits`).
- **fx**
  - It writes its history to the terminal scrollback, not to an alternate
    screen.
  - Its compaction asks for notes under each turn heading, and asks again if one
    is missing. So the summary repeats the headings.
- **Claude Code** keeps its session-title requests, because users make them too.
