---
name: status
description: Read-only report of the model, advisor, effort level, subagents and their models, delegation rules and deny rules that apply in this repository, and where each setting comes from.
disable-model-invocation: true
---

# repo-mode status

Read-only. Do not create, edit, or delete anything. Talk to the user in the language they use (default: Greek).

1. Read, if present: `.claude/repo-mode.json`, `.claude/settings.local.json`, `.claude/settings.json`, `~/.claude/settings.json`, `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, and the list of `.claude/agents/*.md` (note which contain `<!-- managed by repo-mode -->`).
2. Work out the effective value of `model`, `advisorModel`, `effortLevel` and `env.CLAUDE_CODE_SUBAGENT_MODEL` using the precedence local > project > user (managed settings and command-line flags can override all of these; say that you can't see those from files). Show each with the file it comes from.
3. Report in a short table:
   - repo-mode: on (scope, date from the state file) / off / partial (traces without a state file).
   - Main model, advisor, effort level and default subagent model (`CLAUDE_CODE_SUBAGENT_MODEL`), each with source file. Note that `CLAUDE_CODE_EFFORT_LEVEL` in the shell environment would override `effortLevel`.
   - Subagents in `.claude/agents/`, their `model` and `effort`, and whether repo-mode manages them.
   - Delegation rules block: present in which file / absent.
   - `permissions.deny` Read rules, and which of them repo-mode added.
   - Code-intelligence plugin recorded by repo-mode, if any.
4. Flag problems:
   - Advisor/main pairs that the pairing table in `${CLAUDE_PLUGIN_ROOT}/skills/setup/reference.md` rejects (e.g. Opus or `opusplan` main + Sonnet advisor, Sonnet 5.5 main + Haiku advisor).
   - Main model Opus/`opusplan`/Fable with no `CLAUDE_CODE_SUBAGENT_MODEL` and no project `Explore` agent: general-purpose, Plan and (on subscriptions) Explore subagents run on the expensive model.
   - `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` set anywhere: it overrides the helper agents' own models.
   - `model` / `advisorModel` / `effortLevel` set globally in `~/.claude/settings.json` (applies to every repo where repo-mode is off).
   - Files listed in the state file that no longer exist, or managed agents/blocks with no state file.
   - Personal-scope files that `git status --porcelain` shows as untracked or modified (i.e. not excluded and could be committed by mistake).
5. Remind the user that the live session is the final word: `/status` shows the model and which settings files loaded, and an `Advisor Tool (experimental) is on` notification at session start means the advisor is active. Changing the advisor through the `/advisor` picker saves it globally (every repo), so use `/repo-mode:setup` instead.
