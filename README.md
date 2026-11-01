# Asterion Rounder

Existing Android file platform and reader, developed incrementally from File Gestioner. It opens and navigates authorized local and TeraBox files, with video/audio playback, image collections, EPUB/PDF/ZIP/archive viewing, office-file workflows, and a remote PC 3D bridge (still awaiting owner verification).

## Project authority & continuation

| Grade | Document | Purpose |
|---|---|---|
| 7★ | [Canonical project authority](docs/production/PROJECT_7STAR_AUTHORITY.md) | Approved intent, constraints, precise corrections and original references |
| 6★ | [Advancement progress](docs/production/ADVANCEMENT_PROGRESS.json) | Stable feature IDs, engineering evidence, remaining work, distinct owner verdict |
| 5★ | [Automation registry](docs/production/AUTOMATION_5STAR.md) | Existing executable pipelines and reuse-first instructions |
| — | [Repository execution map](docs/production/REPOSITORY_EXECUTION_MAP.md) | Source assembly, actual owners, external execution, protected artifacts |
| — | [AGENTS.md](AGENTS.md) | Mandatory continuation procedure |

Run `python scripts/production/resume_project.py --check` for a read-only consistency check and current Git state. Use `--json` for machine-readable output. This does **not** build, install, or change app data.

## Actual release state (2026-11-01)

- Active development: `fix/asterion-terabox-provider-20261031`, [PR #14](https://github.com/Azrazieliz/AsterionRounder/pull/14); development baseline prior to 7★ adoption: `1b42119d96fba6662c02a3762fc31157abb9260d`.
- Last verified install: **v0.15.14 / versionCode 36**, signed with the existing release identity; downloadable [GitHub release #486](https://github.com/Azrazieliz/AsterionRounder/releases/tag/file-gestioner-release-486).
- Owner reported the app now works properly, with **3D the remaining exception**, pending their Koikatsu Android investigation; no unilateral redesign or auto-acceptance of untested 3D.
- CI #486 built, signed, and published successfully, but *overall workflow failed* because the GitHub-hosted emulator never booted. Runtime CI validation is still outstanding.
- Current source is produced by [the existing release workflow](.github/workflows/openlocaloffice-build.yml) from six source parts, ordered overlays, additions, and hotfix scripts. **Do not build from an untracked PC-only `project/` copy and claim it is the repository.**

## Build and security

The release uses JDK 17, Android SDK 36, Gradle 9.6, and repository GitHub Actions, with an **existing** protected production keystore held in GitHub Actions secrets. Never place keys, TeraBox credentials, private media, ADB tokens, or user assets into public Git history. Preserve source and installation identity. Use the workflow for real signed releases; no replacement debug signature or data wipe.

See 5★ for the exact programs, ordered commands, known tests, and non-destructive verifier. Source and build evidence are not equivalent to owner acceptance.
