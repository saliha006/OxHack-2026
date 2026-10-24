#!/bin/bash
# Runs before every prompt (the UserPromptSubmit hook in .claude/settings.json); Claude Code shows its output to the
# agent. That makes the context sync and the progress.md check happen even after a long session has pushed the
# CLAUDE.md rule out of the agent's attention. Codex users run it by hand (AGENTS.md).
# Never blocks a prompt: every failure prints one line, and the script always exits 0.
export MSYS_NO_PATHCONV=1

# --guard runs as a Read hook (PreToolUse): one oversized read is re-sent with every later request, so it is refused
# before it lands in the context. Exit 2 shows the message to the agent instead of running the read.
if [ "${1:-}" = "--guard" ]; then
  input=$(cat)
  path=$(printf '%s' "$input" | sed -n 's/.*"file_path" *: *"\([^"]*\)".*/\1/p' | sed 's#\\\{1,2\}#/#g')
  has() { grep -q "\"$1\"" <<< "$input"; }
  deny() { echo "read-guard: $1" >&2; exit 2; }
  case "$path" in
    *.jsonl) deny "session transcripts are huge; Grep them for a keyword instead." ;;
    */CLAUDE.md|CLAUDE.md) has limit || deny "CLAUDE.md is already in your context; Grep it or Read with limit." ;;
    *.pdf) has pages && exit 0; deny "give a pages range (max 3); slide PDFs are images and cost thousands of tokens per page." ;;
    *.png|*.jpg|*.jpeg|*.gif|*.webp) exit 0 ;;
  esac
  if ! has limit && [ -f "$path" ]; then
    size=$(wc -c < "$path" 2>/dev/null || echo 0)
    [ "$size" -le 40000 ] || deny "$((size / 1000))KB (~$((size / 4000))k tokens) re-sent on every later request. Grep it, or Read with offset and limit."
  fi
  exit 0
fi

# --install-guard adds that hook to this clone's .claude/settings.json (the file never leaves the machine).
if [ "${1:-}" = "--install-guard" ]; then
  cd "$(git rev-parse --show-toplevel)" || exit 1
  py=$(command -v python3 || command -v python || command -v py) || { echo "no python found: add a PreToolUse hook with matcher Read running 'bash scripts/prompt-check.sh --guard' to .claude/settings.json by hand"; exit 1; }
  mkdir -p .claude
  "$py" - <<'PY'
import json, os
p = ".claude/settings.json"
d = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
hooks = d.setdefault("hooks", {})
cmd = 'bash "${CLAUDE_PROJECT_DIR:-.}/scripts/prompt-check.sh" --guard'
if any(cmd in h.get("command", "") for e in hooks.get("PreToolUse", []) for h in e.get("hooks", [])):
    print("read-guard already installed")
else:
    hooks.setdefault("PreToolUse", []).append({"matcher": "Read", "hooks": [{"type": "command", "command": cmd, "timeout": 10}]})
    json.dump(d, open(p, "w", encoding="utf-8"), indent=2)
    print("read-guard installed in .claude/settings.json (restart the session to activate)")
PY
  exit 0
fi

cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || exit 0

[ -f scripts/sync-context.sh ] && { bash scripts/sync-context.sh 2>&1; }

main=$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
main=${main:-main}
if ! git fetch -q origin "$main" 2>/dev/null; then
  echo "progress: couldn't fetch origin/$main; read the local progress.md and say the check was local-only"
  exit 0
fi
if ! git cat-file -e "origin/$main:progress.md" 2>/dev/null; then
  echo "progress: no progress.md on $main yet (CLAUDE.md 🧰 setup)"
  exit 0
fi

builder=$(git config --get team.builder || true)
if [ -n "$builder" ]; then
  # rows of the Open board table whose To column names this builder or @all; {{…}} rows are the unfilled template
  mine=$(git show "origin/$main:progress.md" \
    | awk '/^## 📌 Open board/{on=1; next} on && /^## /{exit} on && /^\|/' \
    | awk -F'|' -v me="@$(printf '%s' "$builder" | tr '[:upper:]' '[:lower:]')" \
        'NR > 2 && $0 !~ /\{\{/ && (index(tolower($4), me) || index(tolower($4), "@all"))')
  if [ -n "$mine" ]; then
    echo "progress: Open board rows To @$builder. Tell the user these first (CLAUDE.md §2b):"
    printf '%s\n' "$mine"
  else
    echo "progress: nothing on the Open board for @$builder"
  fi
else
  echo "progress: run 'git config team.builder <your-name>' so your Open board rows can be found"
fi

head=$(git rev-parse "origin/$main")
seen=$(git config --get team.progressseen || true)
if [ -n "$seen" ] && git cat-file -e "$seen^{commit}" 2>/dev/null; then
  # by push, not by stamp: an entry stamped earlier but pushed later still shows up here
  new=$(git diff "$seen" "$head" -- progress.md | sed -n 's/^+\([^+|].*\)$/\1/p')
  if [ -n "$new" ]; then
    echo "progress: new lines since your last prompt (all of them; don't read the whole file); check Touched lines against your own area:"
    printf '%s\n' "$new"
  fi
else
  echo "progress: first check in this clone. Read the Open board and the newest entries in progress.md"
fi
git config team.progressseen "$head"
grep -qs -e '--guard' .claude/settings.json || echo "token-guard: Read hook not installed. Run once: bash scripts/prompt-check.sh --install-guard"
exit 0
