# Asterion Rounder — repository execution map

**Repository:** `Azrazieliz/AsterionRounder`. **Active production development PR:** [#14](https://github.com/Azrazieliz/AsterionRounder/pull/14), branch `fix/asterion-terabox-provider-20261031`. Latest verified signed Android version on 2026-11-01: v0.15.14 / code 36. Do not substitute main or a local checkout without checking `git fetch`.

## Canonical locations and grade responsibilities

| Grade | Real location | Source owner or role |
|---|---|---|
| 7★ | `docs/production/PROJECT_7STAR_AUTHORITY.md` | User's approved design decisions, exact references, conflict resolution |
| 6★ | `docs/production/ADVANCEMENT_PROGRESS.json` | Stable feature state, technical evidence, distinct owner verdict |
| 5★ | `docs/production/AUTOMATION_5STAR.md`, `scripts/production/resume_project.py`, existing workflows and patch scripts | Reusable tasks and continuity |
| 4★ | **assembled Android project** at `openlocaloffice-build/project/` during GitHub Actions | Executable Android application; generated/reconstructed, **not** canonical tracked source tree |
| 3★ | `openlocaloffice-build/source.part*`, `patches/`, `feature-patch/`, `feature-overrides/`, `overrides/`, `additions/`, `branding/`, `hotfixes/`, `pc-remote/`, `three-vendor/` | Authored original source and approved integration/visual assets |
| 2★ | GitHub Actions signed releases, tests, CI logs, proof artifacts; `docs/production/evidence/` for **non-private** checked-in evidence | Builds and verification; do not confuse with source or acceptance |
| 1★ | Local untracked `openlocaloffice-build/project/`, `__pycache__`, intermediate APKs/temp ZIPs, emulator caches | Disposable processing outputs **only** when independent from original user data |

**Do not move or delete tracked files to fit the grade table.** Gradings classify responsibility, not value or permission to discard.

## Build assembly is the authority

`.github/workflows/openlocaloffice-build.yml` is the canonical ordered recipe. It verifies SHA-256 of reconstructed `source.zip`, extracts six `source.part*` units, applies `patches/*.patch` and feature overlays, copies source additions and native assets, applies **ordered** Python hotfixes, checks source contracts, builds via Gradle, and signs with pre-existing GitHub Actions secret-held identity. The original-source SHA gate is part of the contract.

Entry points:
- `openlocaloffice-build/additions/BookArchive.java` / `SeekableZip.java` / `RemoteBookSpool.java`: ZIP/EPUB streaming and independent descriptor lifetime.
- `openlocaloffice-build/additions/FgTeraboxClient.java` / `FgTeraboxDocumentsProvider.java`: cloud access and Android SAF.
- `openlocaloffice-build/additions/FgMediaPlayer.java` plus ordered `apply-rounder-video-*.py`: Android native playback.
- `openlocaloffice-build/additions/premium-library.js`, `reader-controls.js`, `epub-reader.js`, `universal-reader.js`: user-facing library/readers, changed incrementally by ordered hotfixes.
- `openlocaloffice-build/pc-remote/fg_remote_server.py`, `fg_studio_background_window.py`, `fg_blender_frame.py`, `FGNativeBackground.cs`: authenticated external 3D execution; user reports 3D still to be validated.
- `openlocaloffice-build/three-vendor/`: tracked external 3D viewer dependencies and asset loaders; preserve licensing and provenance.
- `openlocaloffice-build/noworld-bridge/`: related integration with separate product, preserve boundaries.

## Executable environments and prohibited mutations

- **GitHub** stores durable source, complete commit/PR history, workflow, code review, and release artifacts. Adopt branch/PR already in use; use source commits for changes, not an untracked PC-only expanded workspace.
- **Remote authorized Windows PC:** original Koikatsu/Blender may live here; it is authorized for necessary 3D operations, build diagnostics, ADB, and signing verification. Do not assume a working 3D render from the existence of processes or a socket. Do not commit PC-specific credentials, private game mods, user media or generated personal content.
- **Android Samsung phone via ADB:** actual integration/playback tests. Never wipe, uninstall, reset, change signing identity or replace private files solely to test this repository.
- **TeraBox:** external source/user data provider. Access through existing authenticated SAF/native flow. Do not mirror user files into public Git.
- **GitHub Actions:** JDK 17, Gradle 9.6, SDK API 36, secret-held preserved keystore. Signed release assets are distinct from emulator-only debug artifacts.

## Current execution evidence and mismatch

GitHub Actions run #486, commit `1b42119`: production release successfully compiled, signed and published; verified installed `com.openlocal.office` versionCode 36, versionName 0.15.14. **Overall CI failed** because the x86_64 emulator never reached ADB at TCP port 5554. This is an infrastructure/runtime verification gap; do not call the job green or claim EPUB/ZIP smoke ran there.

The owner explicitly reports the latest app now works **except 3D**, and plans to test Koikatsu on Android. 3D remains awaiting user test; do not replace or rearchitect it in the meantime.

## Initial non-destructive adoption findings

1. Previously absent: root `README.md`, `AGENTS.md`, 7★/6★/5★ hierarchy and a single command to resume, inventory, and record progress.
2. Working but not duplicated: canonical build, extensive patch scripts, source/source-archive layers, CI source regression tests, remote PC helpers, Android instrumentation scripts.
3. Drift risk: similar `apply-*.py` files across dates can conflict; **workflow order** must remain canonical and test contracts updated only for substantive approved behavior changes.
4. Test gap: CI emulator startup failure before runtime validation, and 3D unverified pending owner's Android Koikatsu investigation.
5. Preservation: related NoWorld bridge, vendor source, original ZIP parts and signing process stay exactly where they are.

For future work, read [AGENTS](../../AGENTS.md), [7★](PROJECT_7STAR_AUTHORITY.md), [6★](ADVANCEMENT_PROGRESS.json), then [5★](AUTOMATION_5STAR.md), and run `python scripts/production/resume_project.py --check`. Don't repeat the initial audit without evidence of material source drift.
