# Asterion Rounder — TeraBox-first UI direction and cross-app boundaries (2026-11-08)

## User-confirmed constraints
- TeraBox is the **only normal library**; Android-local content remains reachable through one **Open file** action.
- Search from the TeraBox root must find child and deeper descendant files, e.g. inside Apps, Art, Books.
- 300,000+ files: avoid whole-account/cloud requests on every keystroke. A saved, resumable, account-scoped filename index is the preferred backend; progressive indexing must be reported clearly.
- Existing readers, media player, archives, file transfers, Koikatsu/3D bridge, signing identity and local data must survive.
- Do not replace the approved UI until the owner selects a design variant.

## Current UI deficiencies (owner screenshot 2026-11-08)
1. Three equally prominent top controls (Open file / Collection / TeraBox) despite TeraBox-only usage.
2. TeraBox root incorrectly titled "Your library" without a clear storage/root breadcrumb.
3. Search says "current TeraBox folder" and currently only matches listed entries.
4. Oversized anonymous folder placeholders instead of readable folder rows or distinct directory cards.
5. Folders shown with 0 KB; misleading metadata.
6. Huge header and overlapping filters consume phone viewport; source browser should remain primary.
7. Media preview layout should be adaptive (art/image grid; mixed apps and documents compact rows).
8. Do not fake thumbnails or load entire media collections merely to decorate the UI.

## UI alternatives pending owner selection
- **Atlas:** media-first hybrid; compact directory shortcuts and elegant image/video previews; adaptive view by folder content. Recommended.
- **Vault:** dense professional file explorer; path, search, rows, efficient bulk operations.
- **Obsidian Library:** curated editorial home; recent, collections and large covers. Less useful for high-volume metadata tasks.

### Shared design contract
- Default root: TeraBox (requires configured, connected account); no confusing duplicate storage tabs.
- Primary action: global filename search; results with full parent path, status and location.
- Other action: **Open file** (Android ACTION_OPEN_DOCUMENT) with no continuous local-library indexing.
- Native TeraBox read-only provider/file streaming retained. Cloud token stays encrypted in Rounder's private Keystore-backed preferences, never shared.
- Desktop-logger/developer tools must not appear in the normal file UI; user-accessible diagnostics may live in Settings.
- Real errors, indexing/incomplete progress, and retry/refresh must remain visible.

## Confirmed repo-level cross-app inventory
| Relationship | Existing source evidence | Verified status / gap |
|---|---|---|
| **Downloader → TeraBox** | AsterionDownloader NDUS direct upload and Open Platform/Round Sync paths, outbox and success metadata. | Upload path exists, but independently verifying actual remote readability through Rounder is not established end-to-end. No credential sharing. |
| **TeraBox → Rounder** | FgTeraboxClient; native Android FgTeraboxDocumentsProvider; cached directory pages; direct media streams. | Cloud browse/open implementation exists. Recursive search index source is in PR #16 until built/tested. |
| **Rounder → Core** | Rounder's custom DocumentsProvider and Core's RoundSyncBridge launcher; Core has SAF browsing and a separate TeraBox integration. | **Not a unified shared index** and no confirmed device-tested Core consumption of Rounder's provider; preserve app separation. |
| **Core ↔ Art** | Core AsterionArtSheetProvider, Art CoreSheetBridge, Art CoreResultUploader. | Sheet provider still uses Knowledge DB, not Fusion; Art result upload receiver absent on inspected Core source; do not claim live two-way synchronization. |
| **Art → Downloader** | AsterionDownloaderBridge with explicit broadcast request and status. | Exists at source level; cross-signature/runtime interoperability not yet confirmed. |
| **Downloader → Core** | FlowLinkEmitter source/gallery/page/hash metadata broadcasts. | Treat broadcasts as untrusted hints; future durable signed, idempotent provenance handshake required. |
| **Rounder ↔ Koikatsu/NoWorld** | Source-linked 3D/card reader and PC bridge in Rounder; Asterion-kk local port. | Real conversion/asset exchange and mobile UI integration require device/PC proof; do not label functional based on source links. |
| **Asterion Control → Rounder** | Shared phone UI, native screen sharing and bridge commands. | Can be used for authorized install and acceptance tasks; no device test has been performed by this audit. |
| **Sound/Games/3D** | Separate repositories; no audited Rounder-native production bridge. | Do not invent integrations. |

## Recommended integration architecture (deferred)
Downloader uploads files → TeraBox remote → Rounder browses/streams from the same account → Core receives explicit SAF-intake/verified metadata permission, with source provenance from Downloader via a permissioned, replay-safe interface. Art requests Downloader downloads or publishes to Core when a secure results receiver is implemented. Never provide cloud secrets to other apps. Keep each app functional independently.

## Acceptance gates
1. Search from cloud root for a file located several folders under Art; verify path and correct original file opens.
2. Search from another subfolder; results still include descendants of the selected global TeraBox tree.
3. Repeated search doesn't enumerate remote folders; measure first index and subsequent query separately.
4. Reconnect with a different TeraBox account; old file names must not appear.
5. Interrupt/resume scan; no duplicate file entries or irreversible file operations.
6. Rounder signed Android release upgrades installed app; reader/media/archives still work.
7. New UI selection approved before changing navigation; verify on phone.

**Evidence boundary:** source inspection and CI are not device acceptance. All runtime statuses require explicit tests.
