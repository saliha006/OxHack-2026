#!/bin/bash
# Runs sync-context.sh, publish-context.sh and prompt-check.sh against a throwaway remote: the doc owner creates the
# context branch, a stale copy never undoes a teammate's edit, builders publish only their own brief and the research
# doc, sync never loses an unpublished edit, and the prompt hook shows each builder only their own Open board rows.
# Usage: bash scripts/test-context-scripts.sh
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }
quiet() { "$@" >/dev/null 2>&1; }
# MSYS_NO_PATHCONV only around `git show`: elsewhere Git Bash must still translate the /tmp paths for Windows git
on_context() { (cd "$tmp/$1" && git fetch -q origin context && MSYS_NO_PATHCONV=1 git show "origin/context:$2"); }
clone_as() {
  git clone -q -b main "$tmp/remote.git" "$tmp/$1" 2>/dev/null
  git -C "$tmp/$1" config user.email "$1@test"
  git -C "$tmp/$1" config user.name "$1"
  git -C "$tmp/$1" config team.builder "$1"
}

git init -q --bare --initial-branch=main "$tmp/remote.git"
git init -q --initial-branch=main "$tmp/seed"
cd "$tmp/seed"
git config user.email seed@test
git config user.name seed
mkdir scripts
cp "$here/sync-context.sh" "$here/publish-context.sh" "$here/prompt-check.sh" scripts/
printf '* text=auto eol=lf\n' > .gitattributes
printf '*.md\n!progress.md\n.claude/\n' > .gitignore
cat > progress.md <<'EOF'
# Demo: progress log and conflict board

## 📌 Open board (read on every prompt)
| Since | From | To | Kind | What, and what to do | Entry |
|---|---|---|---|---|---|
| 2026-01-01 10:00 | @alex | @sam | ⚠️ conflict | login API changed; update the form | 2026-01-01 10:00 |
| 2026-01-01 10:05 | @sam | @kim | 📨 waiting on | the schema | 2026-01-01 10:05 |
| 2026-01-01 10:06 | @alex | @all | ❓ question | freeze time? | 2026-01-01 10:06 |
| {{YYYY-MM-DD HH:MM}} | @{{name}} | @sam | {{kind}} | template row | x |

## 👥 Team

## Log (newest first)

### 2026-01-01 10:00 — feat — login API — @alex
EOF
git add .
git commit -qm main
git remote add origin "$tmp/remote.git"
git push -q origin main

# the doc owner writes the shared docs and creates the context branch with the first publish
clone_as alex
cd "$tmp/alex"
mkdir -p docs builder-files .claude/skills/demo/__pycache__
echo "bytecode" > .claude/skills/demo/__pycache__/x.pyc
cat > CLAUDE.md <<'EOF'
| Doc owner | **Alex** (doc owner) |
| Research doc | `docs/research.md` (on `context`) |
EOF
for f in AGENTS.md demo-PRD.md builder-files/builder-file-alex.md builder-files/builder-file-sam.md \
         builder-files/builder-file-kim.md docs/research.md .claude/skills/demo/SKILL.md; do
  echo "$f v1" > "$f"
done
quiet bash scripts/publish-context.sh "start" || fail "the doc owner could not create the context branch"
on_context alex docs/research.md | grep -q v1 || fail "the research doc didn't reach the new context branch"
on_context alex skills/demo/SKILL.md | grep -q v1 || fail "skills didn't reach the new context branch as skills/"
(cd "$tmp/alex" && git ls-tree -r --name-only origin/context) | grep -q -e '^\.claude/' -e __pycache__ \
  && fail ".claude/ or __pycache__ reached the context branch"
on_context alex progress.md >/dev/null 2>&1 && fail "progress.md was published to context"

for who in sam kim; do
  clone_as "$who"
  (cd "$tmp/$who" && quiet bash scripts/sync-context.sh)
  [ -f "$tmp/$who/CLAUDE.md" ] || fail "$who's first sync didn't unpack CLAUDE.md"
  [ -f "$tmp/$who/.claude/skills/demo/SKILL.md" ] || fail "$who's first sync didn't unpack skills into .claude/skills/"
  [ -e "$tmp/$who/skills" ] && fail "$who's sync left a stray skills/ folder"
done

# a skill edited in .claude/skills/ goes up as skills/ and lands in a teammate's .claude/skills/
cd "$tmp/alex"
echo "skill v2" >> .claude/skills/demo/SKILL.md
quiet bash scripts/publish-context.sh "skill v2" || fail "the doc owner could not publish a skill edit"
(cd "$tmp/kim" && quiet bash scripts/sync-context.sh)
grep -q "skill v2" "$tmp/kim/.claude/skills/demo/SKILL.md" || fail "a skill edit didn't reach kim's .claude/skills/"

# a builder whose sync is older than a teammate's publish must not undo that teammate's edit
cd "$tmp/sam"
echo "sam: task 3 done" >> builder-files/builder-file-sam.md
quiet bash scripts/publish-context.sh "sam done" || fail "sam could not publish his own brief"
cd "$tmp/kim"
echo "kim: task 6 done" >> builder-files/builder-file-kim.md
quiet bash scripts/publish-context.sh "kim done" || fail "kim could not publish her own brief"
on_context kim builder-files/builder-file-sam.md | grep -q "task 3 done" || fail "kim's stale copy undid sam's edit"
grep -q "task 3 done" "$tmp/kim/builder-files/builder-file-sam.md" || fail "publish left kim's stale copy in place"

# builders may publish the research doc, but not someone else's brief, the PRD or CLAUDE.md
cd "$tmp/kim"
echo "kim: new research section" >> docs/research.md
quiet bash scripts/publish-context.sh "kim research" || fail "kim could not publish the research doc"
for f in builder-files/builder-file-sam.md demo-PRD.md CLAUDE.md; do
  quiet bash scripts/sync-context.sh
  echo "kim edits $f" >> "$f"
  quiet bash scripts/publish-context.sh "x" && fail "kim published $f"
  on_context kim "$f" > "$f"
done

# the doc owner publishes several docs at once, plus a brand-new doc named on the command line
cd "$tmp/alex"
quiet bash scripts/sync-context.sh
echo "alex tidies" >> builder-files/builder-file-sam.md
echo "alex tidies" >> demo-PRD.md
mkdir -p extra && echo "glossary v1" > extra/glossary.md
quiet bash scripts/publish-context.sh "alex tidies" extra/glossary.md || fail "the doc owner could not publish several docs"
on_context alex extra/glossary.md | grep -q v1 || fail "a doc named on the command line wasn't published"

# a rules change is called out on the next sync, because the agent loaded CLAUDE.md before it changed
echo "| Run · Test | x |" >> CLAUDE.md
quiet bash scripts/publish-context.sh "rules"
sync_out=$(cd "$tmp/kim" && bash scripts/sync-context.sh)
grep -q "CLAUDE.md changed" <<< "$sync_out" || fail "sync didn't flag the CLAUDE.md change"
grep -q '^+| Run · Test | x |' <<< "$sync_out" || fail "sync didn't show the changed CLAUDE.md lines"
grep -q "in full" <<< "$sync_out" && fail "sync told the agent to re-read a whole file"

# credentials and an unknown builder are refused
# built at runtime so this script itself never matches the secret scan and can still be published
printf 'pass%s: %s\n' word hunter2hunter2 >> demo-PRD.md
quiet bash scripts/publish-context.sh "oops" && fail "a credential was published"
on_context alex demo-PRD.md > demo-PRD.md
cd "$tmp/kim"
git config --unset team.builder
echo "x" >> builder-files/builder-file-kim.md
quiet bash scripts/publish-context.sh "x" && fail "publish ran without team.builder"
git config team.builder kim
on_context kim builder-files/builder-file-kim.md > builder-files/builder-file-kim.md

# sam's last sync predates alex's tidy of his brief: publish is refused, and sync keeps his edit as a backup
cd "$tmp/sam"
echo "sam: unpublished note" >> builder-files/builder-file-sam.md
quiet bash scripts/publish-context.sh "conflict" && fail "publish ignored a change made on both sides"
quiet bash scripts/sync-context.sh
grep -rq "unpublished note" .git/context-backup || fail "sync lost sam's unpublished edit"
grep -q "alex tidies" builder-files/builder-file-sam.md || fail "sync didn't bring in alex's tidy"

# the prompt hook: sam sees his row and the @all row, never kim's or the template row; new entries show once
out=$(bash scripts/prompt-check.sh)
grep -q "login API changed" <<< "$out" || fail "prompt-check missed sam's Open board row"
grep -q "freeze time" <<< "$out" || fail "prompt-check missed the @all row"
grep -q "the schema" <<< "$out" && fail "prompt-check showed sam a row addressed to kim"
grep -q "template row" <<< "$out" && fail "prompt-check showed the unfilled template row"
cd "$tmp/alex"
git pull -q origin main
sed -i 's/^## Log (newest first)$/## Log (newest first)\n\n### 2026-01-01 11:00 — fix — schema index — @alex/' progress.md
git commit -qam "Log the schema fix"
git push -q origin main
cd "$tmp/sam"
out=$(bash scripts/prompt-check.sh)
grep -q "schema index" <<< "$out" || fail "prompt-check missed a new progress entry"
out=$(bash scripts/prompt-check.sh)
grep -q "schema index" <<< "$out" && fail "prompt-check showed the same entry twice"

# offline, the hook still exits 0 so it never blocks a prompt
git remote set-url origin "$tmp/missing.git"
bash scripts/prompt-check.sh >/dev/null 2>&1 || fail "prompt-check failed when the remote was unreachable"

echo "PASS: context scripts"
