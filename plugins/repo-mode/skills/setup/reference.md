# repo-mode reference

Facts below come from the Claude Code docs (code.claude.com/docs) and the Claude pricing page, checked 2026-11-08 (workflows: 2026-11-09; Fable versions, advisor pairing table, hooks inside subagents: 2026-11-11). If something here conflicts with what you observe in the user's Claude Code, trust the observation and tell the user.

## Model aliases

`sonnet`, `opus`, `haiku`, `fable` resolve to Claude Code's current default version of each family. On the Anthropic API today: `opus` = Opus 5.5, `sonnet` = Sonnet 5.5, `haiku` = Haiku 5.5, `fable` = Fable 5.2 (Claude Code v2.1.321+; Fable 5 in Claude apps gateway sessions; `ANTHROPIC_DEFAULT_FABLE_MODEL` overrides). On Bedrock / Vertex (Agent Platform) / Foundry / Claude Platform on AWS, `haiku` resolves to Haiku 4.5. A full model ID such as `claude-opus-5-5` is also accepted.

`opusplan` uses `opus` while in plan mode and `sonnet` for execution. `best` uses the same model as `opus`.

Fable needs Fable access, and on some plans a one-time consent to bill Fable usage to usage credits (the user accepts it by running `/model fable` once; that command also saves Fable as the global default, so switch back afterwards with `/model <usual model>`).

## Version floors

| Feature | Claude Code |
|---|---|
| `autoCompactWindow` agent field | v2.1.296+ |
| Haiku 5.5 (main or advisor) | v2.1.293+ |
| Sonnet 5.5 | v2.1.284+ |
| Opus 5.5 | v2.1.280+ |
| `omitClaudeMd` agent field | v2.1.271+ |
| Fable 5.1 | v2.1.257+ |
| Fable 5.2 (`fable` alias on the Anthropic API) | v2.1.321+ |
| `ultracode` setting | v2.1.284+ |
| `workflowSizeGuideline` default `small` on Pro | v2.1.271+ |

Unknown agent frontmatter fields are ignored silently, so an older Claude Code just skips them.

## Advisor pairing rules

The advisor must rank at or above the main model; otherwise Claude Code does not attach it. Haiku 4.5 can call an advisor but can never be one; Haiku 5.5 can be one, but only for a main model at or below it.

| Main model | Accepted advisors |
|---|---|
| Haiku 4.5 | fable, opus, sonnet, haiku 5.5 |
| Sonnet 4.6 | fable, opus, sonnet, haiku 5.5 |
| Opus 4.6 | fable, opus, sonnet (5 or later), haiku 5.5 |
| Sonnet 5 or Haiku 5.5 | fable, opus (4.7 or later), sonnet (5 or later), haiku 5.5 |
| Opus 4.7 or 4.8 | fable, opus (4.7 or later), sonnet 5.5 |
| Sonnet 5.5 | fable, opus (5 or later), sonnet (5.5) |
| Opus 5 / 5.5 (and `opusplan`) | fable, opus (5 or later) — **not** sonnet |
| Fable 5 | fable 5.2, 5.1 or 5 |
| Fable 5.1 | fable 5.2 or 5.1 |
| Fable 5.2 | fable 5.2 only |

With the aliases repo-mode writes, a `fable` main model takes only a `fable` advisor.

Common pairings in the docs: Sonnet main + Opus advisor; Haiku main + Opus advisor ("lowest-cost main model with strong planning").

Other advisor facts:
- Experimental. Anthropic API only: not available on Bedrock, Claude Platform on AWS, Google Cloud's Agent Platform, or Microsoft Foundry.
- Stays off when feature-flag fetching is disabled, e.g. `DISABLE_TELEMETRY` is set, or when `CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1`.
- Off switches: removing the `advisorModel` key, the `/advisor off` command, or `CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1`. `"off"` / `null` are not documented settings values — never write them.
- `/advisor <model>` saves to the user's global settings (`~/.claude/settings.json`), so it would apply to every repo. Never use it from this skill; write the repo settings file instead.
- Subagents inherit the advisor and apply the same pairing check against their own model. So a Haiku 5.5 helper agent can consult an Opus advisor, billed at the advisor's rates on that subagent's conversation. No per-subagent off switch is documented; `/usage` shows whether it happens. Not measured by repo-mode.
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

## Dynamic workflows

- A workflow is a JavaScript script Claude writes to orchestrate many subagents (`agent()`, `pipeline()`, `parallel()`); it runs in the background. Typing `ultracode` in a prompt asks for one; `/effort ultracode` (or the `ultracode` setting) makes Claude write one for every substantive task and sets effort to `xhigh`.
- Cost: the docs say ultracode makes "each request use more tokens and takes longer", and a workflow run "can use meaningfully more tokens than working through the same task in conversation". repo-mode never writes `ultracode`.
- Workflow agents pick their model in the subagent order: a model the script names for a stage, else `CLAUDE_CODE_SUBAGENT_MODEL`, else the session model. So the "Other agents" answer also covers workflow agents the script leaves unassigned.
- `workflowSizeGuideline`: `unrestricted` | `small` | `medium` | `large`; valid in any settings file. Default `medium`, or `small` on Pro (v2.1.271+). It sets the agent count Claude aims for — advice, not a cap.
- Limits: 16 concurrent agents by default (`CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS`, 1–256), 1,000 agents per run; a "Large workflow" warning appears above 25 agents or 1.5M projected tokens.
- Off switches: `"disableWorkflows": true` or `CLAUDE_CODE_DISABLE_WORKFLOWS=1`.

## escalate agent (v1.5.0)

- The advisor takes exactly one model (`advisorModel`), so there is no built-in "Opus advisor, Fable when it's really hard". repo-mode's substitute: an optional read-only `escalate` subagent on `fable` plus a rule in the delegation block telling the main session to call it only after the advisor and two own attempts failed. The main session decides to call it, so it is not guaranteed.
- Docs (sub-agents, model-config, checked 2026-11-11): the subagent `model` field accepts `sonnet`, `opus`, `haiku`, `fable`, a full model ID, or `inherit`; `fable` resolves to Fable 5.2 outside gateway sessions (Fable 5 in Claude apps gateway sessions; `ANTHROPIC_DEFAULT_FABLE_MODEL` overrides). Fable 5.2 needs Claude Code v2.1.321+. Subagent `effort` accepts low/medium/high/xhigh/max (levels depend on the model).
- Not documented: whether a Fable subagent request triggers the Fable usage-credits consent prompt (the docs describe it for the main session only).
- The subagent has no conversation history, so the briefing must carry everything; `omitClaudeMd: true` keeps the Fable-priced context small.

## Test-output filter hook

- Based on the PreToolUse example in the costs docs ("this PreToolUse hook filters test output to show only failures"). A hook returns `hookSpecificOutput.updatedInput` to replace the Bash command before it runs.
- repo-mode's version (`templates/hooks/repo-mode-filter-tests.sh`) improves on the docs example: it keeps the test runner's exit code (`set -o pipefail` with a filter that always succeeds), shows short output (≤ 60 lines) in full, otherwise the failure context (up to 100 lines) plus the last 20 lines, and saves the full output to a temp file whose path it prints.
- It only matches plain test commands with no shell operators (same character rule as the docs example); everything else passes through. It fails open: without `jq`, or on unexpected input, it returns `{}`.
- Registered in the settings file as `hooks.PreToolUse` → `{"matcher": "Bash", "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/repo-mode-filter-tests.sh"}]}`. Hooks are valid in `.claude/settings.local.json`.
- It returns no `permissionDecision`, like the docs example, so the rewritten command goes through the normal permission check: an allow rule such as `Bash(pytest *)` won't match the wrapped command. It does not affect commands started with the Monitor tool. It needs `bash` and `jq`; on native Windows it is unverified.
- **PowerShell variant** (`templates/hooks/repo-mode-filter-tests.ps1`, v1.4.0; tested with `pwsh` 7.6 and Windows PowerShell 5.1): same rules, for the separate `PowerShell` tool. The docs: matcher `Bash|PowerShell` covers shell commands; PowerShell hook input has `tool_input.command` like Bash; `updatedInput` is described generically (not excluded for PowerShell, not stated explicitly). One file, two modes: with no arguments it is the hook (stdin JSON → stdout JSON) and rewrites the command into `& '<script>' -RunCommand '<command>'`; with `-RunCommand` it runs the test command (stderr merged), filters, and exits with the command's exit code. Registration: on native Windows `{"matcher": "PowerShell", "hooks": [{"type": "command", "shell": "powershell", "command": "& \"$env:CLAUDE_PROJECT_DIR/.claude/hooks/repo-mode-filter-tests.ps1\""}]}`; elsewhere `pwsh -NoProfile -File "$CLAUDE_PROJECT_DIR/.claude/hooks/repo-mode-filter-tests.ps1"` with the default shell (the docs describe `shell` for Windows only). The PowerShell tool is automatic on Windows without Git Bash, default-on with Git Bash for claude.ai/Console accounts, opt-in on WSL/Linux/macOS (`pwsh` 7+, `CLAUDE_CODE_USE_POWERSHELL_TOOL=1`); the docs call it a preview. Not verified in a live Claude Code session: that Claude Code accepts the rewritten PowerShell command exactly as it does for Bash, and the hook `shell` field on WSL. State file: a `hooksAdded` entry carries `"shell"` when the group has one.
- Hooks from settings files also run inside subagents (hooks docs: tool events "fire the same configured hooks as in the main conversation", with `agent_id` and `agent_type` in the input). So `test-runner` and `escalate` see filtered output too; their templates tell them to read the saved full-output file before reporting.
- Failure pattern (both variants): `FAIL|ERROR|Error|error:|Traceback|panic:|AssertionError|panicked|Failed asserting`. The last two were added in v1.7.0 after testing against `cargo test` and PHPUnit layouts, where the details of failures in the middle of the output were dropped.
- Verify with `/hooks` (listed under PreToolUse) or `claude --debug-file ./claude-debug.txt` (a `modified tool input keys` line when it rewrites a command).

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

`model`, `effortLevel`, `workflowSizeGuideline` and `env` are read at session start; a change needs a new session. `advisorModel`, `model`, `effortLevel`, `workflowSizeGuideline`, `env` and `permissions.deny` are valid in all three files. In the shared project file, most `env` values apply only after each teammate trusts the folder.

Settings files are strict JSON: no comments, no trailing commas.

`/model <name>` inside a session switches that session and also saves the model as the user's global default (`~/.claude/settings.json`), exactly like the `/advisor` picker; the repo file still wins in this repo at the next session start. Observed once on v2.1.321, not found in the docs read: a resumed session (`--continue` / `--resume`) kept the model it had instead of re-reading `model` from settings, so a fresh session is the reliable way to pick up a changed model.

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

Secrets rules (v1.6.0, optional, safety not cost): `Read(./.env)`, `Read(./.env.*)` (both are the docs' own example), `Read(~/.ssh/**)` (`~/` = home), `Read(./secrets/**)`. Docs (permissions, checked 2026-11-11): Read/Edit rules use gitignore syntax; `//path` is absolute, `~/path` home, `/path` relative to the settings source, `path` or `./path` relative to the current directory. Read denies apply to the built-in file tools and to file commands Claude Code recognizes in Bash (`cat`, `head`, `tail`, `sed`, `tee`, redirections), not to scripts that open files themselves or `grep -r` without a file name; the docs point to the sandbox for OS-level enforcement. Grep/Glob: best effort. The docs don't say whether Read denies apply inside subagents. Whether `./.env` also matches `sub/.env` is not stated (bare `.env` matches at any depth). A `.claudeignore` file has no effect.

## Handoff (v1.6.0)

`/repo-mode:handoff` writes `HANDOFF.md` (goal, state, next steps, decisions, commands, risks; about 40 lines) so the next session can start fresh. Why it saves tokens: a `--continue`/`--resume` re-reads the whole conversation on its first message without the cache, while a new session with a short handoff starts small. It writes only that one file, never commits it, and is not recorded in the state file, so `/repo-mode:off` doesn't touch it.

## Code intelligence (LSP) plugins

Anthropic's official marketplace (`claude-plugins-official`) has code intelligence plugins for TypeScript, Python, Go, Rust and other common languages; `typescript-lsp@claude-plugins-official` is the documented TypeScript one. Each needs the language server binary installed on the machine. Do not guess plugin names for other languages: tell the user to open `/plugin` → Discover, search for the language, and install it with "Install for you, in this repo only".

## Git-local ignore

`.git/info/exclude` uses `.gitignore` syntax but is never committed. Use it for personal-mode files so the repo's own `.gitignore` is untouched. Always take its path from `git rev-parse --git-path info/exclude`: in a git worktree `.git` is a file, and the exclude file lives in the main repository's git directory. Personal-scope files are untracked, so git itself does not carry them into a new worktree. Add exact file paths, one per line, under a `# repo-mode` comment line.

## Re-running setup

When `.claude/repo-mode.json` already exists, the earlier state is the baseline and the run is an update:

- **`previousSettings`**: for each key, if the earlier state's `settings.<key>` is non-`null` (setup wrote it), keep the earlier `previousSettings.<key>`. Capture from the current file only for keys setup had not written before. Recapturing would record repo-mode's own values as "previous" and `/repo-mode:off` would restore the wrong thing.
- **A key setup wrote before that the user now leaves at its default / "no change"**: restore the earlier previous value (remove the key if it was `null`) and record `settings.<key>: null`. Advisor = None is the exception: the user asked for no advisor in this file, so remove the key and record it as "State file" describes (`false` if there is an earlier value to put back, else `null`); never write the earlier advisor back during setup.
- **`settingsFileCreatedBySetup`, `rulesFileCreatedBySetup`**: keep `true` if the earlier state says `true`; the file exists now only because setup created it.
- **No longer chosen**: an agent in `agentsCreated` → delete its file if it still has the `<!-- managed by repo-mode -->` line, otherwise ask; a group in `hooksAdded` → remove it from the settings file, and delete its script from `hookScriptsCreated` if it still has `# managed by repo-mode`; a rule in `denyRulesAdded` → remove it from `permissions.deny`; rules block answered "No", or no helper agent selected any more (the Rules question is then skipped) → remove the block (and the file, if setup created it and nothing else is left); exclude lines of deleted files → remove.
- **The new state file lists everything repo-mode manages after this run**, not only what this run added: unchanged items stay in the lists, removed items leave them.
- Every removal appears in the step-5 plan, deletions listed separately, and nothing happens before approval.
- **Deny rules**: a rule already in `denyRulesAdded` is repo-mode's own. Offer it again marked "(currently on)"; it is removed only if the user unselects it.
- **Hook groups**: never add a group that is already there; one group per variant.
- **Exclude file**: one `# repo-mode` header. Lines from the earlier run stay in the file and in `excludeLinesAdded` even though `git check-ignore` now reports them as ignored. The exclude file is shared by all worktrees of the repository, so these lines apply in every worktree; `/repo-mode:off` asks before removing them when the repository has more than one worktree.
- **Scope change** (personal ↔ team): not done in a re-run. After Round 1, if the Scope answer differs from the state's `scope`, stop and tell the user to run `/repo-mode:off`, then setup again.

## State file

`.claude/repo-mode.json` records everything setup changed, so `/repo-mode:off` can undo exactly that and nothing else:

```json
{
  "version": 2,
  "scope": "personal",
  "appliedAt": "2026-11-08T16:30:00+02:00",
  "settingsFile": ".claude/settings.local.json",
  "settings": { "model": "sonnet", "advisorModel": "opus", "effortLevel": null, "workflowSizeGuideline": null, "env.CLAUDE_CODE_SUBAGENT_MODEL": null },
  "previousSettings": { "model": null, "advisorModel": null, "effortLevel": null, "workflowSizeGuideline": null, "env.CLAUDE_CODE_SUBAGENT_MODEL": null },
  "denyRulesAdded": ["Read(./**/vendor/**/*)"],
  "agentsCreated": [".claude/agents/Explore.md", ".claude/agents/test-runner.md", ".claude/agents/audit.md"],
  "hookScriptsCreated": [".claude/hooks/repo-mode-filter-tests.sh"],
  "hooksAdded": [{ "event": "PreToolUse", "matcher": "Bash", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/repo-mode-filter-tests.sh" }],
  "rulesFile": "CLAUDE.local.md",
  "rulesFileCreatedBySetup": true,
  "agentsMdImport": false,
  "settingsFileCreatedBySetup": false,
  "excludeLinesAdded": [".claude/settings.local.json", "CLAUDE.local.md", ".claude/agents/Explore.md", ".claude/hooks/repo-mode-filter-tests.sh", ".claude/repo-mode.json"],
  "lspPlugin": null
}
```

In `settings`, `null` means setup did not touch that key. `false` means setup **removed** the key (today only `advisorModel`, with Advisor = None): record `false` when `previousSettings` for that key is non-`null`, i.e. there is a value to put back, both on a first run that removes the user's own advisor and on a re-run that drops an advisor setup wrote earlier; if there is nothing to put back, record `null`. `previousSettings` holds the values that were there before setup (`null` = key was absent), so `off` can restore them instead of just deleting. `env.CLAUDE_CODE_SUBAGENT_MODEL` stands for that one entry inside the `env` object; other `env` entries are never touched. A version-1 state file has only `model` and `advisorModel`; treat any missing key as `null` and any missing list (`hooksAdded`, `hookScriptsCreated`) as empty.
