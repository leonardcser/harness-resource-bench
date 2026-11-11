import { no, some, tools, yes, type Profile } from "./features";

export default {
  tagline: "Minimal, extended in TypeScript.",
  text: "It has no subagents and does not ask before it acts. Extensions can change most of it.",
  logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="165 165 470 470"><path fill="#F09082" d="M165.29 165.29H517.36V400H400V282.65H165.29Z"/><path fill="#4D9ABF" d="M165.29 282.65H282.65V400H400V517.36H282.65V634.72H165.29Z"/><path fill="#F1BE58" d="M517.36 400H634.72V634.72H517.36Z"/></svg>`,
  repo: "https://github.com/earendil-works/pi",
  cells: {
    // At a glance
    language: yes("TypeScript, Node"),
    nativeBinary: no("Runs on Node.js 22.19 or newer."),
    license: yes("MIT"),
    windows: yes(),
    models: yes("30+ providers", "API keys and subscription logins."),
    localModels: yes(
      "Yes",
      "llama.cpp is built in. Ollama, LM Studio and others work through models.json.",
    ),
    tools: tools("bash", "edit", "read", "write"),
    sessionData: yes("JSONL"),

    // Sessions
    fullHistory: no("Shows what compaction kept."),
    transcriptSearch: some("Full screen", "Only in full-screen mode."),
    ephemeralSessions: yes("--no-session", "Does not save the session."),
    rewind: some("Chat only"),
    whileItWorks: yes("Both", "Enter steers. Alt+Enter queues."),
    sideQuestion: no(),

    // Workflow
    planMode: some(
      "Extension",
      "Left out on purpose. An example extension adds it.",
    ),
    goals: no(),
    worktrees: no(),
    diffViewer: no(),
    fileViewer: no(),
    codeReview: some(
      "Template",
      "The docs show how to write one as a prompt template.",
    ),
    memory: no(),

    // Agent
    subagents: no("Left out on purpose. Extensions can add them."),
    webSearch: no("Extensions can add it."),
    webFetch: no("Extensions can add it."),
    languageServers: no(),
    backgroundShells: no(),

    // Safety
    asksFirst: no("Its docs suggest a container."),
    osSandbox: no(),

    // Extending
    plugins: yes("TypeScript", "Extensions, shared as npm or git packages."),
    hotReload: yes(
      "/reload",
      "Reloads keybindings, extensions, skills, prompts, themes and context files.",
    ),
    pluginUi: yes(),
    hooks: yes("Extensions"),
    sdk: yes("TS, RPC"),

    // Interface
    editors: no(),
    desktopOrWeb: no(),
    vimMode: some(
      "Extension",
      "An example extension adds a basic modal editor to the prompt.",
    ),
    screen: yes(
      "Both",
      "Full screen by default. The regular mode keeps the scrollback.",
    ),
    notifications: some("Extension", "An example extension sends them."),
    voiceInput: no(),
    nextPrompt: no(),
    customThemes: yes(),
    latexMath: some(
      "Text",
      "As Unicode text. Math that is too wide shows as source.",
    ),
    diagrams: yes("Text", "Mermaid diagrams, drawn with text."),
  },
} satisfies Profile;
