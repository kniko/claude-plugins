# Changelog

All notable changes to **repo-mode**. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

## [1.3.0] - 2026-11-09

### Added
- Optional **test-output filter**: a PreToolUse hook (`.claude/hooks/repo-mode-filter-tests.sh`) that rewrites plain test commands (`pytest`, `npm test`, `go test`, `cargo test`, `dotnet test`, …). Claude sees the full output when it is 60 lines or less; otherwise the failure context (up to 100 lines) and the last 20 lines. The real exit code is kept, and the full output is saved to a temp file. Commands with shell operators pass through unchanged; without `jq` the hook does nothing.
- Setup preflight checks for `bash` and `jq`; new "Test output" question in Round 4.
- `/repo-mode:off` removes the hook entry and script; `/repo-mode:status` reports them.

## [1.2.0] - 2026-11-08

### Added
- "Workflows" question: per-repo `workflowSizeGuideline` (default / `small` / `large` / `unrestricted`).
- Optional delegation rule: stop a fix-and-retest loop after two rounds without progress.
- English README (`README.en.md`); Greek stays the default `README.md`.
- Installation section moved to the top of the README, with update, uninstall and migration steps.

### Changed
- `CLAUDE_CODE_SUBAGENT_MODEL` is documented as also covering dynamic-workflow agents.
- `/repo-mode:status` flags `ultracode: true`; ultracode is never written by setup.

## [1.1.0] - 2026-11-08

### Added
- `effort` per agent: `low` for Explore and test-runner, `high` for audit.
- `autoCompactWindow: 100000` for a Haiku Explore agent (Haiku 5.5 price tier above 100K-token prompts).
- "Other agents" question: default model for general-purpose, Plan and other subagents via `env.CLAUDE_CODE_SUBAGENT_MODEL`.
- Main-session effort question (`effortLevel`) and `opusplan` as a main-model option.
- Delegation rule asking for return format and evidence.
- README with a benefits table, diagrams and sources.

### Changed
- Advisor pairing table updated: Haiku 5.5 as main model with an advisor is supported.
- Delegation threshold: 10+ files or 3+ independent pieces (was more than ~5 files).
- Agent descriptions name their trigger and say "use proactively"; audit asks for evidence and skips style.

## [1.0.0] - 2026-11-08

### Added
- `/repo-mode:setup` wizard: main model, advisor, helper subagents (Explore, test-runner, audit), scope, delegation rules, Read deny rules, code-intelligence plugin. Writes nothing until the plan is approved.
- `/repo-mode:status` (read-only report) and `/repo-mode:off` (exact undo from `.claude/repo-mode.json`).
- Personal scope hides all files via `.git/info/exclude`.

[1.3.0]: https://github.com/kniko/claude-plugins/releases/tag/repo-mode-v1.3.0
[1.2.0]: https://github.com/kniko/claude-plugins/releases/tag/repo-mode-v1.2.0
[1.1.0]: https://github.com/kniko/claude-plugins/releases/tag/repo-mode-v1.1.0
[1.0.0]: https://github.com/kniko/claude-plugins/releases/tag/repo-mode-v1.0.0
