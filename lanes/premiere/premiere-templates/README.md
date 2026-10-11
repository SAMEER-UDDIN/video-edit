# Premiere lane templates

Tracked assets the Premiere lane's scripts consume. Nothing here is a look — the apply mechanics
live in [`../premiere-grading.md`](../premiere-grading.md), the numbers in the preset.

## `adjustment-layer.prproj` — the adjustment-layer donor

**Why it exists:** Premiere's scripting surface has no way to CONSTRUCT an adjustment layer. The
only route is `app.project.importSequences(<this file>, [<its sequence uuid>])`, which lands a
working online "Adjustment Layer" item at project root (plus a junk `adj-template` sequence to
delete). The donor is a fixed **3840×2160**.

`mint-adjustment-layer.py <W>x<H>` patches a copy of it to the sequence's own frame size and prints
the template path + the uuid to import. Those `adjustment-layer-<W>x<H>.prproj` children are
**gitignored and regenerable** (a size mints byte-identically every time, so re-importing is
idempotent); only the donor is tracked.

**Re-cutting the donor**, if Premiere's `.prproj` format ever changes: place a UI-born adjustment
layer on a scratch sequence and call `sequence.exportAsProject(path)` via ExtendScript (the ES
method works; the MCP tool of the same name is a stub). Only the very first donor ever needed the
UI. The tracked file is path-sanitized to `/Users/creator` — sanitize any re-cut the same way before
committing, and remember `packaging/package-for-client.sh`'s leak-check gunzips staged `.prproj`
blobs precisely because a plain `grep` cannot see inside one.

Placing, spanning and grading the layer: [`../premiere-grading.md`](../premiere-grading.md) § 1.

## `youtube-2160p-h264-cbr50.epr` — the locked YouTube export preset

H.264, 3840×2160, **CBR** (`ADBEVideoBitrateEncoding` = 0) with target = max = **50 Mbps**, AAC
320k. VideoToolbox's VBR treats the target as a ceiling, which is the whole reason for the lock; the
measurement behind it is in [`../lab-notes.md`](../lab-notes.md) § YouTube export.

## `cep-bridge-autostart.patch` + `apply-autostart-patch.py`

The CEP panel patch that makes the MCP bridge start on its own instead of needing a click. Applied
by the **script**, never by hand and never by `patch(1)`: it edits by content, so it is idempotent,
needs only python3 (Git Bash has no `patch` binary), and survives upstream line drift. **Re-run it
after any engine re-clone, version bump, or `cep-plugin/` re-copy**, or the panel silently reverts
to click-to-start.

## `locked-screen/`

Scratch AX/CGEvent tools from the locked-screen session. Only `keypid.swift` is used (it is how
`../premiere-dismiss.sh` posts Return to Premiere's pid); the rest are kept as a record of what did
not work — see that folder's own README before reaching for one.
