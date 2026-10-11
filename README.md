# video-edit — staged Fight Club editing in Premiere Pro + After Effects

Claude Code drives Premiere Pro and After Effects through MCP bridges to take a sequence you've already cut through three stages:

1. **Stage 1 — Headtracking** (nose-stabilised in AE, Motion Tile mirror, linked back onto the sequence)
2. **Stage 2 — Zooms & transitions** (one S_BlurMoCurves zoom per cut + BCC dark/flash transitions)
3. **Stage 3.1 — Captions** (WhisperX words → 3-4-word ALL-CAPS captions → Premiere caption track)

## Requirements
Premiere Pro 2025, After Effects 2022+, Node 18+, Git, ffmpeg, [uv](https://docs.astral.sh/uv/), [Claude Code](https://claude.com/claude-code).
Plugins used by the stages: Sapphire (S_BlurMoCurves), Boris Continuum (BCC Brightness-Contrast).

## Setup
```bash
git clone https://github.com/SAMEER-UDDIN/video-edit.git
cd video-edit
./setup.sh        # Windows: run in Git Bash
```
It clones the pinned Premiere and After Effects MCP engines into `vendor/`, installs both CEP panels, and writes `.mcp.json`.
Then restart Premiere + After Effects, restart Claude Code (answer **yes** to the MCP prompt), and confirm:
`node lanes/premiere/premiere-bridge.mjs ping`. In AE, Window ▸ Extensions ▸ AE MCP Bridge must show "Listening on 127.0.0.1:7788"; set your project as **Sandbox** there.

## Use
Open the folder in Claude Code, open your cut sequence in Premiere, and say e.g. *"stage 1, head track sequence 05"*, then *"stage 2"*, then *"stage 3.1"*.
Per-job files are created under `projects/<job>/` (git-ignored). Methods: `docs/fight-club/`. Look: `presets/youtube/fight-club/`.

## Your own Premiere presets
Put your caption text style and presets in `assets/premiere-presets/` (`newfinal.prtextstyle`, `fightcaps.prfpset`, `reverb.prfpset`); Stage 3.1 expects them there.

Third-party engines (not bundled, fetched by setup): [Adobe_Premiere_Pro_MCP](https://github.com/hetpatel-11/Adobe_Premiere_Pro_MCP), [aftereffects-mcp](https://github.com/solomondivyananth/aftereffects-mcp).
