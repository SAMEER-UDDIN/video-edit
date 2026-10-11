#!/usr/bin/env bash
# setup-aftereffects.sh: installs the After Effects MCP (pinned), its CEP panel, and wires .mcp.json.
# Safe to re-run. macOS + Windows (Git Bash). After it: restart After Effects, then Claude Code.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; cd "$ROOT"
REPO_URL="https://github.com/solomondivyananth/aftereffects-mcp.git"
PIN="2ed42650a435f7401bce25e69df6880894d68bcb"
VENDOR="$ROOT/vendor/aftereffects-mcp"
say(){ printf '%s\n' "$*"; }; fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
command -v git >/dev/null || fail "git is required"
command -v node >/dev/null || fail "Node.js 18+ is required"
[[ -d "$VENDOR/.git" ]] || { say "[ae] cloning aftereffects-mcp..."; git clone "$REPO_URL" "$VENDOR"; }
if [[ "$(git -C "$VENDOR" rev-parse HEAD)" != "$PIN" ]]; then
  git -C "$VENDOR" fetch --quiet origin
  git -C "$VENDOR" -c advice.detachedHead=false checkout --quiet -f "$PIN"
fi
say "[ae] engine pinned at ${PIN:0:7}"
case "$(uname -s)" in
  Darwin) (cd "$VENDOR" && ./install.sh) ;;
  MINGW*|MSYS*) (cd "$VENDOR" && node bin/install-panel.js --copy) ;;
  *) fail "After Effects runs on macOS/Windows only" ;;
esac
ENGINE="$VENDOR/mcp/ae-mcp.js"
case "$(uname -s)" in MINGW*|MSYS*) ENGINE="$(cygpath -m "$ENGINE")" ;; esac
node -e '
const fs=require("fs"); const [path,engine]=process.argv.slice(1);
let c={mcpServers:{}}; if(fs.existsSync(path)) c=JSON.parse(fs.readFileSync(path,"utf8"));
c.mcpServers=c.mcpServers||{}; c.mcpServers["after-effects"]={command:"node",args:[engine],env:{}};
fs.writeFileSync(path,JSON.stringify(c,null,2)+"\n"); console.log("[config] after-effects entry written to .mcp.json");
' "$ROOT/.mcp.json" "$ENGINE"
say ""
say "Next: 1) restart After Effects  2) Window > Extensions > AE MCP Bridge must say 'Listening on 127.0.0.1:7788'"
say "      3) in that panel set your project as Sandbox (writes only work on the Sandbox project)"
say "      4) restart Claude Code and answer YES to enabling this project's MCP servers."
