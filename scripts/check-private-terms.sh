#!/usr/bin/env bash
# Checks content about to be pushed against the terms in the local file .dev/private-terms.txt
# (one extended regular expression per line, lines starting with # are comments, matched
# case-insensitively as whole words). The file is not tracked; without it the check is skipped.
#
#   scripts/check-private-terms.sh                  the tracked text files of HEAD, and the message of every
#                                                   commit reachable from HEAD that is not on the remote
#   scripts/check-private-terms.sh --range A..B     the lines added by the commits of A..B, their messages,
#                                                   and the tracked text files at B
#   scripts/check-private-terms.sh --rev REV        as the first form, for REV instead of HEAD
#   scripts/check-private-terms.sh --worktree       the tracked text files as they are in the working tree
#
# Exits 1 and lists file:line (or the commit) of every hit; exits 0 when clean. PRIVATE_TERMS_FILE
# names another terms file. The pre-push hook (.git/hooks/pre-push, local) runs it for the pushed range.
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
terms_file="${PRIVATE_TERMS_FILE:-$root/.dev/private-terms.txt}"
if [ ! -f "$terms_file" ]; then
  echo "check-private-terms: $terms_file not found; skipping the check." >&2
  exit 0
fi
pattern="$(grep -v -e '^[[:space:]]*#' -e '^[[:space:]]*$' "$terms_file" | paste -sd'|' -)"
if [ -z "$pattern" ]; then
  echo "check-private-terms: $terms_file holds no terms; skipping the check." >&2
  exit 0
fi
cd "$root"

mode=head
rev=HEAD
range=
case "${1:-}" in
  "") ;;
  --range) mode=range; range="${2:?--range needs A..B}" ;;
  --rev) rev="${2:?--rev needs a revision}" ;;
  --worktree) mode=worktree ;;
  *) echo "usage: $0 [--range A..B | --rev REV | --worktree]" >&2; exit 2 ;;
esac

found=0
limit=200

scan_tree() { # a revision, or nothing for the working tree
  local out
  if [ -n "${1:-}" ]; then
    out="$(git grep -I -i -n -w -E "($pattern)" "$1" -- 2>/dev/null | sed "s/^$1://" || true)"
  else
    out="$(git grep -I -i -n -w -E "($pattern)" -- 2>/dev/null || true)"
  fi
  if [ -n "$out" ]; then
    echo "Files with a hit (file:line):" >&2
    printf '%s\n' "$out" | cut -c1-200 | head -n "$limit" | sed 's/^/  /' >&2
    found=1
  fi
}

scan_messages() { # arguments of git rev-list
  local sha
  for sha in $(git rev-list "$@"); do
    if git log -1 --format=%B "$sha" | grep -q -i -w -E "($pattern)"; then
      echo "Commit message with a hit: $sha" >&2
      found=1
    fi
  done
}

scan_added() { # a git rev-list range
  local out
  out="$(git log -p -U0 --no-color --format='@@commit %H' "$1" | awk '
    /^@@commit / { commit = substr($2, 1, 12); next }
    /^\+\+\+ / { file = substr($0, 7); next }
    /^--- / { next }
    /^@@ / { split($3, a, ","); line = substr(a[1], 2) + 0; next }
    /^\+/ { print commit " " file ":" line ":" substr($0, 2); line++ }
  ' | grep -i -w -E "($pattern)" | cut -c1-200 || true)"
  if [ -n "$out" ]; then
    echo "Added lines with a hit (commit file:line):" >&2
    printf '%s\n' "$out" | head -n "$limit" | sed 's/^/  /' >&2
    found=1
  fi
}

remote_base() {
  git rev-parse --verify -q '@{push}' 2>/dev/null \
    || git rev-parse --verify -q origin/main 2>/dev/null \
    || true
}

case "$mode" in
  worktree)
    scan_tree
    ;;
  range)
    to="${range#*..}"
    from="${range%%..*}"
    if [ -z "$from" ] || [ "$(printf '%s' "$from" | tr -d 0)" = "" ]; then
      scan_messages "$to"
    else
      scan_messages "$range"
      scan_added "$range"
    fi
    scan_tree "$to"
    ;;
  head)
    base="$(remote_base)"
    if [ -n "$base" ] && git merge-base --is-ancestor "$base" "$rev" 2>/dev/null; then
      scan_messages "$base..$rev"
    else
      scan_messages "$rev"
    fi
    scan_tree "$rev"
    ;;
esac

if [ "$found" -ne 0 ]; then
  echo "check-private-terms: hits found (terms from $terms_file). Nothing is pushed until they are removed." >&2
  exit 1
fi
echo "check-private-terms: clean."
