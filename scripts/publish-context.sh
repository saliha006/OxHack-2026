#!/bin/bash
# Publish your edited shared docs to the `context` branch without switching branches.
# Usage: scripts/publish-context.sh "what changed, in plain words" [brand-new-doc ...]
# Only files you changed since your last sync are sent. Everything else keeps the version already on `context`,
# so a stale local copy can never undo a teammate's edit. Refuses: a file changed on `context` AND locally,
# anything that looks like a credential, and, unless you're the doc owner, anything but your own brief and the
# research doc. Who you are comes from `git config team.builder <name>` (once per clone). The doc owner and the
# research doc are read from the CLAUDE.md Registry, so nothing in here is tied to one project.
# The very first run, before origin has a `context` branch, creates it from the shared docs on disk.
set -euo pipefail
# Git Bash on Windows rewrites "rev:.claude/..." arguments as Windows paths unless this is set
export MSYS_NO_PATHCONV=1
cd "$(git rev-parse --show-toplevel)"
msg=${1:?usage: scripts/publish-context.sh "what changed" [brand-new-doc ...]}
shift
gitdir=$(git rev-parse --git-dir)

builder=$(git config --get team.builder || true)
if [ -z "$builder" ]; then
  echo "publish refused: say who you are first: git config team.builder <your-name>" >&2
  exit 1
fi
builder=$(printf '%s' "$builder" | tr '[:upper:]' '[:lower:]')
# an unfilled {{…}} slot yields an empty value, which means "no owner set yet"
owner=$(sed -n 's/^| Doc owner | *\**\([A-Za-z0-9_.-]*\).*/\1/p' CLAUDE.md 2>/dev/null | head -n1 | tr '[:upper:]' '[:lower:]')
research=$(sed -n 's/^| Research doc | *`\([^`{]*\)`.*/\1/p' CLAUDE.md 2>/dev/null | head -n1)

# Candidates are context paths. .claude/ never leaves this machine, so the local .claude/skills/ is published as skills/
local_of() { case "$1" in skills/*) printf '.claude/%s\n' "$1" ;; *) printf '%s\n' "$1" ;; esac; }
list_candidates() {
  { git ls-tree -r --name-only origin/context 2>/dev/null
    ls CLAUDE.md AGENTS.md ./*-PRD.md builder-files/builder-file-*.md ./*-CONTEXT.md 2>/dev/null | sed 's#^\./##'
    [ -n "$research" ] && printf '%s\n' "$research"
    find .claude/skills -type f -not -path '*/__pycache__/*' 2>/dev/null | sed 's#^\.claude/##'
    [ $# -gt 0 ] && printf '%s\n' "$@"; } | grep -v -x -e progress.md -e README.md | grep -v '^\.claude/' | sort -u || true
}
may_publish() {
  [ -z "$owner" ] || [ "$builder" = "$owner" ] || [ "$1" = "builder-files/builder-file-$builder.md" ] || [ "$1" = "$research" ]
}
# matches the shape of a secret, never a fragment of a real one: this script is public
looks_secret() {
  grep -l -i -E 'BEGIN [A-Z ]*PRIVATE KEY|drive\.google\.com/(file|drive)/|gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|(password|passphrase|passwd) *[:=] *[^ ]{8,}' "$@" 2>/dev/null
}
[ -n "$owner" ] || echo "context: no doc owner in the CLAUDE.md Registry yet, so anyone may publish anything" >&2

if ! git fetch -q origin context 2>/dev/null; then
  if git ls-remote --exit-code --heads origin context >/dev/null 2>&1; then
    echo "publish refused: couldn't fetch the context branch" >&2
    exit 1
  fi
  [ -z "$owner" ] || [ "$builder" = "$owner" ] || { echo "publish refused: only the doc owner (@$owner) creates the context branch" >&2; exit 1; }
  docs=()
  while IFS= read -r f; do [ -f "$(local_of "$f")" ] && docs+=("$f"); done <<< "$(list_candidates "$@")"
  [ ${#docs[@]} -gt 0 ] || { echo "publish refused: no shared docs on disk to start the context branch with" >&2; exit 1; }
  mapfile -t paths < <(for f in "${docs[@]}"; do local_of "$f"; done)
  if looks_secret "${paths[@]}"; then echo "publish refused: a file above looks like it contains a credential" >&2; exit 1; fi
  export GIT_INDEX_FILE="$gitdir/context-index"
  rm -f "$GIT_INDEX_FILE"
  for f in "${docs[@]}"; do git update-index --add --cacheinfo "100644,$(git hash-object -w "$(local_of "$f")"),$f"; done
  commit=$(git commit-tree "$(git write-tree)" -m "$msg")
  rm -f "$GIT_INDEX_FILE"
  unset GIT_INDEX_FILE
  git push -q origin "$commit:refs/heads/context"
  git fetch -q origin context
  echo "$commit" > "$gitdir/context-synced"
  echo "context: created the context branch at ${commit:0:7} with ${#docs[@]} files"
  exit 0
fi

synced=$(cat "$gitdir/context-synced" 2>/dev/null || true)
if [ -z "$synced" ]; then
  echo "publish refused: run scripts/sync-context.sh first" >&2
  exit 1
fi
parent=$(git rev-parse origin/context)

blob() { git rev-parse -q --verify "$1:$2" 2>/dev/null || echo none; }
changed=()
conflicts=()
while IFS= read -r f; do
  lf=$(local_of "$f")
  [ -f "$lf" ] || continue
  mine=$(git hash-object "$lf"); base=$(blob "$synced" "$f"); remote=$(blob "$parent" "$f")
  if [ "$mine" = "$base" ] || [ "$mine" = "$remote" ]; then continue; fi
  if [ "$remote" != "$base" ]; then conflicts+=("$f"); else changed+=("$f"); fi
done <<< "$(list_candidates "$@")"

if [ ${#conflicts[@]} -gt 0 ]; then
  printf 'publish refused: changed on context since your last sync AND locally:\n' >&2
  printf '  %s\n' "${conflicts[@]}" >&2
  echo "run scripts/sync-context.sh (it saves your copy under .git/context-backup/), re-apply your edit, re-run" >&2
  exit 1
fi
if [ ${#changed[@]} -eq 0 ]; then
  echo "context: nothing to publish"
  exit 0
fi
for f in "${changed[@]}"; do
  if ! may_publish "$f"; then
    echo "publish refused: only the doc owner (@$owner) publishes $f. Post it to them as a row on the progress.md Open board, or undo your local edit" >&2
    exit 1
  fi
done
mapfile -t paths < <(for f in "${changed[@]}"; do local_of "$f"; done)
if looks_secret "${paths[@]}"; then
  echo "publish refused: a file above looks like it contains a credential" >&2
  exit 1
fi

export GIT_INDEX_FILE="$gitdir/context-index"
rm -f "$GIT_INDEX_FILE"
git read-tree "$parent"
for f in "${changed[@]}"; do
  git update-index --add --cacheinfo "100644,$(git hash-object -w "$(local_of "$f")"),$f"
done
tree=$(git write-tree)
rm -f "$GIT_INDEX_FILE"
unset GIT_INDEX_FILE
commit=$(git commit-tree "$tree" -p "$parent" -m "$msg")
git push -q origin "$commit:refs/heads/context"

# teammates' newer copies replace yours, so the stamp below matches the disk and the next publish sees only real edits
while IFS= read -r f; do
  latest=$(git rev-parse "$commit:$f")
  lf=$(local_of "$f")
  if [ ! -f "$lf" ] || [ "$(git hash-object "$lf")" != "$latest" ]; then
    mkdir -p "$(dirname "$lf")"
    git cat-file blob "$latest" > "$lf"
  fi
done < <(git diff --name-only --diff-filter=d "$synced" "$commit")
echo "$commit" > "$gitdir/context-synced"
echo "context: published ${commit:0:7} ($msg): ${changed[*]}"
