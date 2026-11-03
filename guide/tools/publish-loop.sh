#!/bin/sh
# While any Codex wave runs (a lock file exists or a chain waits for a usage limit), rebuild dist/ every 5 minutes so the
# engine's /docs shows the pages as they are written. Stops by itself when no wave has run for 15 minutes.
cd "$(dirname "$0")/.." || exit 1
idle=0
while [ $idle -lt 3 ]; do
  if ls _waves/runs/.lock-* >/dev/null 2>&1 || pgrep -f codex-chain.sh >/dev/null; then idle=0; else idle=$((idle + 1)); fi
  npm run build > _waves/runs/publish.log 2>&1 && date '+published %F %T' >> _waves/runs/publish.log
  sleep 300
done
