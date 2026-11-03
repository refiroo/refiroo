#!/bin/sh
# Runs waves in order, each with --wait-on-limit, then its check; logs to _waves/runs/chain-<WAVE>.log.
# Usage: sh guide/tools/codex-chain.sh WAVE [WAVE...]
cd "$(dirname "$0")/.." || exit 1
for w in "$@"; do
  echo "== $w $(date '+%F %T')" >> _waves/runs/chain-$w.log
  node tools/codex-wave.mjs run "$w" --wait-on-limit --timeout 180 >> _waves/runs/chain-$w.log 2>&1
  rc=$?
  node tools/codex-wave.mjs check "$w" >> _waves/runs/chain-$w.log 2>&1
  node tools/codex-wave.mjs status "$w" | tail -2 >> _waves/runs/chain-$w.log
  [ $rc -eq 0 ] || { echo "== $w stopped, run exit $rc" >> _waves/runs/chain-$w.log; exit $rc; }
done
