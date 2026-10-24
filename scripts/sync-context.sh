#!/bin/bash
# Pull the latest shared docs (CLAUDE.md, AGENTS.md, the PRD, builder-files/, the research doc, skills/) from the
# `context` branch into this folder. Files are unpacked, never staged: main's .gitignore ignores them, so they can't be
# committed by accident. context's skills/ lands in .claude/skills/, where Claude Code loads it. A doc you edited but haven't published is copied to .git/context-backup/ before it's
# replaced, so no edit is lost. Prints what changed since the last sync so the agent can tell the user before working.
set -euo pipefail
# Git Bash on Windows rewrites "rev:.claude/..." arguments as Windows paths unless this is set
export MSYS_NO_PATHCONV=1
cd "$(git rev-parse --show-toplevel)"
# .claude/ never leaves this machine, so context keeps the skills at skills/ and this maps them back
local_of() { case "$1" in skills/*) printf '.claude/%s\n' "$1" ;; *) printf '%s\n' "$1" ;; esac; }
if ! git fetch -q origin context 2>/dev/null; then
  echo "context: couldn't fetch the context branch (offline, or the doc owner hasn't created it yet); using local copies" >&2
  exit 1
fi
new=$(git rev-parse origin/context)
gitdir=$(git rev-parse --git-dir)
stamp="$gitdir/context-synced"
old=$(cat "$stamp" 2>/dev/null || echo none)
if [ "$new" = "$old" ]; then
  echo "context: up to date (${new:0:7})"
  exit 0
fi

if [ "$old" != none ] && git cat-file -e "$old^{commit}" 2>/dev/null; then
  incoming=$(git diff --name-only --diff-filter=d "$old" "$new")
else
  incoming=$(git ls-tree -r --name-only "$new")
fi
backup="$gitdir/context-backup/$(date +%Y%m%d-%H%M%S)"
saved=()
while IFS= read -r f; do
  [ -n "$f" ] || continue
  latest=$(git rev-parse "$new:$f")
  lf=$(local_of "$f")
  if [ -f "$lf" ]; then
    mine=$(git hash-object "$lf")
    [ "$mine" = "$latest" ] && continue
    base=$(git rev-parse -q --verify "$old:$f" 2>/dev/null || echo none)
    if [ "$mine" != "$base" ]; then
      mkdir -p "$backup/$(dirname "$lf")"
      cp "$lf" "$backup/$lf"
      saved+=("$lf")
    fi
  fi
  mkdir -p "$(dirname "$lf")"
  git cat-file blob "$latest" > "$lf"
done <<< "$incoming"
echo "$new" > "$stamp"

if [ "$old" = none ]; then
  echo "context: first sync at ${new:0:7}. Read CLAUDE.md in full, then the PRD's §0 NOW and your builder-files/builder-file-<name>.md."
else
  echo "context: UPDATED ${old:0:7} -> ${new:0:7}"
  git log --format='  %h %s (%an, %ar)' "$old..$new"
  git diff --stat "$old" "$new" | tail -n +1
  # Claude Code loads CLAUDE.md once at session start, so a mid-session rules change has to be read on purpose
  if grep -qx 'CLAUDE.md' <<< "$incoming"; then
    echo "context: CLAUDE.md changed. Re-read it in full before doing anything else."
  fi
fi
if [ ${#saved[@]} -gt 0 ]; then
  echo "context: you had unpublished edits, saved in $backup. Re-apply them, then publish:"
  printf '  %s\n' "${saved[@]}"
fi
