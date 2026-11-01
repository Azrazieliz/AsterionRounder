# Asterion Rounder — mandatory agent continuity

This repository is **an existing production project**, not a starting template. Keep the approved application, package identity, signing certificate, source archive, overlays, assets, and current integrations.

## Required entry sequence
1. Fetch latest GitHub state, identify active development branch and PR; do not rely on an old workstation checkout.
2. Read [7★ Authority](docs/production/PROJECT_7STAR_AUTHORITY.md) → [6★ Progress](docs/production/ADVANCEMENT_PROGRESS.json) → [5★ Automation](docs/production/AUTOMATION_5STAR.md), in that order.
3. Read [Execution Map](docs/production/REPOSITORY_EXECUTION_MAP.md) and inspect only relevant current source/dependencies.
4. Run `python scripts/production/resume_project.py --check` before coding; consult the existing automation registry before adding a new program.
5. Work from the highest-priority **actionable** requirement, reusing known-good code and tooling. Do not repeat completed work or independently redesign accepted UX.
6. Before any material implementation, read 6★. Afterward update its stable task record, code location, precise Git commit/PR, evidence, engineering state, dependencies, and next action. Update 5★ for new/changed automation; 7★ only following an actual approved decision.
7. Distinguish **code present**, **tested functional**, **unverified**, **blocked**, and **owner verdict**. Never infer owner acceptance/rejection from a commit, build, or missing test.
8. Commit and push to the active PR branch; do not push unreviewed work to main, expose secrets, reset signing identities, destroy user data, or run destructive device commands.
9. Report implemented vs verified vs remaining clearly. A conversation change never restarts project history.

## Current owner decisions
- Preserve the v0.15.14 library/player/ZIP/EPUB behavior and appearance (latest owner report: working properly).
- The sole explicitly remaining end-user uncertainty is 3D. The owner is exploring a native Android Koikatsu solution and will report results. Do **not** represent PC 3D, Blender, or a Koikatsu Android port as working without device evidence.
- Read exact latest details in 7★ and task-level 6★ rather than interpreting these lines as replacement specifications.

## Source-of-truth warning
The checked-in `openlocaloffice-build/project/` folder may not exist: the actual Android project is **reassembled** from immutable source parts and applied patches in `.github/workflows/openlocaloffice-build.yml`. Untracked generated build trees on a PC are not canonical. All approved source/patch updates must be reproducible from tracked GitHub files.
