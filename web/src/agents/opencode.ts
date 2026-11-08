import { no, some, tools, yes, type Profile } from "./features";

export default {
  tagline: "A server with many clients.",
  text: "The terminal, desktop app, web app and editors all connect to it. It supports the most model providers.",
  logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="96 96 320 320"><path class="fill-fg" fill-rule="evenodd" d="M384 416H128V96H384V416ZM320 160H192V352H320V160Z"/><path class="fill-muted" d="M320 224V352H192V224H320Z"/></svg>`,
  cells: {
    // At a glance
    language: yes("TypeScript, Bun"),
    nativeBinary: no("It is a Bun executable with the runtime inside."),
    license: yes("MIT"),
    windows: yes("Yes", "WSL recommended."),
    models: yes("75+ providers", "Through the AI SDK and Models.dev."),
    localModels: yes(),
    tools: tools(
      "edit",
      "execute",
      "experimental_image_generate",
      "glob",
      "grep",
      "question",
      "read",
      "shell",
      "skill",
      "subagent",
      "webfetch",
      "websearch",
      "write",
    ),
    sessionData: yes("SQLite"),

    // Sessions
    fullHistory: yes(),
    transcriptSearch: some(
      "Prompts only",
      "It searches your prompts, not the answers.",
    ),
    ephemeralSessions: no(),
    rewind: yes("Chat and files", "It keeps a git snapshot of your files."),
    whileItWorks: yes("Both", "Enter steers. Leader and Enter queues."),
    sideQuestion: yes("/btw"),

    // Workflow
    planMode: yes("Yes", "The plan agent. Tab switches agents."),
    goals: yes("/goal"),
    worktrees: yes(),
    diffViewer: yes("Yes", "With a file tree."),
    fileViewer: some(
      "Desktop and web",
      "The desktop and web apps have a file tree and open files. The terminal UI shows a file tree only beside diffs.",
    ),
    codeReview: yes("/review"),
    memory: no(),

    // Agent
    subagents: yes(),
    webSearch: some(
      "Needs a provider",
      "Exa, Tavily, Firecrawl, Parallel or TinyFish, with an API key.",
    ),
    webFetch: yes(),
    languageServers: yes(),
    backgroundShells: yes(),

    // Safety
    asksFirst: some("Opt-in", "By default it allows most actions."),
    osSandbox: no(),

    // Extending
    plugins: yes("JavaScript", "JavaScript or TypeScript modules."),
    hotReload: yes(
      "Automatic",
      "Local plugins reload when their files change. /reload reloads the configuration.",
    ),
    pluginUi: yes(),
    hooks: yes("Plugins"),
    sdk: yes("JS, HTTP"),

    // Interface
    editors: yes("ACP, VS Code"),
    desktopOrWeb: yes("Both"),
    vimMode: no(
      "Not built in. A community plugin, opencode-vim, adds Vim keys to the prompt.",
    ),
    screen: yes("Both", "Full screen. opencode mini keeps the scrollback."),
    notifications: some("Opt-in", "Off by default."),
    voiceInput: some("Desktop app"),
    nextPrompt: no(),
    customThemes: yes(),
    latexMath: some(
      "Code blocks",
      "Only latex and math code blocks, as Unicode text.",
    ),
    diagrams: yes("Text", "Mermaid diagrams, drawn with text."),
  },
} satisfies Profile;
