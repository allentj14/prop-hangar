#!/usr/bin/env bash
# Rebuild app data from a War Thunder datamine checkout.
# Usage: scripts/rebuild.sh <path-to-datamine> <game-version>
set -euo pipefail
WTDM="$1"
VER="${2:-unknown}"
S="$(cd "$(dirname "$0")" && pwd)"
T="$(mktemp -d)"
python3 -I "$S/extract.py" "$WTDM" "$T/planes.json"
python3 -I "$S/classify.py" "$T/planes.json" "$T/planes2.json" > /dev/null
python3 -I "$S/families.py" "$T/planes2.json" "$T/families.json" > /dev/null
python3 -I "$S/merge_comm.py" "$T/planes2.json" "$S/community.json" "$T/families.json" "$T/planes3.json"
python3 -I "$S/tags.py" "$T/planes3.json" > /dev/null
python3 -I "$S/lineups.py" "$T/planes3.json" "$T/lineups.json" > /dev/null
python3 -I "$S/build_data.py" "$T/planes3.json" "$T/lineups.json" data "$VER"
python3 -I "$S/build_xlsx.py" "$T/planes3.json" "$T/lineups.json" "data/War Thunder Prop Planes.xlsx"
echo "Rebuilt data for game version $VER"
