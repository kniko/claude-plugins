---
name: setup
description: Interactive wizard that configures this repository's main model, effort level, advisor model, helper subagents (Explore, test-runner, audit), the default model for other subagents and workflow agents, workflow size, delegation rules, Read deny rules, an optional test-output filter hook and code-intelligence plugin. Writes nothing until the user approves the full plan.
disable-model-invocation: true
---

# repo-mode setup

You are configuring Claude Code for the repository the session was started in. Read [reference.md](reference.md) before you start; it holds the pairing rules, cost facts, file locations and the state-file format. Agent and rules templates are in the `templates/` folder next to this file (`${CLAUDE_SKILL_DIR}/templates/`).

Ground rules for the whole run:
- **Ask, don't guess.** Every choice comes from the user. Use the `AskUserQuestion` tool for each round (at most 4 questions per call, 2–4 options each, short headers, put the recommended option first and mark it "(Recommended)"). If that tool is unavailable, ask the same questions in plain text and wait.
- **Talk to the user in the language they use** (default: Greek). Keep model names and file paths as-is.
- **Write nothing, delete nothing, overwrite nothing until the user approves the final plan** (step 5). Before that, only read files and run read-only commands.
- **Never run `/advisor`, `/model`, `/effort`, or edit `~/.claude/settings.json`.** All changes go into this repository.
- If something you need isn't verifiable (a plugin name, a version), say so instead of inventing it.

## Step 0 — Preflight (read-only)

1. Find the repository root (`git rev-parse --show-toplevel`). If the session is not at the root, tell the user that Claude Code reads the repo's `.claude/settings*.json` and `CLAUDE.md` from the folder it was started in, and ask whether to continue at the root path or stop. If this isn't a git repo, say that personal-mode git exclusion will be skipped and continue only if the user agrees.
2. Run `claude --version` if possible and note it. If it is below v2.1.296, list what needs a newer version (table "Version floors" in reference.md): `autoCompactWindow` v2.1.296, Haiku 5.5 v2.1.293, Sonnet 5.5 v2.1.284, Opus 5.5 v2.1.280, `omitClaudeMd` v2.1.271. Older versions silently ignore unknown agent fields.
3. Read, if they exist: `.claude/repo-mode.json`, `.claude/settings.local.json`, `.claude/settings.json`, `~/.claude/settings.json` (read only), `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.git/info/exclude`, and the list of files in `.claude/agents/`.
4. If `.claude/repo-mode.json` exists, repo-mode is already set up here. Show what it recorded and ask: **change the settings** (continue; the plan in step 5 will show old → new) or **cancel**.
5. If `~/.claude/settings.json` sets `model`, `advisorModel`, `effortLevel`, `workflowSizeGuideline`, `ultracode` or `env.CLAUDE_CODE_SUBAGENT_MODEL`, tell the user: those are global and apply in every repo where repo-mode is off; the repo file will override them here. Do not change the global file.
6. Check whether `bash` and `jq` are on PATH (`command -v bash jq`). The test-output filter (Round 4) needs both; note the result.
7. If any existing `.claude/agents/` file is named `Explore.md`, `test-runner.md`, or `audit.md` and was not created by repo-mode (no `<!-- managed by repo-mode -->` line), note it — the user must decide later whether to replace it or skip that agent.

## Step 1 — Round 1: models and scope

Ask these four together:

1. **Main model** (header "Main model"): `Sonnet (Recommended)` — cheaper main model, pairs with an Opus advisor · `Opus` — strongest Opus as main model · `opusplan` — Opus while in plan mode, Sonnet for execution · `Haiku` — cheapest; with an Opus advisor the docs call it the lowest-cost pairing with strong planning. Say in the question text that "Other" accepts `fable` (needs Fable access) or a full model ID such as `claude-opus-5-5`.
2. **Advisor** (header "Advisor"): `Opus (Recommended)` · `Fable` · `Sonnet` · `None`. Explain in the option description that the advisor is consulted at decision points (before committing to an approach, on recurring errors, before declaring done) and must rank at or above the main model.
3. **Helper subagents** (header "Subagents", multiSelect): `Explore` — repo map + call sites, read-only; replaces the built-in Explore, which runs on Opus on subscription accounts · `test-runner` — runs tests, returns only failures verbatim · `audit` — independent read-only review of the uncommitted diff (overlaps with the built-in `/code-review`; pick it if you want the review to run automatically).
4. **Scope** (header "Scope"): `Only me, this repo (Recommended)` — writes `.claude/settings.local.json`, `CLAUDE.local.md`, hides new files via `.git/info/exclude`; nothing to commit · `Whole team (committed)` — writes `.claude/settings.json` and `CLAUDE.md`; teammates get it when you commit.

Then validate the main/advisor pair against the table in reference.md:
- Treat `opusplan` as Opus for the check (it runs Opus in plan mode): Fable or Opus advisor only.
- Opus main + Sonnet advisor, Sonnet 5.5 main + Haiku advisor, or Fable main + non-Fable advisor → not accepted; explain and ask again.
- Haiku as advisor → only accepted for a Haiku 5.5 main model, and pointless there; recommend Opus instead.
- Haiku main → accepted with an Opus, Sonnet, or Fable advisor (v2.1.293+).
- Fable anywhere → remind them it needs Fable access and possibly the one-time `/model fable` consent.
- Any advisor → remind them once: experimental, Anthropic API only (not Bedrock/Vertex/Foundry), off if `DISABLE_TELEMETRY` or `CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1` is set, each consult re-reads the whole conversation uncached at advisor rates — worth it for long multi-step work, not for short tasks.

For team scope, also warn: `model`, `advisorModel`, `effortLevel`, `workflowSizeGuideline` and `env` in `.claude/settings.json` apply to every teammate, and the advisor fails for anyone not on the Anthropic API.

If Advisor = None but `~/.claude/settings.json` sets `advisorModel`, explain that a repo file cannot switch off a global advisor (the only documented off switches are removing the key, `/advisor off`, or `CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1`), so that global advisor will still apply here. Suggest they handle it themselves if they want per-repo control; don't do it for them.

## Step 2 — Round 2: subagent models

Ask about the helper agents the user selected, plus the default for every other subagent:

- **Explore model** (header "Explore"): `Haiku (Recommended)` · `Sonnet` · `Inherit` (same as main).
- **test-runner model** (header "Tests"): `Haiku (Recommended)` · `Sonnet` · `Inherit`.
- **audit model** (header "Audit"): `Sonnet (Recommended)` — judgment task, Haiku is the weakest choice · `Opus` · `Inherit`.
- **Other subagents** (header "Other agents") — the model for general-purpose, Plan, workflow agents and any subagent without its own `model` (a workflow script that names a model for a stage still wins), set through `env.CLAUDE_CODE_SUBAGENT_MODEL`: if the main model is Opus, opusplan or Fable: `Sonnet (Recommended)` — otherwise those subagents also run on the expensive main model · `Haiku` · `Same as main (no change)`. If the main model is Sonnet or Haiku: `Same as main (Recommended)` · `Haiku` · `Sonnet`.

Write the model values as the aliases `haiku` / `sonnet` / `opus` / `inherit`. If Explore = Haiku, the rendered Explore file gets `autoCompactWindow: 100000` (see reference.md, Haiku price tier); otherwise drop that line.

If a selected agent's file already exists and isn't managed by repo-mode, ask whether to **replace it** or **skip that agent**.

## Step 3 — Scan the repository (read-only)

1. **Tracked generated/vendored code.** With `git ls-files`, look for tracked paths under directories such as `vendor/`, `third_party/`, `external/`, `generated/`, `gen/`, `dist/`, `build/`, `out/`, `bin/`, `obj/`, `node_modules/`, and tracked files matching `*.generated.*`, `*.min.js`, `*.min.css`, `*.designer.cs`, `*.g.cs`, `*.pb.go`, `*_pb2.py`, lock files over ~1 MB. Count files per candidate. Ignore anything that is gitignored (already excluded from search).
2. **Languages.** Count tracked files by extension and name the top languages.
3. Check existing `permissions.deny` entries in the target settings file so you don't propose duplicates.

## Step 4 — Round 3: effort, workflows, rules and deny rules; Round 4: test output and code intelligence

Round 3 — ask together (skip a question if there's nothing to ask):

- **Main effort** (header "Effort"): `Model default (Recommended)` — writes nothing; the 5.5 models default to `medium` · `high` — for work where overlooked edge cases are costly · `xhigh` · `low` — cheapest, for routine edits. Written as `effortLevel`. `max` is not a valid settings value; mention it can only be chosen per session with `/effort`.
- **Workflow size** (header "Workflows") — how many agents Claude aims for when it writes a dynamic workflow (advice, not a hard cap): `Default (Recommended)` — writes nothing; `medium`, or `small` on Pro (v2.1.271+) · `small` — fewest agents, lowest cost · `large` — big refactors and audits · `unrestricted`. Written as `workflowSizeGuideline`. Mention that ultracode (Claude writes a workflow for every substantive task, at `xhigh` effort) is deliberately not offered: it uses more tokens per request; turn it on per session with `/effort ultracode` when a task is big enough.
- **Delegation rules** (header "Rules", only if subagents were selected): `Yes (Recommended)` — short lines telling the main session when to delegate and what to ask back · `Yes + stop fix loops` — also stop a fix-and-retest loop after two rounds in a row without progress, and report instead · `No`.
- **Read deny rules** (header "Deny reads", multiSelect): one option per candidate found in step 3 (up to 4, biggest first), each with its file count, e.g. `vendor/ (1,240 files)`. If there are more than 4, mention the rest in the question text and let the user name them via "Other". If none were found, skip this question and say so.
Round 4 — ask together:

- **Test output filter** (header "Test output"): `Yes (Recommended)` — a PreToolUse hook rewrites plain test commands (`pytest`, `npm test`, `go test`, `cargo test`, …) so Claude sees only the failure context and the last 20 lines, keeps the real exit code, and saves the full output to a temp file it can read; output of 60 lines or less is shown in full; any command with shell operators passes through unchanged · `No`. If `bash` or `jq` is missing (step 0), don't offer Yes: say what's missing and that the hook would do nothing without it. Mention that the rewritten command goes through the normal permission check, so an allow rule such as `Bash(pytest *)` no longer matches it and Claude may ask once per run (auto mode decides by itself).
- **Code intelligence** (header "LSP", only if a main language was found): `Install <language> code-intelligence plugin for this repo (Recommended)` · `Skip`. Only TypeScript's plugin name is verified (`typescript-lsp@claude-plugins-official`); for other languages, the plan will tell the user to install it from `/plugin` → Discover with "Install for you, in this repo only". Mention the language server binary must be installed on the machine.

## Step 5 — Show the full plan and wait for approval

Build the complete plan without writing anything, and show it to the user:

1. **Settings file** (`.claude/settings.local.json` for personal, `.claude/settings.json` for team): show the full JSON **before** and **after**. Merge, never drop existing keys (keep `permissions.allow`, `enabledPlugins`, hooks, other `env` entries, everything). Set `model`; set `advisorModel` (or, if Advisor = None, remove `advisorModel` only if it exists in this file and say so); set `effortLevel` if chosen; set `env.CLAUDE_CODE_SUBAGENT_MODEL` if chosen (never set `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` — it would override the helper agents' own models); set `workflowSizeGuideline` if chosen; never write `ultracode`; append chosen deny rules to `permissions.deny` without duplicates; if the test-output filter was chosen, append this group to `hooks.PreToolUse` (keep every existing hook): `{"matcher": "Bash", "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/repo-mode-filter-tests.sh"}]}`. Valid strict JSON only.
2. **Agent files**: for each selected agent, the path `.claude/agents/<name>.md` and its full content, rendered from `${CLAUDE_SKILL_DIR}/templates/<name>.md` with `{{MODEL}}` replaced and, in Explore, `{{AUTOCOMPACT}}` replaced by `autoCompactWindow: 100000` (Haiku) or the line removed. Keep the templates' `effort` values. Mark any file that will replace an existing one.
3. **Rules block** (if chosen): target `CLAUDE.local.md` (personal) or `CLAUDE.md` (team). Render `templates/rules-block.md`, keeping only the lines for selected agents and dropping empty placeholder lines:
   - `{{RULE_EXPLORE}}` → `- Use the Explore subagent for searches across 10+ files or 3+ independent places; ask it for paths and line refs, not file contents. Do small, targeted lookups yourself.`
   - `{{RULE_TESTS}}` → `- Run single tests directly. Delegate full test-suite runs, builds and long log output to the test-runner subagent.`
   - `{{RULE_AUDIT}}` → `- Before declaring a multi-file change done, run the audit subagent on the current diff and the task description.`
   - `{{RULE_LOOPS}}` (only with "Yes + stop fix loops") → `- If a fix-and-retest loop goes two rounds in a row without progress, stop and report what you tried instead of trying again.`
   - `{{RULE_RETURN}}` (always, when any agent is selected) → `- When delegating, say exactly what to return (short summary, path:line refs) and require evidence — the command run and its output, not just "tests pass". Never run two subagents that edit the same file.`
   If a repo-mode block already exists, replace only the text between the markers. If the target file doesn't exist, it will be created containing only the block. **AGENTS.md caveat:** for personal scope, if the repo has `AGENTS.md` and no `CLAUDE.md` / `.claude/CLAUDE.md` / `CLAUDE.local.md`, put `@AGENTS.md` as the first line inside the block and explain why.
4. **Hook script** (if the test-output filter was chosen): `.claude/hooks/repo-mode-filter-tests.sh`, copied unchanged from `${CLAUDE_SKILL_DIR}/templates/hooks/repo-mode-filter-tests.sh` and made executable. Mark it if a file with that name exists and has no `# managed by repo-mode` line, and ask before replacing it.
5. **Git exclusion** (personal scope, git repo only): the exact lines to add to `.git/info/exclude` under a `# repo-mode` line — every file setup will create that is not already ignored: the settings file, `CLAUDE.local.md`, each agent file, the hook script, and `.claude/repo-mode.json`. Check with `git check-ignore -q <path>` and skip paths already ignored.
6. **Code intelligence**: the exact command (`claude plugin install <plugin>@claude-plugins-official --scope local`) or the `/plugin` instructions.
7. **State file** `.claude/repo-mode.json` with its full content (format in reference.md), including `previousSettings` captured from the current file.

Then ask with `AskUserQuestion` (header "Apply?"): `Apply all changes` · `Change answers` (go back to step 1) · `Cancel` (write nothing).

## Step 6 — Apply

Only after "Apply all changes":
1. Write/merge the settings file. Re-read it afterwards and confirm it parses as JSON.
2. Create `.claude/agents/` if needed and write the agent files. If the test-output filter was chosen, create `.claude/hooks/`, copy the script and `chmod +x` it.
3. Insert or replace the rules block.
4. Append the exclude lines to `.git/info/exclude` (personal scope).
5. Write `.claude/repo-mode.json`.
6. For the LSP plugin: if the user approved running the command, run it from the repo root; if it fails, show the error and give the `/plugin` instructions instead. Never retry with a guessed name.

If any step fails, stop, report exactly what was and wasn't written, and keep the state file consistent with what actually happened.

## Step 7 — Report

Tell the user, briefly:
- What changed, file by file.
- **Start a new Claude Code session** in this repo for the model, effort, env, workflow size, hooks and agents to load. With the test-output filter, `/hooks` should list it under PreToolUse.
- How to check: `/status` shows the model and which settings files loaded; when the advisor is active, Claude Code shows an `Advisor Tool (experimental) is on` notification at session start; asking Claude "which subagents are available?" lists the agents; `/usage` breaks usage down per subagent. Warn them **not** to pick anything in the `/advisor` picker: that saves the advisor to their global settings for every repo.
- `/repo-mode:status` shows the current state; `/repo-mode:off` undoes everything recorded in `.claude/repo-mode.json`.
- For team scope: which files to commit.
