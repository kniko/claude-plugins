# repo-mode reference

Facts below come from the Claude Code docs (code.claude.com/docs, checked 2026-11-07). If something here conflicts with what you observe in the user's Claude Code, trust the observation and tell the user.

## Model aliases

`sonnet`, `opus`, `haiku`, `fable` resolve to Claude Code's current default version of each family. On the Anthropic API today: `opus` = Opus 5.5, `sonnet` = Sonnet 5.5, `haiku` = Haiku 5.5, `fable` = Fable 5.1. On Bedrock / Vertex (Agent Platform) / Foundry / Claude Platform on AWS, `haiku` resolves to Haiku 4.5. A full model ID such as `claude-opus-5-5` is also accepted.

Version floors: Opus 5.5 needs Claude Code v2.1.280+, Sonnet 5.5 v2.1.284+, Haiku 5.5 v2.1.293+.

Fable needs Fable access, and on some plans a one-time consent to bill Fable usage to usage credits (the user accepts it by running `/model fable` once).

## Advisor pairing rules

The advisor must rank at or above the main model. Haiku can call an advisor but can never be one.

| Main model | Accepted advisors |
|---|---|
| Haiku 4.5 | fable, opus, sonnet |
| Sonnet 5.5 | fable, opus (5 or later), sonnet (5.5) |
| Opus 5 / 5.5 | fable, opus (5 or later) — **not** sonnet |
| Fable 5 | fable 5.1 or fable 5 |
| Fable 5.1 | fable 5.1 only |

Haiku 5.5 is not listed in the docs' pairing table or its supported-main-model list (only Haiku 4.5 is). If the user picks haiku as the main model with an advisor, say this is unverified and tell them to check with `/advisor` after restarting.

Other advisor facts:
- Experimental. Anthropic API only: not available on Bedrock, Claude Platform on AWS, Google Cloud's Agent Platform, or Microsoft Foundry.
- Stays off when feature-flag fetching is disabled, e.g. `DISABLE_TELEMETRY` is set, or when `CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1`.
- Turned off only by **removing** the `advisorModel` key. `"off"` / `null` are not documented values — never write them.
- `/advisor <model>` saves to the user's global settings (`~/.claude/settings.json`), so it would apply to every repo. Never use it from this skill; write the repo settings file instead.
- Subagents inherit the advisor and apply the same pairing check against their own model.
- Each advisor call re-reads the whole conversation, uncached, at the advisor model's rates.

## Settings files

| File | Who it affects | Committed? |
|---|---|---|
| `~/.claude/settings.json` | the user, every project | no |
| `.claude/settings.json` | everyone in this repo | yes (team) |
| `.claude/settings.local.json` | the user, this repo only | no |

Precedence (highest first): managed > command line > `.claude/settings.local.json` > `.claude/settings.json` > `~/.claude/settings.json`. Lists such as `permissions.deny` merge across files.

`model` is read at session start; a change needs a new session. `advisorModel`, `model`, and `permissions.deny` are valid in all three files.

Settings files are strict JSON: no comments, no trailing commas.

## Subagent files

Project agents live in `.claude/agents/<name>.md` and win over user agents (`~/.claude/agents/`) with the same name. A project agent named `Explore` replaces the built-in Explore agent in that repo.

Custom subagents load CLAUDE.md files unless `omitClaudeMd: true` (needs Claude Code v2.1.271+). A subagent can spawn its own subagents only if it has the Agent tool; the templates' `tools:` lists leave it out on purpose.

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
  "version": 1,
  "scope": "personal",
  "appliedAt": "2026-11-07T16:30:00+02:00",
  "settingsFile": ".claude/settings.local.json",
  "settings": { "model": "sonnet", "advisorModel": "opus" },
  "previousSettings": { "model": null, "advisorModel": null },
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

`previousSettings` holds the values that were there before setup (`null` = key was absent), so `off` can restore them instead of just deleting.
