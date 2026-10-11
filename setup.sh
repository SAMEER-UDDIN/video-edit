#!/usr/bin/env bash
# One-command setup: checks tools, installs the Premiere + After Effects MCP bridges, wires .mcp.json.
set -euo pipefail
cd "$(cd "$(dirname "$0")" && pwd)"
miss=0
for t in git node ffmpeg uv; do command -v $t >/dev/null || { echo "MISSING: $t"; miss=1; }; done
if [[ $miss -eq 1 ]]; then
  echo "Install the missing tools first. Windows (PowerShell): winget install Git.Git OpenJS.NodeJS.LTS Gyan.FFmpeg astral-sh.uv"
  echo "macOS: brew install git node ffmpeg uv"; exit 1
fi
bash ./setup-premiere.sh
bash ./setup-aftereffects.sh
echo; echo "Done. Restart Premiere + After Effects, then restart Claude Code (answer YES to the MCP prompt)."
echo "Check:  node lanes/premiere/premiere-bridge.mjs ping"
