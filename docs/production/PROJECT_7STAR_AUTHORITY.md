# PROJECT 7★ AUTHORITY — Asterion Rounder

**Canonical requirement and design index.** Adopted 2026-11-01. Repository: `Azrazieliz/AsterionRounder`. This links, never replaces, original source, commit history, detailed owner decisions, screenshots or PR discussions.

## Intended final product and inviolable baseline

Asterion Rounder (previously File Gestioner/OpenLocalOffice) is the existing phone-first Android file manager, media player and reader for the owner's **actual** local and TeraBox files. Preserve its original content and responsive progressive reading. It already includes SAF file handling, direct TeraBox provider/connector, EPUB/PDF/ZIP and image archives, document/spreadsheet workflows, video/audio playback, 3D model/card classification and PC-assisted 3D integration. **Do not restart, substitute a competing app, use fake files to replace the user's own, or casually redesign the product.**

Package `com.openlocal.office`, original approved signing certificate, original user data and any accepted source/assets must remain intact.

## Approved requirements and superseding owner corrections

| ID | Current owner intent | Evidence/reference |
|---|---|---|
| AR-UX-001 | Preserve the preferred classic Asterion library and branding; **no Home/Welcome dashboard**. | Owner screenshots and explicit feedback, 2026-11-01; commit `2e5b673` |
| AR-LIB-002 | Two **large** landscape video thumbnails per row, including mixed folders. No three-dot menus or redundant VIDEO/ZIP/EBOOK labels covering tiles. File actions via long press/context menu. | Owner correction 2026-11-01, commit `02f6bcf` |
| AR-VID-003 | Video displays the **complete native aspect ratio** by default; automatic crop was rejected. Optional pinch zoom and pan, compact useful controls, Play Next / Replay / Shuffle, accessible seek bar, phone orientation and independent lock, immersive mode without taskbar overlap. No Share button. | Owner correction after v0.15.13, commit `02f6bcf`; prior player changes `910626d` |
| AR-IMG-004 | Reading choices have distinct semantics: **Pages** = discrete fitted page with left/right tap/swipe; **V-scroll** = vertical continuous; **H-scroll** = horizontal continuous without snapping. No divider bars or special webtoon reader; correct sort order; pinch zoom, double-tap return to fit; no zoom smaller than fit. Loaded images must not blink when loading more. | Owner testing 2026-10-27 through 2026-11-01, commit `2027701` |
| AR-BOOK-005 | Genuine ZIP/EPUB images and text, progressive read of completed pages while other parts download, persistent decoded images, bounded memory, correct encoded filenames, no forced timeout cancel, retry/fallback native decode without substituting another source; useful compact non-image ZIP listing; large books supported where provider allows. | Owner screenshots and corrections, commits `e5a606f`, `02f6bcf`, `1b42119` |
| AR-CLOUD-006 | Original actual local and TeraBox content, direct/efficient native connector/SAF access, correct caching and progressive previews. Never manufacture replacement files or replace restricted content with random media. Protect credentials and private data. | Explicit owner instructions, `FgTeraboxClient` / `FgTeraboxDocumentsProvider` |
| AR-DOC-007 | Preserve functional CSV/XLSX editing, rich document formats, image/ZIP/PDF reading, conversion and immersive layouts wherever implemented. Missing format-level tests do not count as owner rejection or proof of support. | Original source, iterative owner reports, release workflow |
| AR-3D-008 | Koikatsu `Open 3D` **only** for valid Koikatsu cards; preserve original Koikatsu/Blender/model-viewer/PC-assisted integration. Display real loading/ready/error state, do not claim success on mere connection. Owner is exploring a native Koikatsu Android app and will test later. **3D remains unverified**. | Latest owner feedback 2026-11-01; `pc-remote/` and 3D bridge source |
| AR-REL-009 | Preserve production signing identity and application ID, install without data wipe; use genuine compiled and signed APK; distinguish committed source, build passing, real-device verification and explicit owner acceptance. | Release workflow and owner directives |
| AR-SEC-010 | Don't destroy, move or override approved code/assets just to organize; protect original user media, device data, personal credentials, signing materials and external files. Only use authorized PC/phone as execution environments. | Permanent owner directives |
| AR-PREV-011 | Display app-generated TeraBox image thumbnails from readable originals instead of relying on provider previews, including animated GIFs. Add an affected-image filter: automatically identify missing server preview URLs, with an explicit owner flag for visual placeholders that metadata cannot detect. Keep the existing approved cards, readers, cloud files and non-destructive behavior intact. | Owner request 2026-11-14; source branch `fix/rounder-terabox-gif-thumbnail-recovery-20261114` |

**Current owner statement (2026-11-01):** “It seems like everything works properly now. Just 3d but I might just turn koikatsu to an android app (to be tested first, I'll come back when I'lI have results).” This means the owner reports broad satisfaction with the **non-3D** release; it does **not** certify 3D or every individual edge case.

## Canonical technical and data authority

- The Android project is assembled in GitHub Actions from tracked six-part archive `openlocaloffice-build/source.part*` (checksum gate), `feature-patch/`, `feature-overrides/`, `patches/`, `overrides/`, `additions/`, and **ordered** `hotfixes/` scripts. The order in `.github/workflows/openlocaloffice-build.yml` matters. An untracked PC `openlocaloffice-build/project/` is only an execution output, **not** source authority.
- App code assembled by workflow includes `MainActivity.java`, `ReaderLibrary`, `BookArchive`, `SeekableZip`, `RemoteBookSpool`, `FgTeraboxClient`, `FgTeraboxDocumentsProvider`, `FgMediaPlayer`, assets `premium-library.js`, `reader-controls.js`, `epub-reader.js`, `universal-reader.js`, `style.css`, and 3D/viewer components.
- Existing `openlocaloffice-build/pc-remote/` Python/C# bridge and Blender/Koikatsu scripts are source; the PC is execution-only. Source asset provenance is the tracked files and the original archive (not screenshots reconstructed as source).
- Signing identities/keystores/passwords/TeraBox credentials are **not** to be recorded in Git. GitHub Actions release secrets and their existing security workflow remain protected.
- The repository also contains `openlocaloffice-build/noworld-bridge/README.md` and `RECOVERY_20261027.md`; these document an integration and are **not** a redesign authority for Rounder.

## Preservation, conflict and acceptance rules

Later explicit owner decisions supersede conflicting earlier ones: video **FIT** overrides the former edge-cropping request; two-column video grid overrides three-column mobile gallery; removal of Home overrides the previously added dashboard; page modes use the explicit three-way distinction. Do not erase earlier source or decisions; inspect Git history and the actual user-supplied screenshots, PR #14 conversation, and existing artifacts for detailed requirements.

The repo previously contained **no tracked comprehensive canonical specification master**. Treat this as the highest-priority **index**, not a fabricated reconstruction of every hidden earlier conversation detail. Missing original detail is an evidence gap, not permission to simplify.

See [6★](ADVANCEMENT_PROGRESS.json) for engineering status, linked requirement IDs, evidence and distinct owner verdict. See [5★](AUTOMATION_5STAR.md) and the [execution map](REPOSITORY_EXECUTION_MAP.md). Update this file **only** for approved design changes, and never because a technical build/test failed.
