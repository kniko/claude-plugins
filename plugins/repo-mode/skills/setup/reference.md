# repo-mode reference

Facts below come from the Claude Code docs (code.claude.com/docs) and the Claude pricing page, checked 2026-11-08. If something here conflicts with what you observe in the user's Claude Code, trust the observation and tell the user.

## Model aliases

`sonnet`, `opus`, `haiku`, `fable` resolve to Claude Code's current default version of each family. On the Anthropic API today: `opus` = Opus 5.5, `sonnet` = Sonnet 5.5, `haiku` = Haiku 5.5, `fable` = Fable 5.1. On Bedrock / Vertex (Agent Platform) / Foundry / Claude Platform on AWS, `haiku` resolves to Haiku 4.5. A full model ID such as `claude-opus-5-5` is also accepted.

`opusplan` uses `opus` while in plan mode and `sonnet` for execution. `best` = Fable where available, otherwise Opus.

Fable needs Fable access, and on some plans a one-time consent to bill Fable usage to usage credits (the user accepts it by running `/model fable` once).

## Version floors

| Feature | Claude Code |
|---|---|
| `autoCompactWindow` agent field | v2.1.296+ |
| Haiku 5.5 (main or advisor) | v2.1.293+ |
| Sonnet 5.5 | v2.1.284+ |
| Opus 5.5 | v2.1.280+ |
| `omitClaudeMd` agent field | v2.1.271+ |
| Fable 5.1 | v2.1.257+ |

Unknown agent frontmatter fields are ignored silently, so an older Claude Code just skips them.

## Advisor pairing rules

The advisor must rank at or above the main model; otherwise Claude Code does not attach it. Haiku 4.5 can call an advisor but can never be one; Haiku 5.5 can be one, but only for a main model at or below it.

| Main model | Accepted advisors |
|---|---|
| Haiku 4.5 | fable, opus, sonnet, haiku 5.5 |
| Sonnet 5 or Haiku 5.5 | fable, opus (4.7 or later), sonnet (5 or later), haiku 5.5 |
| Sonnet 5.5 | fable, opus (5 or later), sonnet (5.5) |
| Opus 5 / 5.5 (and `opusplan`) | fable, opus (5 or later) — **not** sonnet |
| Fable 5 | fable 5.1 or fable 5 |
| Fable 5.1 | fable 5.1 only |

Common pairings in the docs: Sonnet main + Opus advisor; Haiku main + Opus advisor ("lowest-cost main model with strong planning").

Other advisor facts:
- Experimental. Anthropic API only: not available on Bedrock, Claude Platform on AWS, Google Cloud's Agent Platform, or Microsoft Foundry.
- Stays off when feature-flag fetching is disabled, e.g. `DISABLE_TELEMETRY` is set, or when `CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1`.
- Off switches: removing the `advisorModel` key, the `/advisor off` command, or `CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1`. `"off"` / `null` are not documented settings values — never write them.
- `/advisor <model>` saves to the user's global settings (`~/.claude/settings.json`), so it would apply to every repo. Never use it from this skill; write the repo settings file instead.
- Subagents inherit the advisor and apply the same pairing check against their own model.
- The main model decides when to consult: typically before committing to an approach, when an error keeps recurring, and before declaring done. There is no setting to cap calls in Claude Code.
- Each advisor call re-reads the whole conversation, uncached, at the advisor model's rates. Toggling the advisor does not invalidate the main model's cache.
- Best fit: long, multi-step tasks where most turns are routine but plan quality decides the outcome. Little value on short tasks.
- Anthropic's launch post (older models: Sonnet 4.6 / Haiku 4.5 with an Opus 4.6 advisor) reported Sonnet + Opus advisor at +2.7 points on SWE-bench Multilingual with 11.9% lower cost per task, and Haiku + Opus advisor at 41.2% vs 19.7% solo on BrowseComp.

## Effort

- Levels: `low`, `medium`, `high`, `xhigh`, `max` (5.5 models and Fable). Opus 5.5, Sonnet 5.5 and Haiku 5.5 default to `medium`.
- Settings key `effortLevel` (`low` | `medium` | `high` | `xhigh`; `max` is not accepted in settings). Valid in every settings file; a top-level `effortLevel` in project or local settings applies to every model.
- Precedence: `CLAUDE_CODE_EFFORT_LEVEL` env > in-session `/effort` > `--effort` > settings > model default.
- **Subagents:** a subagent on the main session's model runs at the session's effort; a subagent on another model does not get the session level. The `effort` frontmatter field sets it explicitly. The templates use `low` for Explore and test-runner (mechanical work) and `high` for audit (overlooked edge cases are the whole point).

## Subagent models and cost

- Built-in **Explore** runs on the main model, except with a Claude subscription, Console account, or an `ANTHROPIC_BASE_URL` gateway, where it runs on the `opus` alias's model. A project agent named `Explore` replaces it and keeps its own `model` — this is the biggest saving repo-mode offers.
- Built-in **Plan** and **general-purpose** inherit the main model unless `CLAUDE_CODE_SUBAGENT_MODEL` is set.
- Model resolution for a subagent: per-invocation `model` parameter > the agent's `model` frontmatter (`inherit` = main model) > `CLAUDE_CODE_SUBAGENT_MODEL` > main model. So the env var is only a **default** and does not override the helper agents' own `model`. `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` would override everything — never set it.
- Set it per repo in the settings file: `"env": { "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet" }`.
- Subagents send their own requests and count toward the same usage limits. They don't produce smarter answers than the main session; they pay off for parallel work, keeping noisy output (test runs, wide searches, logs) out of the main context, and independent review. Anthropic's multi-agent guidance puts the overhead at roughly 3–10× the tokens of a single agent.
- Non-fork subagents get a separate prompt cache with a 5-minute TTL (`experimental: cacheTtl: 1h` can change it; not used by repo-mode).
- **Haiku 5.5 price tier:** $0.10 / $0.50 per MTok (input / output) for prompts up to 100,000 tokens, $0.50 / $2.50 above that. `autoCompactWindow: 100000` in a Haiku agent makes it compact before crossing that line.
- `/usage` breaks usage down per subagent, skill, plugin and MCP server.

## Delegation guidance (Anthropic blog and best-practices)

- Delegate when gathering context means reading 10+ files, when there are 3+ independent pieces of work, or when verification should not be influenced by the conversation.
- Stay in the main thread for sequential, dependent work, small tasks, and edits to the same file.
- Descriptions route delegation: name the trigger ("before declaring a multi-file change done"), not just the capability. "Use proactively" encourages automatic delegation. Keep the number of agents small — too many specialists make automatic delegation less reliable.
- Ask for a specific return format and for evidence (the command run and its output). Tell reviewers to skip style.
- Restrict tools in the agent file: that limit is enforced by Claude Code, a prompt instruction is not.

## Settings files

| File | Who it affects | Committed? |
|---|---|---|
| `~/.claude/settings.json` | the user, every project | no |
| `.claude/settings.json` | everyone in this repo | yes (team) |
| `.claude/settings.local.json` | the user, this repo only | no |

Precedence (highest first): managed > command line > `.claude/settings.local.json` > `.claude/settings.json` > `~/.claude/settings.json`. Lists such as `permissions.deny` merge across files.

`model`, `effortLevel` and `env` are read at session start; a change needs a new session. `advisorModel`, `model`, `effortLevel`, `env` and `permissions.deny` are valid in all three files. In the shared project file, most `env` values apply only after each teammate trusts the folder.

Settings files are strict JSON: no comments, no trailing commas.

## Subagent files

Project agents live in `.claude/agents/<name>.md` and win over user agents (`~/.claude/agents/`) and plugin agents with the same name. A project agent named `Explore` replaces the built-in Explore agent in that repo.

Fields used by the templates: `name`, `description`, `model`, `effort`, `tools`, `omitClaudeMd`, `maxTurns`, `autoCompactWindow`. Custom subagents load CLAUDE.md files unless `omitClaudeMd: true`. A subagent can spawn its own subagents only if it has the Agent tool; the templates' `tools:` lists leave it out on purpose. Subagents spawned from the main conversation start in the background by default; Read, Grep, Glob and Bash all stay available there.

`isolation: worktree` is deliberately **not** used: a subagent worktree branches from the default branch, not the working branch, and never contains uncommitted changes, so an audit agent there could not see the diff.

## Instruction files

- `CLAUDE.local.md` at the repo root: personal, this repo only. Loads alongside `CLAUDE.md`.
- `CLAUDE.md` at the repo root: shared with the team.
- Block-level HTML comments (`<!-- ... -->`) in these files are stripped before Claude sees them, so the `repo-mode:start` / `repo-mode:end` markers cost no context.
- **AGENTS.md caveat:** by default Claude reads `AGENTS.md` only when there is no `CLAUDE.md`, `.claude/CLAUDE.md`, or `CLAUDE.local.md` in the working directory or above. Creating `CLAUDE.local.md` in a repo that relies on `AGENTS.md` would stop `AGENTS.md` loading. In that case put `@AGENTS.md` as the first line inside the repo-mode block, so it is still imported.

## Read deny rules

Format: `"Read(./**/<dir>/**/*)"` for a directory, `"Read(./**/*.generated.*)"` for a file pattern, inside `permissions.deny`. Gitignored paths are already excluded from Claude's searches, so only propose rules for paths that are **tracked** in git (vendored SDKs, committed generated code, committed build output, minified bundles).

## Code intelligence (LSP) plugins

Anthropic's official marketplace (`claude-plugins-official`) has code intelligence plugins for TypeScript, Python, Go, Rust and other common languages; `typescript-lsp@claude-plugins-official` is the documented TypeScript one. Each needs the language server binary installed on the machine. Do not guess plugin names for other languages: tell the user to open `/plugin` → Discover, search for the language, and install it with "Install for you, in this repo only".

## Git-local ignore

`.git/info/exclude` uses `.gitignore` syntax but is never committed. Use it for personal-mode files so the repo's own `.gitignore` is untouched. Add exact file paths, one per line, under a `# repo-mode` comment line.

## State file

`.claude/repo-mode.json` records everything setup changed, so `/repo-mode:off` can undo exactly that and nothing else:

```json
{
  "version": 2,
  "scope": "personal",
  "appliedAt": "2026-11-08T16:30:00+02:00",
  "settingsFile": ".claude/settings.local.json",
  "settings": { "model": "sonnet", "advisorModel": "opus", "effortLevel": null, "env.CLAUDE_CODE_SUBAGENT_MODEL": null },
  "previousSettings": { "model": null, "advisorModel": null, "effortLevel": null, "env.CLAUDE_CODE_SUBAGENT_MODEL": null },
  "denyRulesAdded": ["Read(./**/vendor/**/*)"],
  "agentsCreated": [".claude/agents/Explore.md", ".claude/agents/test-runner.md", ".claude/agents/audit.md"],
  "rulesFile": "CLAUDE.local.md",
  "rulesFileCreatedBySetup": true,
  "agentsMdImport": false,
  "settingsFileCreatedBySetup": false,
  "excludeLinesAdded": [".claude/settings.local.json", "CLAUDE.local.md", ".claude/agents/Explore.md", ".claude/repo-mode.json"],
  "lspPlugin": null
}
```

In `settings`, `null` means setup did not set that key. `previousSettings` holds the values that were there before setup (`null` = key was absent), so `off` can restore them instead of just deleting. `env.CLAUDE_CODE_SUBAGENT_MODEL` stands for that one entry inside the `env` object; other `env` entries are never touched. A version-1 state file has only `model` and `advisorModel`; treat the missing keys as `null`.
