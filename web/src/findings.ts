// What a person found, with the recipes in RELEASE.md, at the versions in the benchmark:
// the cause behind each chart and the numbers that the bench cannot measure.

import { PROFILES, tagOf, type Agent } from "./agents";
import type { Piece } from "./lib/splits";

export type Source = { label: string; href?: string };

/** One agent's cause and a short label for its approach. */
export type Cause = { tag: string; text: string; source?: Source };

export type Topic = {
  causes: Record<Agent, Cause>;
  /** A sentence that applies to several agents. */
  note?: string;
};

/** An agent's source at the version that the analysis read. */
const at = (agent: Agent, version: string) =>
  `${PROFILES[agent].repo}/blob/${tagOf(agent, version)}`;
const FX = at("fx", "0.0.16");
const OPENCODE = at("opencode", "2.2.7");
const OMP = at("omp", "18.19.0");
const CODEX = at("codex", "0.167.2");
const PI = at("pi", "1.5.2");
const SMELT = at("smelt", "0.8.0");

const src = (repo: string, path: string, lines: string): Source => ({
  label: `${path.split("/").pop()}:${lines}`,
  href: `${repo}/${path}#L${lines.replace("-", "-L")}`,
});
const trace = (label: string): Source => ({ label });

export const STARTUP: Topic = {
  note: "The JavaScript runtimes boot in 3 to 16 ms. The rest is loading and running each agent's code.",
  causes: {
    fx: {
      tag: "Native",
      text: "A small binary that shows the prompt at once.",
    },
    smelt: {
      tag: "Native",
      text: "A native binary. About half of its startup is the kernel, as it reads each TLS certificate file and searches for Lua modules.",
      source: trace("strace: open and stat"),
    },
    codex: {
      tag: "Native",
      text: "A large binary. A worker thread sets up codex while the main thread waits for it. It clones a plugin repository in the background.",
      source: trace("bpftrace: futex wait of the main thread"),
    },
    "claude-code": {
      tag: "Loads JavaScript",
      text: "Bun starts in 7 ms at most. Then it runs 108 MB of precompiled JavaScript on the CPU until the first frame, and runs git 3 times.",
      source: trace("bpftrace: CPU, exec and connect"),
    },
    pi: {
      tag: "Loads JavaScript",
      text: "A shell script starts Node.js in 6 ms. Node.js starts in 16 ms, then loads 22 JavaScript files and runs them.",
      source: trace("bpftrace: exec and open"),
    },
    omp: {
      tag: "Loads JavaScript",
      text: "Bun starts in 3 ms. Then a long chain of JavaScript setup runs on one thread. In it, omp writes a 129 MB native module into the home folder, in about 50 ms. Each case has a new home folder, so it pays this every time. You pay it once per version.",
      source: trace("bpftrace: CPU and open"),
    },
    opencode: {
      tag: "Two processes",
      text: "Bun starts in 3 ms. The TUI loads, starts a server process and waits for it, for about a quarter of the startup. In a new home folder, the server also creates its database first.",
      source: trace("bpftrace: event loop waits of the TUI"),
    },
  },
};

export const INSTALL: Topic = {
  causes: {
    fx: { tag: "One binary", text: "One Zig binary." },
    smelt: {
      tag: "One binary",
      text: "One Rust binary and its Lua files.",
    },
    codex: {
      tag: "Several binaries",
      text: "A large main binary and 3 helpers that repeat much of its code.",
    },
    "claude-code": {
      tag: "JavaScript twice",
      text: "Keeps both JavaScript source and compiled bytecode.",
    },
    omp: {
      tag: "JavaScript twice",
      text: "Keeps source, bytecode and two native modules for different CPUs.",
    },
    opencode: {
      tag: "JavaScript twice",
      text: "Keeps source, bytecode, a web UI and a model catalog.",
    },
    pi: {
      tag: "Node.js install",
      text: "Includes Node.js, its development files and npm.",
    },
  },
};

export const IDLE: Topic = {
  causes: {
    smelt: {
      tag: "Waits",
      text: "Sleeps until input or a model event arrives.",
    },
    pi: {
      tag: "Waits",
      text: "No repeating timers. Update checks finish in the first 30 s.",
    },
    codex: {
      tag: "Slow timers",
      text: "Writes logs every 10 s. Its 500 ms terminal size check runs only inside tmux, which the agent cannot detect here.",
      source: src(CODEX, "codex-rs/state/src/log_db.rs", "58"),
    },
    "claude-code": {
      tag: "Polls files",
      text: "Checks ~/.claude.json every 1 s and the ~/.claude folder every 2 s.",
      source: trace("strace: statx every 1 s"),
    },
    opencode: {
      tag: "Polls files",
      text: "Checks plugin folders every 500 ms; sends a heartbeat every 15 s.",
      source: src(OPENCODE, "packages/tui/src/plugin/watch.ts", "100"),
    },
    omp: {
      tag: "Watchdog",
      text: "Checks for a blocked event loop every 250 ms.",
      source: src(OMP, "packages/tui/src/loop-watchdog.ts", "78"),
    },
    fx: {
      tag: "Busy loop",
      text: "Checks for input every 8 ms, about 120 times a second.",
      source: src(FX, "src/main.zig", "174"),
    },
  },
  note: "Bun agents spend most idle CPU time on memory cleanup after wake-ups.",
};

export const MEMORY: Topic = {
  causes: {
    fx: { tag: "Small", text: "Its code and data fit in 16 MiB." },
    smelt: { tag: "Small", text: "Most of its memory is its own code." },
    codex: {
      tag: "Own code",
      text: "About 80% is program code; little is data.",
    },
    pi: { tag: "JavaScript heap", text: "Node.js code and a small heap." },
    "claude-code": {
      tag: "JavaScript heap",
      text: "The JavaScript heap is two thirds of its memory.",
    },
    omp: {
      tag: "JavaScript heap",
      text: "The JavaScript heap, plus a 50 MiB native module.",
    },
    opencode: {
      tag: "Two heaps",
      text: "The TUI and server each keep their own JavaScript code and data.",
    },
  },
};

export const RENDER: Topic = {
  causes: {
    opencode: {
      tag: "Rebuilds rows",
      text: "Rebuilds the session's display rows when the message list changes.",
      source: src(
        OPENCODE,
        "packages/tui/src/routes/session/rows.ts",
        "164-187",
      ),
    },
    codex: {
      tag: "Animates",
      text: "The progress animation adds redraws between tokens.",
      source: src(
        CODEX,
        "codex-rs/tui/src/status_indicator_widget.rs",
        "308-318",
      ),
    },
    fx: {
      tag: "Renders all",
      text: "Renders the whole transcript on each update, but writes finished text only once.",
      source: src(
        FX,
        "src/ui/render_engine/transcript_blocks.zig",
        "2497-2513",
      ),
    },
    "claude-code": {
      tag: "Lays out all",
      text: "Lays out all messages each frame and parses Markdown again for each token.",
      source: trace("perf: Yoga layout and Markdown"),
    },
    smelt: {
      tag: "Animates",
      text: "Animations add redraws between tokens, without clearing the screen.",
      source: src(SMELT, "runtime/lua/smelt/prompt_chrome.lua", "175"),
    },
    pi: {
      tag: "Rewrites rows",
      text: "Rewrites each screen row that changes. When the transcript scrolls, that is the whole screen.",
      source: src(PI, "packages/tui/src/tui-alt-screen.ts", "1778-1781"),
    },
    omp: {
      tag: "Animates",
      text: "Animations add redraws between tokens. The task clears the screen only at startup.",
    },
  },
};

export const GROWTH: Topic = {
  causes: {
    smelt: {
      tag: "Flat",
      text: "CPU per turn stays level after turn 16.",
    },
    pi: {
      tag: "Flat",
      text: "CPU per turn stays level after turn 16.",
    },
    omp: {
      tag: "Flat",
      text: "CPU per turn stays level after turn 16.",
    },
    codex: {
      tag: "Flat",
      text: "CPU per turn stays level after turn 16.",
    },
    "claude-code": {
      tag: "Flat",
      text: "Nearly level after turn 16, but each frame still lays out all messages.",
    },
    opencode: {
      tag: "Rebuilds per message",
      text: "Rebuilds all display rows per message and reads all history per step.",
      source: src(
        OPENCODE,
        "packages/tui/src/routes/session/rows.ts",
        "164-187",
      ),
    },
    fx: {
      tag: "Walks all per update",
      text: "Renders the whole transcript on each change. A longer session means more work.",
      source: src(
        FX,
        "src/ui/render_engine/transcript_blocks.zig",
        "2497-2513",
      ),
    },
  },
};

/** How each agent stores sessions, and what takes the space. */
export const SESSION: Topic = {
  note: "Same session text; different copies, logs and caches.",
  causes: {
    pi: {
      tag: "File per session",
      text: "Saves each tool result once, plus small edit diffs.",
    },
    omp: {
      tag: "File per session",
      text: "Keeps extra copies of tool results and edits, plus a 12 MiB model catalog.",
    },
    "claude-code": {
      tag: "File per session",
      text: "Keeps tool results in 3 places, plus copies of edited files.",
    },
    codex: {
      tag: "File per session",
      text: "Saves each item twice in the session log, plus database copies and debug logs.",
    },
    fx: {
      tag: "Folder per session",
      text: "Saves tool output in both a log and separate files: about 4,370 files in 64 turns.",
    },
    opencode: {
      tag: "One database",
      text: "Stores 8 MiB of messages, plus a model catalog and its write log at 11 MiB each.",
    },
    smelt: {
      tag: "One database",
      text: "Keeps display and model history separately, plus request logs and a search index.",
    },
  },
};

/** fx: blocks that one update renders, in each eighth of a 32-turn session,
 * from its own trace (FX_TRACE=1). */
export const FX_WALK = [91, 227, 535, 628, 687, 735, 849, 968];

/** The timers that wake each agent when idle, from its source. */
export const TIMERS: Record<string, { ms: number; label: string }[]> = {
  smelt: [],
  pi: [],
  codex: [{ ms: 10000, label: "log write" }],
  "claude-code": [
    { ms: 1000, label: "~/.claude.json check" },
    { ms: 2000, label: "~/.claude folder check" },
  ],
  omp: [{ ms: 250, label: "event loop watchdog" }],
  opencode: [
    { ms: 500, label: "plugin folder check" },
    { ms: 15000, label: "server heartbeat" },
  ],
  fx: [{ ms: 8, label: "input poll" }],
};

const MB = 1e6;

/** What the installer puts on disk, in bytes. */
export const INSTALL_PIECES: Record<string, Piece[]> = {
  fx: [{ part: "code", items: ["fx, a static Zig binary"] }],
  smelt: [
    {
      part: "code",
      items: ["smelt, a static Rust binary", "Lua runtime files, 0.8 MB"],
    },
  ],
  codex: [
    {
      part: "code",
      value: 320.2 * MB,
      items: ["codex: 251 MB machine code, 36 MB unwind tables"],
    },
    {
      part: "extra",
      value: 207 * MB,
      items: [
        "codex-exec-server, 82 MB",
        "codex-code-mode-host, 79 MB",
        "codex-voice-host, 40 MB",
        "ripgrep, 5 MB",
      ],
    },
    { part: "other" },
  ],
  "claude-code": [
    {
      part: "code",
      value: 58.6 * MB,
      items: ["JavaScript, 54.9 MB", "assets, 3.7 MB"],
    },
    { part: "runtime", value: 149.4 * MB, items: ["Bun"] },
    { part: "bytecode", value: 109.4 * MB, items: ["JavaScriptCore bytecode"] },
    { part: "other" },
  ],
  omp: [
    {
      part: "code",
      value: 75.1 * MB,
      items: [
        "native module for new CPUs, 40.8 MB",
        "JavaScript, 30.2 MB",
        "scripts and docs, 4.1 MB",
      ],
    },
    { part: "runtime", value: 109.1 * MB, items: ["Bun"] },
    { part: "bytecode", value: 47.9 * MB, items: ["JavaScriptCore bytecode"] },
    {
      part: "extra",
      value: 40.9 * MB,
      items: ["native module for old CPUs, 40.9 MB"],
    },
    { part: "other" },
  ],
  opencode: [
    {
      part: "code",
      value: 49.9 * MB,
      items: [
        "JavaScript, 16.5 MB",
        "file search library, 12.9 MB",
        "TUI library, 8.5 MB",
        "tree-sitter and other wasm, 6.9 MB",
        "terminal helper, 3.5 MB",
      ],
    },
    { part: "runtime", value: 109.1 * MB, items: ["Bun"] },
    { part: "bytecode", value: 49.3 * MB, items: ["JavaScriptCore bytecode"] },
    {
      part: "extra",
      value: 42.5 * MB,
      items: ["web UI archive, 25.9 MB", "models.dev catalog, 16.6 MB"],
    },
    { part: "other" },
  ],
  pi: [
    { part: "code", value: 164.8 * MB, items: ["pi and its npm packages"] },
    {
      part: "runtime",
      value: 211.5 * MB,
      items: [
        "Node.js binary, 124.9 MB",
        "C headers, 67.7 MB",
        "npm and corepack, 18.9 MB",
      ],
    },
    { part: "extra", value: 27.3 * MB, items: ["npm download cache"] },
    { part: "other" },
  ],
};
