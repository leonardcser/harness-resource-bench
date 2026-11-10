// What a person found, with ANALYSIS.md, at the versions in the benchmark:
// the cause behind each chart and the numbers that the bench cannot measure.

import type { Piece } from "./lib/splits";

export type Source = { label: string; href?: string };

/** One agent's cause in a topic. `tag` names its class, from the topic's
 * `tags`. */
export type Cause = { tag: string; text: string; source?: Source };

export type Topic = {
  /** The classes, in order from cheapest to most costly. */
  tags: string[];
  causes: Record<string, Cause>;
  /** A sentence that applies to several agents. */
  note?: string;
};

const FX = "https://github.com/vercel-labs/fx/blob/v0.0.16";
const OPENCODE = "https://github.com/sst/opencode/blob/v2.2.6";
const OMP = "https://github.com/can1357/oh-my-pi/blob/v18.18.0";
const CODEX = "https://github.com/openai/codex/blob/rust-v0.167.0";
const PI = "https://github.com/earendil-works/pi/blob/v1.5.0";
const SMELT = "https://github.com/leonardcser/smelt/blob/v0.8.0";

const src = (repo: string, path: string, lines: string): Source => ({
  label: `${path.split("/").pop()}:${lines}`,
  href: `${repo}/${path}#L${lines.replace("-", "-L")}`,
});
const trace = (label: string): Source => ({ label });

export const STARTUP: Topic = {
  tags: ["Native", "Loads JavaScript", "Two processes"],
  note: "The JavaScript runtimes boot in 3 to 16 ms. The rest is loading and running each agent's code.",
  causes: {
    fx: {
      tag: "Native",
      text: "A small static binary. It draws the prompt at once.",
    },
    smelt: {
      tag: "Native",
      text: "A static binary. Half of the time is the kernel that maps the binary into memory.",
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
  tags: [
    "One binary",
    "Several binaries",
    "JavaScript twice",
    "Node.js install",
  ],
  causes: {
    fx: { tag: "One binary", text: "One static Zig binary." },
    smelt: {
      tag: "One binary",
      text: "One static Rust binary and its Lua files.",
    },
    codex: {
      tag: "Several binaries",
      text: "A main binary of about 1,200 Rust crates with 3 TLS libraries, and 3 helper binaries that repeat much of its code.",
    },
    "claude-code": {
      tag: "JavaScript twice",
      text: "Bun keeps the JavaScript source and also its precompiled bytecode.",
    },
    omp: {
      tag: "JavaScript twice",
      text: "Source and bytecode, and its native module twice: for new and for old CPUs.",
    },
    opencode: {
      tag: "JavaScript twice",
      text: "Source and bytecode, and a web UI and a model catalog that the TUI does not use.",
    },
    pi: {
      tag: "Node.js install",
      text: "It needs Node.js, which comes with its C headers and npm.",
    },
  },
};

export const IDLE: Topic = {
  tags: ["Waits", "Slow timers", "Polls files", "Watchdog", "Busy loop"],
  causes: {
    smelt: {
      tag: "Waits",
      text: "It sleeps until a key or a model event comes.",
    },
    pi: {
      tag: "Waits",
      text: "No timers. The first 30 s run one-time checks for updates.",
    },
    codex: {
      tag: "Slow timers",
      text: "It checks the terminal size every 500 ms and writes its log every 10 s.",
      source: src(CODEX, "codex-rs/tui/src/tui/size_monitor.rs", "19"),
    },
    "claude-code": {
      tag: "Polls files",
      text: "It checks ~/.claude.json and the git HEAD for changes every second, and the keybindings every 2 s.",
      source: trace("strace: statx every 1 s"),
    },
    opencode: {
      tag: "Polls files",
      text: "It checks 2 plugin folders that do not exist every 500 ms, and sends a heartbeat every 15 s.",
      source: src(OPENCODE, "packages/tui/src/plugin/watch.ts", "100"),
    },
    omp: {
      tag: "Watchdog",
      text: "A watchdog checks every 250 ms that the event loop is not blocked.",
      source: src(OMP, "packages/tui/src/loop-watchdog.ts", "78"),
    },
    fx: {
      tag: "Busy loop",
      text: "Its main loop waits for input for at most 8 ms, then runs again, about 120 times a second.",
      source: src(FX, "src/main.zig", "174"),
    },
  },
  note: "In the Bun agents, 70 to 83% of this CPU time is the memory allocator, which cleans up after each wake-up. A larger heap makes each clean-up cost more.",
};

export const MEMORY: Topic = {
  tags: ["Small", "Own code", "JavaScript heap", "Two heaps"],
  causes: {
    fx: { tag: "Small", text: "Its code and data fit in 16 MiB." },
    smelt: { tag: "Small", text: "Most of its memory is its own code." },
    codex: {
      tag: "Own code",
      text: "About 80% of its memory is its own machine code. Its heap is small.",
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
      text: "The TUI and the server are two processes, each with its own JavaScript engine and heap.",
    },
  },
};

export const RENDER: Topic = {
  tags: ["Lays out all", "Renders all", "Animates", "Reprints"],
  causes: {
    fx: {
      tag: "Renders all",
      text: "It writes little to the terminal, because finished text goes to the scrollback once. But each update renders the whole transcript again, and its loop wakes about 120 times a second.",
      source: src(
        FX,
        "src/ui/render_engine/transcript_blocks.zig",
        "2497-2513",
      ),
    },
    "claude-code": {
      tag: "Lays out all",
      text: "Each frame lays out the whole message tree, and each new token parses the whole message as Markdown again.",
      source: trace("perf: Yoga layout and Markdown"),
    },
    smelt: {
      tag: "Animates",
      text: "While it works, an animation draws about 23 frames a second. Each frame runs the full render, but 86% of frames change 40 characters or fewer.",
      source: src(SMELT, "runtime/lua/smelt/prompt_chrome.lua", "175"),
    },
    pi: {
      tag: "Reprints",
      text: "When a change is above the visible screen, it prints the whole transcript again.",
      source: src(PI, "packages/tui/src/tui-main-screen.ts", "456-458"),
    },
    omp: {
      tag: "Reprints",
      text: "It draws up to 30 frames a second and sometimes replays the whole screen.",
    },
  },
};

export const GROWTH: Topic = {
  tags: ["Flat", "Rebuilds per message", "Walks all per update"],
  causes: {
    smelt: {
      tag: "Flat",
      text: "CPU time per turn stays the same after turn 16.",
    },
    pi: {
      tag: "Flat",
      text: "CPU time per turn stays the same after turn 16.",
    },
    omp: {
      tag: "Flat",
      text: "CPU time per turn stays the same after turn 16.",
    },
    codex: {
      tag: "Flat",
      text: "CPU time per turn stays the same after turn 16.",
    },
    "claude-code": {
      tag: "Flat",
      text: "Flat after turn 16. Each frame lays out the whole message tree, so each turn costs more than in the other flat agents.",
    },
    opencode: {
      tag: "Rebuilds per message",
      text: "For each new message, the TUI builds all rows of the session again. The server reads the whole history from its database for each step.",
      source: src(
        OPENCODE,
        "packages/tui/src/routes/session/rows.ts",
        "164-187",
      ),
    },
    fx: {
      tag: "Walks all per update",
      text: "Each change renders every block of the transcript again. When its scrollback cap is full, each new line removes an old one and starts another full render.",
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
  tags: ["File per session", "Folder per session", "One database"],
  note: "Each agent stores the same text. The sizes differ by how many copies of it they keep, and by what else they cache next to it.",
  causes: {
    pi: {
      tag: "File per session",
      text: "One JSONL file per session, in a folder per project. It keeps each tool result once, plus a small diff for each edit.",
    },
    omp: {
      tag: "File per session",
      text: "One JSONL file per session, like pi. Each tool result also keeps a display copy, a trace copy, and the old and new text of each edit. 4 SQLite databases sit next to it, and the model catalog is the largest (12 MiB with its WAL).",
    },
    "claude-code": {
      tag: "File per session",
      text: "One JSONL file per session, in a folder per project. Each tool result goes in 3 times: the message, a toolUseResult copy (with the whole file before each edit) and an API request record. A file-history folder keeps each version of each edited file.",
    },
    codex: {
      tag: "File per session",
      text: "One JSONL rollout per session, in date folders, plus 6 SQLite databases. The rollout writes each item twice, and the thread_history database keeps another copy of the rollout. A log database keeps debug logs, with full diffs.",
    },
    fx: {
      tag: "Folder per session",
      text: "One folder per session: a JSONL log, plus one blob file per tool output, named by its hash. The log and the blobs both hold the output, and the number of files grows with each call (4,362 in 64 turns).",
    },
    opencode: {
      tag: "One database",
      text: "One SQLite database for all sessions. The messages take only 8 MiB. The same database caches the models.dev catalog (11 MiB), and its WAL holds another 11 MiB from that write.",
    },
    smelt: {
      tag: "One database",
      text: "One SQLite database for all sessions. It keeps the display transcript and the model history in separate tables, plus blobs, a record of each request and a full-text search index.",
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
  codex: [
    { ms: 500, label: "terminal size check" },
    { ms: 10000, label: "log write" },
  ],
  "claude-code": [
    { ms: 1000, label: "~/.claude.json check" },
    { ms: 1000, label: "git HEAD check" },
    { ms: 2000, label: "keybindings check" },
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
      value: 320.6 * MB,
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
      value: 58.2 * MB,
      items: ["JavaScript, 54.5 MB", "assets, 3.7 MB"],
    },
    { part: "runtime", value: 149.4 * MB, items: ["Bun"] },
    { part: "bytecode", value: 108.3 * MB, items: ["JavaScriptCore bytecode"] },
    { part: "other" },
  ],
  omp: [
    {
      part: "code",
      value: 74.5 * MB,
      items: [
        "native module for new CPUs, 40.8 MB",
        "JavaScript, 29.7 MB",
        "scripts and docs, 4 MB",
      ],
    },
    { part: "runtime", value: 109.1 * MB, items: ["Bun"] },
    { part: "bytecode", value: 47.1 * MB, items: ["JavaScriptCore bytecode"] },
    {
      part: "extra",
      value: 40.7 * MB,
      items: ["native module for old CPUs, 40.7 MB"],
    },
    { part: "other" },
  ],
  opencode: [
    {
      part: "code",
      value: 50 * MB,
      items: [
        "JavaScript, 16.5 MB",
        "file search library, 12.9 MB",
        "TUI library, 8.5 MB",
        "tree-sitter and other wasm, 6.9 MB",
        "terminal helper, 3.5 MB",
      ],
    },
    { part: "runtime", value: 109.1 * MB, items: ["Bun"] },
    { part: "bytecode", value: 49.4 * MB, items: ["JavaScriptCore bytecode"] },
    {
      part: "extra",
      value: 42.3 * MB,
      items: ["web UI archive, 25.9 MB", "models.dev catalog, 16.4 MB"],
    },
    { part: "other" },
  ],
  pi: [
    { part: "code", value: 163.3 * MB, items: ["pi and its npm packages"] },
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
