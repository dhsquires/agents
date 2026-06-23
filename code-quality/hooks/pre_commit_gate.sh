#!/usr/bin/env bash
# Claude Code PreToolUse hook: run the code-quality gate on staged files before
# a `git commit` Bash command is executed. Blocks the commit (exit 2) only when
# there are error-level violations. Anything that is not a git commit passes
# straight through.
#
# Disable per-repo by setting gate.fail_on = "never" in code-quality.toml, or
# uninstall the hook.

set -euo pipefail

input="$(cat)"

# Extract the command being run from the hook payload.
command="$(printf '%s' "$input" | python3 -c \
  'import sys,json
try:
    print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except Exception:
    print("")' 2>/dev/null || true)"

# Only gate real commits. Skip --no-verify, --amend metadata-only is still fine.
case "$command" in
  *"git commit"*) : ;;
  *) exit 0 ;;
esac
case "$command" in
  *"--no-verify"*) exit 0 ;;
esac

root="${CLAUDE_PLUGIN_ROOT:-"$(cd "$(dirname "$0")/.." && pwd)"}"
engine="$root/scripts/code-quality.py"
[ -f "$engine" ] || exit 0

if output="$(python3 "$engine" analyze --staged --gate --format text --no-color 2>&1)"; then
  exit 0
fi

{
  echo "❌ code-quality gate failed on staged files — commit blocked."
  echo
  echo "$output"
  echo
  echo "Resolve the error-level findings, or bypass with 'git commit --no-verify',"
  echo "or set gate.fail_on = \"never\" in code-quality.toml."
} >&2
exit 2
