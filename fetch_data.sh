#!/bin/bash
# Requires FOOTBALL_DATA_API_TOKEN env var set (free key from football-data.org)
set -e

fetch() {
  # $1 = output file, rest = curl args (URL, headers, etc.)
  local out="$1"; shift
  curl -s "$@" -o "$out"
  if grep -q '"errorCode"' "$out" 2>/dev/null; then
    echo "ERROR: fetch failed for $out — $(cat "$out")" >&2
    exit 1
  fi
  sleep 7
}

fetch standings.json -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/CL/standings"
fetch matches.json -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/CL/matches"
fetch scorers.json -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/CL/scorers?limit=50"
python3 build_site.py
echo "Rebuilt site/index.html"
