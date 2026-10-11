#!/usr/bin/env bash
# typecheck + lint + format-check + tests, one ✅/❌ line each (with the last line of the error).
# Uses the tools pinned in mise.toml: `mise x -- bash validate.sh` (lefthook runs it before every push).
cd "$(dirname "$0")" || exit 1
[ -x .venv/bin/python ] || python -m venv .venv
if ! .venv/bin/pip install -q -r requirements.txt >/dev/null 2>&1; then echo "❌ deps (.venv)"; exit 1; fi

fail=0
check() {
  local name=$1 out
  shift
  if out=$("$@" 2>&1); then echo "✅ $name"; else echo "❌ $name — $(printf '%s\n' "$out" | tail -1 | cut -c1-140)"; fail=1; fi
}
check typecheck mypy --check-untyped-defs --ignore-missing-imports ./*.py
check lint sh -c 'ruff check -q --output-format concise . && shellcheck -f gcc ./*.sh'
check format-check ruff format --check .
check tests .venv/bin/python test_bot.py
exit $fail
