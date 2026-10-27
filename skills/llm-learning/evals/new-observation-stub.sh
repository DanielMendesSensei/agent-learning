#!/usr/bin/env bash
# stub of the real helper: mints the next id and prints the path to write into
set -euo pipefail
d="$(cd "$(dirname "$0")" && pwd)/observation-log"
slug="${1:?usage: new-observation.sh <slug>}"
n=$(find "$d" -maxdepth 1 -name '*.md' | wc -l); n=$((n+1))
p=$(printf '%s/%04d-%s.md' "$d" "$n" "$slug"); : > "$p"; echo "$p"
