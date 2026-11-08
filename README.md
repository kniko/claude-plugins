# kniko-tools

A Claude Code plugin marketplace.

## Install

```bash
claude plugin marketplace add kniko/claude-plugins
claude plugin install repo-mode@kniko-tools
claude plugin install bricscad@kniko-tools
```

## Plugins

| Plugin | Description |
|---|---|
| [repo-mode](plugins/repo-mode/) | Per-repo model/advisor/subagent setup wizard: `/repo-mode:setup`, `/repo-mode:status`, `/repo-mode:off`. Writes nothing until you approve the plan. |
| [bricscad](plugins/bricscad/) | Drive a running BricsCAD (Windows) from Claude: MCP server + skill for plans, sections, elevations, measured dimensions, Greek text and 3D solids. Needs `uv`. |

## License

MIT
