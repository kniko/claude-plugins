#!/usr/bin/env bash
# managed by repo-mode
#
# PreToolUse hook for Bash. When Claude runs a plain test command (pytest,
# npm test, go test, ...), rewrite it so Claude sees only the failure context
# and the last lines, the real exit code is kept, and the full output is saved
# to a temp file Claude can read if it needs more. Short output (<= 60 lines)
# is shown in full. Every other command passes through unchanged.
#
# Based on the "filter test output" hook in the Claude Code docs
# (code.claude.com/docs/en/costs). Fails open: without jq, or on any
# unexpected input, it changes nothing.

command -v jq >/dev/null 2>&1 || { echo '{}'; exit 0; }

input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null) || { echo '{}'; exit 0; }

runners='(npm test|npm run test|yarn test|pnpm test|npx jest|npx vitest|pytest|python -m pytest|python3 -m pytest|uv run pytest|go test|cargo test|dotnet test|mvn test|mvn -q test|gradle test|\./gradlew test|make test|rspec|bundle exec rspec|phpunit|vendor/bin/phpunit)'
# Same safety rule as the docs example: plain arguments only, no shell operators.
pattern='^'"$runners"'( [^;&|<>`$#\\[:cntrl:]]*)?$'

if [[ ! "$cmd" =~ $pattern ]]; then
  echo '{}'
  exit 0
fi

awk_prog='{ if (NR<=60) a[NR]=$0; t[NR%20]=$0 }
/FAIL|ERROR|Error|error:|Traceback|panic:|AssertionError|panicked|Failed asserting/ { k=6 }
k>0 { if (c<100) m[++c]=$0; k-- }
END {
  if (NR<=60) { for (i=1;i<=NR;i++) print a[i]; exit }
  if (c>0) { print "--- failure context (" c " lines) ---"; for (i=1;i<=c;i++) print m[i] }
  print "--- last 20 of " NR " lines ---"
  for (i=NR-19;i<=NR;i++) print t[i%20]
  print "[repo-mode: full output saved to " f "]"
}'

wrapped="(set -o pipefail; f=\$(mktemp \"\${TMPDIR:-/tmp}/repo-mode-test.XXXXXX\"); $cmd 2>&1 | tee \"\$f\" | awk -v f=\"\$f\" '$awk_prog')"

printf '%s' "$input" | jq --arg c "$wrapped" \
  '{hookSpecificOutput: {hookEventName: "PreToolUse", updatedInput: (.tool_input + {command: $c})}}' 2>/dev/null || echo '{}'
