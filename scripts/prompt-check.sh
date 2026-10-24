#!/bin/bash
# Runs before every prompt (the UserPromptSubmit hook in .claude/settings.json); Claude Code shows its output to the
# agent. That makes the context sync and the progress.md check happen even after a long session has pushed the
# CLAUDE.md rule out of the agent's attention. Codex users run it by hand (AGENTS.md).
# Never blocks a prompt: every failure prints one line, and the script always exits 0.
export MSYS_NO_PATHCONV=1
cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || exit 0

[ -f scripts/sync-context.sh ] && { bash scripts/sync-context.sh 2>&1 | head -n 40; }

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
  new=$(git diff "$seen" "$head" -- progress.md | sed -n 's/^+### /### /p')
  if [ -n "$new" ]; then
    echo "progress: new entries since your last prompt. Read them; check their Touched lines against your own area:"
    printf '%s\n' "$new"
  fi
else
  echo "progress: first check in this clone. Read the Open board and the newest entries in progress.md"
fi
git config team.progressseen "$head"
exit 0
