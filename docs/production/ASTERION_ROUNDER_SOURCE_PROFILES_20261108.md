# Asterion Rounder — unified app-origin file routing (corrected 2026-11-08)

## User's authoritative correction
**Asterion Downloader is ONE application.** Kuroha, Kyora and VideoFlow were deleted as separate apps and merged into Asterion Downloader. These must not appear as separate app identities, independent active source configurations, or permanent new TeraBox destinations.

Some *historical cloud folders* may retain those labels, as the Downloader repository still has legacy default paths in older upload code. Those historical names are directory names only. They may be explicitly mapped to the single Downloader source, but must not be interpreted as currently installed standalone apps.

Potential additional origin applications:
- **Asterion Art** — generated artwork and approved exports.
- **Asterion Sound** — audio exports.
- **Asterion 2D→3D** — produced models and textures.
- **Asterion KK** — character cards, CharaStudio scenes, mods and models (only when the native Android version produces them).

These origins are **possible**, not evidence that the corresponding app writes to a particular cloud folder. No app is assumed to have uploaded anything.

## Implemented v0.15.17 source update

`FgRounderSources.java` centralizes five source profiles. The owner configures the actual TeraBox incoming/export folder per connected account in **Organizer → Connected Asterion sources**. No guessed root folders are silently registered.

Routing uses:
1. Exact account-scoped, user-confirmed source directory; then
2. Deterministic extension and safe subfolder markers; then
3. A destination rule for that source; otherwise **leave unmoved**.

General `/Incoming` and `/Downloads` are generic catchalls, not proof of any app identity. Same-name files do not establish a source. Existing metadata/MD5 duplicate comparisons are separate and **never delete**.

### Deterministic routing table
| Source | Strong routing evidence | Destination |
|---|---|---|
| Asterion Downloader | Configured export folder + known file extension | `/Art/Downloads`, `/Books/Downloads`, `/Videos/Downloads`, `/Apps/Downloads`, `/Audio/Downloads`, `/3D/Downloads`, etc. |
| Asterion Art | Confirmed Art export folder + image/video/project extension | `/Art/Generated`, `/Art/Animations`, `/Art/Projects` |
| Asterion Sound | Confirmed Sound export folder + audio/MIDI extension | `/Audio/AsterionSound`, `/Audio/MIDI` |
| Asterion 2D→3D | Confirmed converter output folder + model extension, or image under a `textures` subfolder | `/3D/Models`, `/3D/Textures` |
| Asterion KK | Confirmed KK output folder + explicit `chara/characters/cards/scenes/studio/models/mods` path markers and supported type | `/Games/Koikatsu/Characters`, `/Scenes`, `/Models`, `/Mods` |
| Generic TeraBox incoming | Known extension only, no app attribution | Type-specific `Downloads` destination |

**Important:** A Koikatsu PNG with no character/scene marker remains **unclassified**. A PNG found in a general Download folder is categorized by type only, with no invented creator app.

### Permission and safeguards
- Each source root is explicit and account-scoped.
- Broad collection roots (`/Art`, `/Books`, `/Apps`, etc.) are rejected as source roots to protect existing library content.
- Any automatic sorting is separately opt-in globally **and per registered app source**. General incoming roots use the existing global toggle.
- Manual moves show proposed source and destination, require confirmation, and cap batches at 30.
- The TeraBox server-side move requests collision-fail and verifies remote destination metadata; no network write is counted as completed until a matching read-back.
- No AI, inferred provenance, file deletion or overwrite operations.
- Legacy subproduct directory paths are not polled automatically, but an owner can manually map a historical folder as an Asterion Downloader source.

## Remaining validation
- Build and signing must pass GitHub CI after updating the native and UI contracts.
- Actual connected-account source paths, backend move compatibility, index updates, scheduling and device rendering still need physical Android tests.
- If a future application emits signed, authenticated upload provenance, it should become the preferred source identity. Current folder mapping is a deterministic fallback, not authenticated app telemetry.
