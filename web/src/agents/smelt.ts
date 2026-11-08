import { no, some, tools, yes, type Profile } from "./features";

export default {
  tagline: "Native, extended in Lua.",
  text: "Lua plugins reload without a restart. Vim keys work in the prompt and the transcript. It has no subagents, sandbox or SDK.",
  logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="2 2 12 12"><path class="fill-fg" d="M3 2h1v1h-1zM4 2h1v1h-1zM5 2h1v1h-1zM6 2h1v1h-1zM7 2h1v1h-1zM8 2h1v1h-1zM9 2h1v1h-1zM10 2h1v1h-1zM11 2h1v1h-1zM12 2h1v1h-1zM3 3h1v1h-1zM4 3h1v1h-1zM5 3h1v1h-1zM6 3h1v1h-1zM7 3h1v1h-1zM8 3h1v1h-1zM9 3h1v1h-1zM10 3h1v1h-1zM11 3h1v1h-1zM12 3h1v1h-1zM3 4h1v1h-1zM4 4h1v1h-1zM11 4h1v1h-1zM12 4h1v1h-1zM3 5h1v1h-1zM4 5h1v1h-1zM11 5h1v1h-1zM12 5h1v1h-1zM3 6h1v1h-1zM4 6h1v1h-1zM11 6h1v1h-1zM12 6h1v1h-1zM3 7h1v1h-1zM4 7h1v1h-1zM11 7h1v1h-1zM12 7h1v1h-1zM3 8h1v1h-1zM4 8h1v1h-1zM5 8h1v1h-1zM6 8h1v1h-1zM7 8h1v1h-1zM8 8h1v1h-1zM11 8h1v1h-1zM12 8h1v1h-1zM3 9h1v1h-1zM4 9h1v1h-1zM5 9h1v1h-1zM6 9h1v1h-1zM7 9h1v1h-1zM8 9h1v1h-1zM11 9h1v1h-1zM12 9h1v1h-1zM3 10h1v1h-1zM4 10h1v1h-1zM11 10h1v1h-1zM12 10h1v1h-1zM3 11h1v1h-1zM4 11h1v1h-1zM11 11h1v1h-1zM12 11h1v1h-1zM3 12h1v1h-1zM4 12h1v1h-1zM5 12h1v1h-1zM6 12h1v1h-1zM7 12h1v1h-1zM8 12h1v1h-1zM9 12h1v1h-1zM10 12h1v1h-1zM11 12h1v1h-1zM12 12h1v1h-1zM3 13h1v1h-1zM4 13h1v1h-1zM5 13h1v1h-1zM6 13h1v1h-1zM7 13h1v1h-1zM8 13h1v1h-1zM9 13h1v1h-1zM10 13h1v1h-1zM11 13h1v1h-1zM12 13h1v1h-1z"/><path class="fill-bg" d="M5 4h1v1h-1zM6 4h1v1h-1zM7 4h1v1h-1zM8 4h1v1h-1zM9 4h1v1h-1zM10 4h1v1h-1zM5 5h1v1h-1zM6 5h1v1h-1zM7 5h1v1h-1zM8 5h1v1h-1zM9 5h1v1h-1zM10 5h1v1h-1zM5 6h1v1h-1zM6 6h1v1h-1zM5 7h1v1h-1zM6 7h1v1h-1zM9 8h1v1h-1zM10 8h1v1h-1zM9 9h1v1h-1zM10 9h1v1h-1zM5 10h1v1h-1zM6 10h1v1h-1zM7 10h1v1h-1zM8 10h1v1h-1zM9 10h1v1h-1zM10 10h1v1h-1zM5 11h1v1h-1zM6 11h1v1h-1zM7 11h1v1h-1zM8 11h1v1h-1zM9 11h1v1h-1zM10 11h1v1h-1z"/><path class="fill-muted" d="M7 6h1v1h-1zM8 6h1v1h-1zM9 6h1v1h-1zM10 6h1v1h-1zM7 7h1v1h-1zM8 7h1v1h-1zM9 7h1v1h-1zM10 7h1v1h-1z"/></svg>`,
  cells: {
    // At a glance
    language: yes("Rust"),
    nativeBinary: yes(),
    license: yes("MIT"),
    windows: yes(),
    models: yes(
      "Many",
      "OpenAI, Anthropic, ChatGPT, Copilot, Kimi, Claude Code and any compatible API.",
    ),
    localModels: yes("Yes", "Ollama, vLLM, SGLang, llama.cpp and others."),
    tools: tools(
      "ask_user_question",
      "bash",
      "edit_file",
      "enter_worktree",
      "glob",
      "grep",
      "load_skill",
      "read_file",
      "read_process_output",
      "show_image",
      "smelt_reload",
      "stop_process",
      "switch_cwd",
      "web_fetch",
      "web_search",
      "write_file",
    ),
    sessionData: yes("SQLite"),

    // Sessions
    fullHistory: yes(),
    transcriptSearch: yes("Yes", "Search with / and ?, as in Vim."),
    ephemeralSessions: yes(
      "--ephemeral",
      "Does not save the session or list it for resume.",
    ),
    rewind: some("Chat only"),
    whileItWorks: yes("Both", "Enter queues. Ctrl+Enter steers."),
    sideQuestion: yes("/btw"),

    // Workflow
    planMode: yes("Yes", "Shift+Tab. Plans are saved as files."),
    goals: some(
      "Opt-in",
      "A bundled plugin that is off by default. After a usage limit, it resumes on its own.",
    ),
    worktrees: yes(
      "Yes",
      "/worktree or --worktree. The agent can also create one.",
    ),
    diffViewer: yes("/diff"),
    fileViewer: yes(
      "/files",
      "Finds files by name, with a source preview beside the results. /search finds text in files.",
    ),
    codeReview: some("/simplify", "It reviews quality and reuse, not bugs."),
    memory: no(),

    // Agent
    subagents: no("Left out on purpose."),
    webSearch: yes("Yes", "DuckDuckGo, or Brave if you set an API key."),
    webFetch: yes(),
    languageServers: some("Opt-in", "A bundled plugin. It is off by default."),
    backgroundShells: yes(),

    // Safety
    asksFirst: yes(),
    osSandbox: no(),

    // Extending
    plugins: yes("Lua", "Plugins reload without a restart."),
    hotReload: yes(
      "Automatic",
      "Lua config and plugins reload when their files change, or with /reload.",
    ),
    pluginUi: yes(),
    hooks: yes("Lua"),
    sdk: no(),

    // Interface
    editors: no(),
    desktopOrWeb: no(),
    vimMode: yes("Everywhere", "In the prompt and the transcript."),
    screen: some("Full screen"),
    notifications: some("Opt-in", "Off by default."),
    voiceInput: no(),
    nextPrompt: yes(),
    customThemes: yes(),
    latexMath: yes(
      "Images",
      "As images in terminals with Kitty graphics, and as Unicode text in others.",
    ),
    diagrams: yes("Text", "Mermaid diagrams, drawn with text."),
  },
} satisfies Profile;
