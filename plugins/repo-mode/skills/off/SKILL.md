---
name: off
description: Undo repo-mode in this repository — restores the previous model/advisor/effort/subagent-model/workflow-size settings and removes the agents, rules block, deny rules and git-exclude lines that /repo-mode:setup added. Shows the plan and waits for approval before changing anything.
disable-model-invocation: true
---

# repo-mode off

Undo exactly what `/repo-mode:setup` recorded in `.claude/repo-mode.json` — nothing else.

Ground rules:
- Talk to the user in the language they use (default: Greek).
- **Change, delete, or overwrite nothing until the user approves the plan.** Before that, only read.
- Never touch `~/.claude/settings.json`, and never run `/advisor` or `/model`.
- If a file was changed by hand since setup, don't silently discard those changes: show the difference and ask.

## Step 1 — Read the state

1. Read `.claude/repo-mode.json` at the repository root. If it doesn't exist, say repo-mode isn't set up here (or was set up by hand), show any repo-mode traces you can find — agent files containing `<!-- managed by repo-mode -->`, a `<!-- repo-mode:start -->` block in `CLAUDE.md` / `CLAUDE.local.md`, a `# repo-mode` section in `.git/info/exclude`, `.claude/hooks/repo-mode-filter-tests.sh` and its PreToolUse entry — and ask whether to remove those. Stop if the user says no.
2. Read the current settings file named in the state, each file in `agentsCreated` and `hookScriptsCreated`, the `rulesFile`, and `.git/info/exclude`.

## Step 2 — Build the plan (no changes yet)

1. **Settings file**: for each key in the state's `settings` that setup set (non-`null`): `model`, `advisorModel`, `effortLevel`, `workflowSizeGuideline`, and `env.CLAUDE_CODE_SUBAGENT_MODEL` (the one entry inside `env`; a version-1 state file only has the first two):
   - If the current value still equals what setup wrote: restore `previousSettings` (remove the key if the previous value is `null`). If `env` ends up empty, remove it; never touch other `env` entries.
   - If the current value differs (changed by hand after setup): show it and ask whether to keep it or restore the previous value.
   - Remove each entry in `denyRulesAdded` from `permissions.deny`. If `permissions.deny` ends up empty, remove it; if `permissions` ends up empty, remove it.
   - Keep every other key untouched.
   - If `settingsFileCreatedBySetup` is true and the file would end up as `{}`, plan to delete it.
   - Show the full JSON before and after.
   - For each entry in `hooksAdded`: remove from `hooks.<event>` the group whose matcher, command and `shell` (if recorded) match it exactly; leave every other hook. If `hooks.<event>` ends up empty, remove it; if `hooks` ends up empty, remove it.
2. **Hook scripts** in `hookScriptsCreated`: plan to delete each one that still contains `# managed by repo-mode`; otherwise list it separately and ask. Remove `.claude/hooks/` only if it ends up empty and setup created it.
3. **Agent files** in `agentsCreated`: plan to delete each one that still contains `<!-- managed by repo-mode -->`. If one no longer has the marker, or is missing, list it separately and ask.
4. **Rules block**: remove everything from `<!-- repo-mode:start -->` to `<!-- repo-mode:end -->` inclusive in `rulesFile`. If `rulesFileCreatedBySetup` is true and nothing but whitespace remains, plan to delete the file. Show the before/after of that file.
5. **Git exclude**: remove the lines in `excludeLinesAdded` and the `# repo-mode` header line from `.git/info/exclude`. Leave all other lines.
6. **Code intelligence plugin**: if `lspPlugin` is set, offer `claude plugin disable <plugin> --scope local` (or uninstall) — as a separate yes/no, since the user may want to keep it.
7. **State file**: delete `.claude/repo-mode.json`.
8. If `.claude/agents/` (or `.claude/`) would be left empty, plan to remove the empty folder only if setup created it; otherwise leave it.

Show the whole plan, listing every file that will be **deleted** separately from files that will be **edited**. Then ask with `AskUserQuestion` (header "Undo?"): `Apply` · `Cancel`. If the tool isn't available, ask in plain text and wait.

## Step 3 — Apply and report

Apply the approved plan. Re-read the settings file and confirm it is valid JSON. If any step fails, stop and report exactly what was and wasn't done; don't delete the state file in that case.

Then tell the user:
- What was restored, edited, and deleted.
- **Start a new Claude Code session** for the model change to take effect.
- If `~/.claude/settings.json` sets `model`, `advisorModel`, `effortLevel`, `workflowSizeGuideline` or `env.CLAUDE_CODE_SUBAGENT_MODEL`, those global values will now apply in this repo — mention them.
