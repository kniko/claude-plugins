# managed by repo-mode
#
# PreToolUse hook for the PowerShell tool (PowerShell 5.1 and 7+). When Claude
# runs a plain test command (pytest, npm test, go test, ...), rewrite it so
# Claude sees only the failure context and the last lines, the real exit code
# is kept, and the full output is saved to a temp file Claude can read if it
# needs more. Short output (<= 60 lines) is shown in full. Every other command
# passes through unchanged.
#
# Two modes in one file:
#   - hook mode (no arguments): reads the hook JSON on stdin, prints the hook
#     JSON on stdout. Fails open: on any unexpected input it changes nothing.
#   - run mode (-RunCommand '<test command>'): runs the command, filters the
#     output. The hook rewrites the command into a call of this mode.
param([string]$RunCommand)

if ($RunCommand) {
    $f = Join-Path ([IO.Path]::GetTempPath()) ('repo-mode-test-' + [guid]::NewGuid().ToString('N') + '.txt')
    $global:LASTEXITCODE = 0
    $lines = @(Invoke-Expression ($RunCommand + ' 2>&1') | ForEach-Object { "$_" })
    $code = $global:LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    try { $lines | Set-Content -Path $f -Encoding UTF8 } catch { $f = '(could not save)' }

    $n = $lines.Count
    if ($n -le 60) {
        $lines
    } else {
        # Failure context: a matching line plus the 5 after it, at most 100 lines.
        $ctx = New-Object System.Collections.Generic.List[string]
        $k = 0
        foreach ($l in $lines) {
            if ($l -cmatch 'FAIL|ERROR|Error|error:|Traceback|panic:|AssertionError|panicked|Failed asserting') { $k = 6 }
            if ($k -gt 0) { if ($ctx.Count -lt 100) { $ctx.Add($l) }; $k-- }
        }
        if ($ctx.Count -gt 0) {
            "--- failure context ($($ctx.Count) lines) ---"
            $ctx
        }
        "--- last 20 of $n lines ---"
        $lines[($n - 20)..($n - 1)]
        "[repo-mode: full output saved to $f]"
    }
    exit $code
}

# ---- hook mode ----
try {
    $raw = [Console]::In.ReadToEnd()
    $inp = $raw | ConvertFrom-Json
    $cmd = [string]$inp.tool_input.command
} catch { '{}'; exit 0 }

$runners = '(npm test|npm run test|yarn test|pnpm test|npx jest|npx vitest|pytest|python -m pytest|python3 -m pytest|py -m pytest|uv run pytest|go test|cargo test|dotnet test|mvn test|mvn -q test|gradle test|\.\\gradlew test|\./gradlew test|make test|rspec|bundle exec rspec|phpunit|vendor/bin/phpunit)'
# Plain arguments only: no statement separators, pipes, redirections, variables,
# sub-expressions, script blocks, backticks, comments or control characters.
$pattern = '^' + $runners + '( [^;&|<>`$#(){}@\x00-\x1f]*)?$'

if (-not $cmd -or $cmd -cnotmatch $pattern) { '{}'; exit 0 }
if (-not $PSCommandPath) { '{}'; exit 0 }

try {
    $q = { param($s) "'" + ($s -replace "'", "''") + "'" }
    $inp.tool_input.command = "& " + (& $q $PSCommandPath) + " -RunCommand " + (& $q $cmd)
    @{ hookSpecificOutput = @{ hookEventName = 'PreToolUse'; updatedInput = $inp.tool_input } } |
        ConvertTo-Json -Depth 10 -Compress
} catch { '{}' }
exit 0
