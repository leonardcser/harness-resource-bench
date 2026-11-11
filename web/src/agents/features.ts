// Every row of the agent tables, in order. Each agent file has one cell per
// row.

export type Level = "yes" | "some" | "no";
/** `text` fits on one line. `detail` tells more on hover. */
export type Cell = { level: Level; text: string; detail?: string };

export const yes = (text = "Yes", detail?: string): Cell => ({
  level: "yes",
  text,
  detail,
});
export const some = (text: string, detail?: string): Cell => ({
  level: "some",
  text,
  detail,
});
export const no = (detail?: string): Cell => ({
  level: "no",
  text: "No",
  detail,
});
/** The number of tools, with their names on hover. */
export const tools = (...names: string[]): Cell =>
  yes(String(names.length), [...names].sort().join(", ") + ".");

/** The "At a glance" rows make the first table. The other groups make the
 * feature table. */
export const FEATURES = {
  language: { group: "At a glance", label: "Language" },
  nativeBinary: {
    group: "At a glance",
    label: "Native binary",
    hint: "Compiled to machine code. No JavaScript runtime.",
  },
  license: { group: "At a glance", label: "License" },
  windows: {
    group: "At a glance",
    label: "Windows",
    hint: "All seven run on macOS and Linux.",
  },
  models: { group: "At a glance", label: "Models" },
  localModels: {
    group: "At a glance",
    label: "Local models",
    hint: "Models that run on your own machine, such as with Ollama.",
  },
  tools: {
    group: "At a glance",
    label: "Tools",
    hint: "The tools that the model can call by default, without MCP servers, read from the first request of each agent in the benchmark. Hover a number for the names.",
  },
  sessionData: {
    group: "At a glance",
    label: "Session data",
    hint: "How the agent keeps sessions on disk.",
  },
  fullHistory: {
    group: "Sessions",
    label: "Full history",
    hint: "After compaction, the view still scrolls back to the first turn.",
  },
  transcriptSearch: { group: "Sessions", label: "Transcript search" },
  ephemeralSessions: {
    group: "Sessions",
    label: "Ephemeral sessions",
    hint: "Run without saving the session to disk.",
  },
  rewind: {
    group: "Sessions",
    label: "Rewind",
    hint: "Go back to an earlier turn.",
  },
  whileItWorks: {
    group: "Sessions",
    label: "While it works",
    hint: "Send a message while the agent works. Steering adds it to the current turn. Queueing keeps it for the next turn.",
  },
  sideQuestion: {
    group: "Sessions",
    label: "Side question",
    hint: "Ask a quick question without changing the main chat.",
  },
  planMode: {
    group: "Workflow",
    label: "Plan mode",
    hint: "A read-only mode where the agent plans before it changes anything.",
  },
  goals: {
    group: "Workflow",
    label: "Goals",
    hint: "The agent keeps working across turns until a task is done.",
  },
  worktrees: {
    group: "Workflow",
    label: "Worktrees",
    hint: "Run a task in its own git worktree.",
  },
  diffViewer: {
    group: "Workflow",
    label: "Diff viewer",
    hint: "See the changes in the working tree without leaving the agent.",
  },
  fileViewer: {
    group: "Workflow",
    label: "File viewer",
    hint: "Find and read any file in the workspace without leaving the agent.",
  },
  codeReview: {
    group: "Workflow",
    label: "Code review",
    hint: "A built-in command that reviews your changes.",
  },
  memory: {
    group: "Workflow",
    label: "Memory",
    hint: "Notes that the agent writes itself and reads in later sessions.",
  },
  subagents: { group: "Agent", label: "Subagents" },
  webSearch: { group: "Agent", label: "Web search" },
  webFetch: { group: "Agent", label: "Web fetch" },
  languageServers: {
    group: "Agent",
    label: "Language servers",
    hint: "Diagnostics and code navigation for the model.",
  },
  backgroundShells: {
    group: "Agent",
    label: "Background shells",
    hint: "Commands such as a dev server keep running while the agent works.",
  },
  asksFirst: {
    group: "Safety",
    label: "Asks first",
    hint: "The agent asks before it runs a command or edits a file.",
  },
  osSandbox: {
    group: "Safety",
    label: "OS sandbox",
    hint: "Commands run with limited access to files and the network.",
  },
  plugins: { group: "Extending", label: "Plugins" },
  hotReload: {
    group: "Extending",
    label: "Hot reload",
    hint: "Apply changes to plugins and skills without a restart.",
  },
  pluginUi: {
    group: "Extending",
    label: "Plugin UI",
    hint: "Plugins can change the interface.",
  },
  hooks: {
    group: "Extending",
    label: "Hooks",
    hint: "Your code runs on events, for example before a tool call.",
  },
  sdk: {
    group: "Extending",
    label: "SDK",
    hint: "Run the agent from your own program.",
  },
  editors: { group: "Interface", label: "Editors" },
  desktopOrWeb: { group: "Interface", label: "Desktop or web" },
  vimMode: { group: "Interface", label: "Vim mode" },
  screen: {
    group: "Interface",
    label: "Screen",
    hint: "Full screen takes over the terminal. Inline keeps the output in your scrollback.",
  },
  notifications: {
    group: "Interface",
    label: "Notifications",
    hint: "Tell you when a turn ends or the agent needs input.",
  },
  voiceInput: { group: "Interface", label: "Voice input" },
  nextPrompt: {
    group: "Interface",
    label: "Next prompt",
    hint: "The agent suggests your next prompt as gray text in the input.",
  },
  customThemes: { group: "Interface", label: "Custom themes" },
  latexMath: {
    group: "Interface",
    label: "LaTeX math",
    hint: "Show math in answers as images or as Unicode text, not as LaTeX source.",
  },
  diagrams: {
    group: "Interface",
    label: "Diagrams",
    hint: "Draw Mermaid diagrams in the terminal.",
  },
} as const satisfies Record<
  string,
  { group: string; label: string; hint?: string }
>;
export type FeatureId = keyof typeof FEATURES;

/** What an agent file holds. */
export type Profile = {
  /** A few words, as the title of the agent's card. */
  tagline: string;
  /** A few plain sentences under the tagline. */
  text: string;
  /**
   * The agent's mark as SVG, square, in sRGB colors. The classes `fill-fg`,
   * `fill-muted` and `fill-bg`, and `currentColor`, follow the theme.
   */
  logo: string;
  /** The agent's GitHub repository. */
  repo: string;
  /** What comes before the version in a release tag. The default is "v". */
  tagPrefix?: string;
  cells: Record<FeatureId, Cell>;
};
