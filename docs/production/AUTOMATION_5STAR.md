# AUTOMATION 5★ — executable registry and reuse-first production instructions

**Scope:** Asterion Rounder. Authority: [7★](PROJECT_7STAR_AUTHORITY.md). Actual progress: [6★](ADVANCEMENT_PROGRESS.json). All tooling listed here is **existing tracked source** unless expressly marked **NEW**. Its presence is *not* proof the tool or endpoint succeeds in every environment.

## Mandatory reuse-first procedure

1. Read 7★ then 6★ before changing code. Check the specific unfinished task, source location and verification.
2. Search this registry and the **actual executable** (not merely its name) for an existing capability. Run `python scripts/production/resume_project.py --catalog` for the exact currently tracked automation paths. Validate inputs, dependencies, permissions and non-destructive effects.
3. Prefer extending the existing build/source/remote/verification workflow. Never build a parallel Android compilation pipeline just to apply a new patch.
4. If the capability is genuinely missing, document the gap and create **one** generalized, reproducible, incremental and safe program. Add it here, run it for the actual task, then update 6★ with concrete results and precise commit.
5. Output may be generated into a local temporary build directory, but **all approved source changes** and required artifacts must be published via the existing GitHub workflow.
6. Test against originals when functionality depends on owner files. Existing CI-generated EPUB/ZIP fixtures test mechanics only, **not** the owner’s original media or source compatibility.

## 5★ program registry

| Program / canonical path | Input / execution | Output | Dependencies and safety |
|---|---|---|---|
| **NEW** `scripts/production/resume_project.py` | `python scripts/production/resume_project.py --check`; `--json` for machine output; `--catalog` lists indexed scripts; `--device` runs optional read-only ADB checks | Git branch/HEAD, 7★/6★/5★ validation, task priorities, source inventory, diagnostics | Python stdlib + Git; ADB optional; **never** deletes, builds, installs or changes app state |
| **NEW** same program `--record TASK_ID --commit SHA --state ENGINEERING_STATE --evidence TEXT --next TEXT` | Explicit material change and available commit, optionally `--remaining TEXT` | Atomic 6★ task update and audit log | Validates commit, stable task ID and enum; **never** modifies an owner verdict |
| `.github/workflows/openlocaloffice-build.yml` | GitHub PR/push or explicit workflow dispatch; source archive parts and tracked patch overlays in exact declared order | Expanded source artifact, compiled APK, signature-checked signed release, debug APK and attempted emulator verification | JDK 17, Gradle 9.6, API 36, GitHub secrets for **existing** signer; no key replacement or secret export |
| `openlocaloffice-build/source.part*` + `patches/*.patch` + `feature-patch/feature.patch.gz.b64.*` | Reassemble verified ZIP, apply ordered modifications as in workflow | Baseline Android project | Never treat an untracked `project/` folder as newer than GitHub |
| `openlocaloffice-build/hotfixes/apply-*.py` | Run **only in workflow order**, from `openlocaloffice-build/project`, on expected base source | Reproducible patches for interface, readers, provider, media, system services, 3D and editing | Many are one-time string transforms (not universally idempotent); never indiscriminately rerun on an already patched tree |
| `openlocaloffice-build/hotfixes/normalize-release-icons.py` | After all approved source modifications, before release assemble | Production icon assets | Part of existing release workflow |
| `openlocaloffice-build/hotfixes/test-*.cjs` | Node tests against **assembled** project in workflow | Source/contract assertions | Does not replace device testing; inspect test when code contracts change |
| `openlocaloffice-build/hotfixes/android-runtime-smoke.sh` | GitHub-hosted Android emulator with debug app installed | EPUB, ZIP, navigation checks and screenshots/logs | Uses generated fixtures **only in CI**; #486 failed before smoke at emulator boot (port 5554 refused), not a proven application failure |
| `openlocaloffice-build/hotfixes/create-large-epub-fixture.py`, `create-image-zip-fixture.py` | CI-only mechanical test fixtures | Temporary EPUB / ZIP stress inputs | Do **not** substitute these for owner's real media or put on their phone |
| `openlocaloffice-build/pc-remote/fg_remote_server.py` | Existing authenticated PC session and original model/card; companion `fg_studio_background_window.py`, `fg_studio_hidden.py`, `fg_blender_frame.py` | Native remote 3D status/frames, where installed and connected | Requires actual Koikatsu/Blender PC environment and pairing; presence of scripts is **not** verified rendering |
| `openlocaloffice-build/pc-remote/FGNativeBackground.cs` | Existing approved native PC host | Remote process/control helper | Preserve existing executable and trust boundary; never launch unrelated assets |
| `openlocaloffice-build/noworld-bridge/test_bridge.py` | NoWorld integration development only | Bridge-specific test evidence | Separate product/integration; not a replacement Rounder workflow |

### Existing categorized implementation programs (not replacements)

| Family | Existing script ownership and applicability |
|---|---|
| Cloud, throughput, large media | `apply-direct-terabox-20261031.py`, `apply-rounder-cloud-backpressure-20261031.py`, `apply-rounder-large-range-20261031.py`, `apply-rounder-preview-only-policy-20261031.py`, `apply-scale-library-20261031.py`, `apply-scale-media-20261031.py`, `apply-streamed-image-folders-20261031.py` |
| ZIP/EPUB/image reading | `apply-universal-reader-backend.py`, `apply-epub-native-reader.py`, `apply-streamed-large-readers.py`, `apply-rounder-zip-descriptor-lifetime-20261101.py`, `apply-rounder-aspect-grid-archive-20261101.py`, `apply-reader-controls-20261030.py`, `apply-rounder-ui-readers-20261101.py`, `apply-image-zip-reader-polish.py` |
| Video and UI | `apply-rounder-video-aloha-20261101.py`, `apply-rounder-video-single-mode-20261101.py`, `apply-rounder-video-orientation-20261101.py`, `apply-rounder-video-premium-20261101.py`, `apply-rounder-classic-library-20261101.py`, `apply-rounder-book-speed-20261101.py`, `apply-rounder-final-ui-20261031.py` |
| Documents, editing, conversion | `apply-docx-flow-editor.py`, `apply-spreadsheet-interactions.py`, `apply-spreadsheet-mobile-20261031.py`, `apply-mobile-spreadsheet-ui.py`, `apply-file-conversion-20261031.py`, `apply-native-file-actions-20261031.py`, `apply-library-transfer-20261031.py` |
| 3D and PC bridge | `apply-3d-asset-viewer.py`, `apply-native-pc-remote.py`, `apply-rounder-native-pc-transport-20261101.py`, and programs in `pc-remote/` |
| Regression | `test-media-image-regressions.cjs`, `test-premium-v13.cjs`, `test-rounder-end-to-end-contract.cjs`, `test-rounder-aspect-archive-20261101.cjs`, `test-rounder-premium-video-20261101.cjs`, `test-archive-saf-regression.cjs`, `test-premium-book-reader.cjs`, `test-native-scroll.cjs` |

**Directory-wide discovery:** `python scripts/production/resume_project.py --catalog` enumerates *all* tracked scripts (including those not individually named above) and identifies which files appear in the release workflow. Before running any one, open its source and confirm preconditions, expected input and side effects. A filename is not a supported command contract.

## Real source-to-delivery execution sequence

1. Verify the active GitHub branch and 6★ state. Keep `openlocaloffice-build/source.part*` and approved additions unchanged where working.
2. Implement changes as new or modified **tracked** source/patch components; if automation changes, update this registry. No persistent PC-only edits.
3. Run applicable source regression tests against the **workflow-assembled** source; do not assume direct execution of `apply-*.py` scripts is idempotent.
4. CI assembles and builds; existing GitHub secrets sign; verify fingerprint and version before any in-place ADB update.
5. Run supported real-device checks using the original files and mark evidence accurately. If emulator fails to boot, record CI infrastructure failure separately; do not suppress the failing test to claim a fully green build.
6. Update 6★ stable task record with exact commit/verification, then push. Preserve source, artifacts and logs.

## Current automation gap

GitHub Actions #486 passed release compile/sign/publish but emulator launch failed with port 5554 connection refused before the smoke tests. A boot-preflight/runner investigation is pending. 3D round-trip functional testing is dependent on the owner's native Koikatsu/PC environment results; do not add a duplicate viewer or claim it succeeded.
