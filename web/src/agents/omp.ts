import { no, some, tools, yes, type Profile } from "./features";

export default {
  tagline: "A pi fork with everything built in.",
  text: "It adds subagents, language servers, a debugger, memory and hashline edits to pi.",
  logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 13 44 44"><defs><linearGradient id="gradient" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f84fcc"/><stop offset=".5" stop-color="#9362f4"/><stop offset="1" stop-color="#00dbe4"/></linearGradient></defs><path fill="url(#gradient)" d="M10 14h44v9H43v33h-9V23h-9v22h-9V23H10z"/></svg>`,
  cells: {
    // At a glance
    language: yes(
      "TypeScript, Rust",
      "TypeScript on Bun, with about 680,000 lines of Rust.",
    ),
    nativeBinary: no(
      "It is a Bun executable with the runtime inside, plus a Rust core.",
    ),
    license: yes("MIT"),
    windows: yes(),
    models: yes(
      "60+ providers",
      "API keys, subscription logins and any compatible API.",
    ),
    localModels: yes(
      "Yes",
      "Finds Ollama, llama.cpp and LM Studio on its own.",
    ),
    tools: tools(
      "ask",
      "bash",
      "edit",
      "eval",
      "glob",
      "grep",
      "read",
      "task",
      "todo",
      "wait",
      "web_search",
      "write",
    ),
    sessionData: yes("JSONL"),

    // Sessions
    fullHistory: yes("Yes", "Compactions show as a divider in the transcript."),
    transcriptSearch: some(
      "In rewind",
      "Press f in the rewind view to filter the transcript.",
    ),
    ephemeralSessions: yes("--no-session", "Does not save the session."),
    rewind: some("Chat only"),
    whileItWorks: yes("Both", "Enter steers. Ctrl+Enter queues."),
    sideQuestion: yes("/btw"),

    // Workflow
    planMode: yes("/plan"),
    goals: yes("/goal, /loop"),
    worktrees: yes(
      "Yes",
      "/wt. Subagents can also work in their own worktrees.",
    ),
    diffViewer: yes("/git", "A split diff viewer with staging and commits."),
    fileViewer: no(),
    codeReview: yes("/review", "Reviewer subagents rank issues from P0 to P3."),
    memory: some("Opt-in", "Off by default. memory.backend turns it on."),

    // Agent
    subagents: yes(),
    webSearch: yes(
      "Yes",
      "Works without an API key through public search engines.",
    ),
    webFetch: yes("Yes", "Through read, which also opens URLs."),
    languageServers: yes(),
    backgroundShells: yes(),

    // Safety
    asksFirst: some(
      "Opt-in",
      "Off by default. tools.approvalMode turns it on.",
    ),
    osSandbox: no(),

    // Extending
    plugins: yes("TypeScript", "Extensions and a plugin marketplace."),
    hotReload: yes(
      "/reload-plugins",
      "Reloads skills, commands, hooks, tools, agents and MCP servers.",
    ),
    pluginUi: yes(),
    hooks: yes("Extensions"),
    sdk: yes("TS, RPC"),

    // Interface
    editors: yes("ACP", "For example in Zed."),
    desktopOrWeb: some(
      "Web viewer",
      "/collab shares a live session that others can open in a browser.",
    ),
    vimMode: yes("Prompt", "Off by default."),
    screen: some("Inline"),
    notifications: yes(),
    voiceInput: some("Opt-in", "Off by default. stt.enabled turns it on."),
    nextPrompt: some("Opt-in", "Off by default."),
    customThemes: yes(),
    latexMath: some(
      "Text",
      "As Unicode text, with a 2D layout for display math.",
    ),
    diagrams: yes("Text", "Mermaid diagrams, drawn with text."),
  },
} satisfies Profile;
