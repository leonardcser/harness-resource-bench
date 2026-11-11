import { no, some, tools, yes, type Profile } from "./features";

export default {
  tagline: "Safest by default.",
  text: "It runs commands in a sandbox by default. It also has a desktop app and cloud tasks.",
  logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M8.086.457a6.105 6.105 0 013.046-.415c1.333.153 2.521.72 3.564 1.7a.117.117 0 00.107.029c1.408-.346 2.762-.224 4.061.366l.063.03.154.076c1.357.703 2.33 1.77 2.918 3.198.278.679.418 1.388.421 2.126a5.655 5.655 0 01-.18 1.631.167.167 0 00.04.155 5.982 5.982 0 011.578 2.891c.385 1.901-.01 3.615-1.183 5.14l-.182.22a6.063 6.063 0 01-2.934 1.851.162.162 0 00-.108.102c-.255.736-.511 1.364-.987 1.992-1.199 1.582-2.962 2.462-4.948 2.451-1.583-.008-2.986-.587-4.210-1.736a.145.145 0 00-.14-.032c-.518.167-1.04.191-1.604.185a5.924 5.924 0 01-2.595-.622 6.058 6.058 0 01-2.146-1.781c-.203-.269-.404-.522-.551-.821a7.74 7.74 0 01-.495-1.283 6.11 6.11 0 01-.017-3.064.166.166 0 00.008-.074.115.115 0 00-.037-.064 5.958 5.958 0 01-1.38-2.202 5.196 5.196 0 01-.333-1.589 6.915 6.915 0 01.188-2.132c.45-1.484 1.309-2.648 2.577-3.493.282-.188.55-.334.802-.438.286-.12.573-.22.861-.304a.129.129 0 00.087-.087A6.016 6.016 0 015.635 2.31C6.315 1.464 7.132.846 8.086.457zm-.804 7.85a.848.848 0 00-1.473.842l1.694 2.965-1.688 2.848a.849.849 0 001.46.864l1.94-3.272a.849.849 0 00.007-.854l-1.94-3.393zm5.446 6.24a.849.849 0 000 1.695h4.848a.849.849 0 000-1.696h-4.848z"/></svg>`,
  repo: "https://github.com/openai/codex",
  tagPrefix: "rust-v",
  cells: {
    // At a glance
    language: yes("Rust"),
    nativeBinary: yes(),
    license: yes("Apache-2.0"),
    windows: yes(),
    models: yes(
      "OpenAI",
      "Also Amazon Bedrock and any server with the Responses API. It no longer supports Chat Completions.",
    ),
    localModels: yes("Ollama, LM Studio"),
    tools: tools(
      "close_agent",
      "create_goal",
      "create_thread",
      "create_worktree",
      "exec_command",
      "fork_thread",
      "get_goal",
      "get_worktree_creation_status",
      "list_archived_threads",
      "list_mcp_resource_templates",
      "list_mcp_resources",
      "list_threads",
      "list_worktrees",
      "read_mcp_resource",
      "read_thread",
      "request_user_input",
      "resume_agent",
      "send_input",
      "send_message_to_thread",
      "set_thread_archived",
      "set_thread_title",
      "spawn_agent",
      "update_goal",
      "view_image",
      "wait_agent",
      "wait_threads",
      "web_search",
      "write_stdin",
    ),
    sessionData: yes("JSONL, SQLite"),

    // Sessions
    fullHistory: yes(),
    transcriptSearch: yes(),
    ephemeralSessions: some(
      "Headless",
      "codex exec --ephemeral. The terminal UI always saves the session.",
    ),
    rewind: some("Chat only"),
    whileItWorks: yes("Both", "Enter steers. Tab queues."),
    sideQuestion: yes("/side", "Also /btw. It opens a temporary fork."),

    // Workflow
    planMode: yes("Yes", "/plan."),
    goals: yes("/goal", "A goal stops at a usage limit until you resume it."),
    worktrees: yes("Yes", "/worktree or --worktree."),
    diffViewer: yes("/diff"),
    fileViewer: some(
      "Desktop app",
      "The desktop app opens project files in its side panel. The terminal UI has none.",
    ),
    codeReview: yes("/review"),
    memory: some("Opt-in", "Off by default. /memories turns it on."),

    // Agent
    subagents: yes(),
    webSearch: yes(),
    webFetch: no(),
    languageServers: no(),
    backgroundShells: yes("Yes", "/ps lists them and /stop stops them."),

    // Safety
    asksFirst: yes(),
    osSandbox: yes(
      "Default",
      "Read-only until you trust the project, then workspace-write.",
    ),

    // Extending
    plugins: yes(
      "Bundles",
      "Skills, hooks, MCP servers and commands. Shared in marketplaces.",
    ),
    hotReload: some("Skills", "Changed skill files load without a restart."),
    pluginUi: no(),
    hooks: yes("14 events"),
    sdk: yes("TS, Python"),

    // Interface
    editors: yes("VS Code", "Also forks such as Cursor and Windsurf."),
    desktopOrWeb: yes("Both"),
    vimMode: yes("Prompt"),
    screen: yes(
      "Both",
      "Full screen by default. --no-alt-screen keeps the scrollback.",
    ),
    notifications: yes("Yes", "When the terminal is not in focus."),
    voiceInput: yes("/voice"),
    nextPrompt: no(
      "Answers can name follow-ups, but the terminal shows them as plain text that you cannot pick.",
    ),
    customThemes: some("Syntax only", "Custom .tmTheme files."),
    latexMath: some("Text", "A subset of TeX, as Unicode text."),
    diagrams: yes("Text", "Mermaid diagrams, drawn with text."),
  },
} satisfies Profile;
