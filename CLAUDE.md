# CLAUDE.md — Fight Club staged editing (Premiere Pro + After Effects)

Claude is the editor. This repo runs three prompt-driven stages on a Premiere sequence you have already cut.
Never touch the user's cut; every stage adds layers on top.

| Stage | Say | Skill |
|---|---|---|
| 1 Headtracking | "stage 1 / head track sequence NN" | `.claude/skills/stage-1-headtracking` |
| 2 Zooms + transitions | "stage 2" | `.claude/skills/stage-2-zooms-transitions` |
| 3.1 Captions | "stage 3.1 / make captions" | `.claude/skills/stage-3-1-creating-captions` |

First run: if `.mcp.json` is missing, run `./setup.sh` (see README). Methods and house style: `docs/fight-club/`.
Channel preset: `presets/youtube/fight-club/`. Per-job files go in `projects/<job>/` (git-ignored).
After Effects writes only work on the project set as **Sandbox** in the AE MCP Bridge panel.
At the start of every editing session, if `C:\CLAUDE\Fight Club\` exists on this PC, read its `README.md` first, then `shorts-catalog.md`, `sequences/` and `setup-log.md` as needed; never edit or delete those files (append only to `setup-log.md`). `docs/fight-club/` is newer for the methods.
