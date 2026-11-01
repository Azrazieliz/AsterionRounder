#!/usr/bin/env python3
"""Non-destructive Asterion Rounder continuity and reusable automation catalog.

Usage:
  python scripts/production/resume_project.py --check
  python scripts/production/resume_project.py --json
  python scripts/production/resume_project.py --catalog
  python scripts/production/resume_project.py --device
  python scripts/production/resume_project.py --record AR-012 --commit <SHA> \
    --state SOURCE_PRESENT --evidence '...' --next '...'

No code/build/download/install/uninstall or private media read occurs.
Only explicit --record atomically updates 6-star; owner approval is never changed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "production"
PROGRESS = DOC / "ADVANCEMENT_PROGRESS.json"
AUTHORITY = DOC / "PROJECT_7STAR_AUTHORITY.md"
AUTOMATION = DOC / "AUTOMATION_5STAR.md"
EXEC_MAP = DOC / "REPOSITORY_EXECUTION_MAP.md"
STATES = {
    "NOT_IMPLEMENTED", "SOURCE_PRESENT", "PARTIALLY_INTEGRATED",
    "INTEGRATED_UNTESTED", "TECHNICALLY_BLOCKED", "TESTED_FUNCTIONAL",
    "AWAITING_USER_TEST",
}
MANDATORY = [
    ROOT / "AGENTS.md", ROOT / "README.md", AUTHORITY, PROGRESS,
    AUTOMATION, EXEC_MAP, ROOT / ".github/workflows/openlocaloffice-build.yml",
]
PROGRAM_EXTENSIONS = {".py", ".cjs", ".sh", ".ps1", ".bat"}


def git(*args: str, timeout: int = 15) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["git", "-C", str(ROOT), *args],
            text=True, capture_output=True, timeout=timeout, check=False
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 127, ""
    return p.returncode, p.stdout.strip()


def catalogue() -> list[dict[str, object]]:
    rc, raw = git("ls-files", "--cached", "-z")
    if rc:
        return []
    workflow = (ROOT / ".github/workflows/openlocaloffice-build.yml").read_text(
        encoding="utf-8", errors="replace"
    )
    result: list[dict[str, object]] = []
    for path in sorted(raw.split("\0")):
        if not path or Path(path).suffix not in PROGRAM_EXTENSIONS:
            continue
        if not (
            path.startswith("openlocaloffice-build/hotfixes/")
            or path.startswith("openlocaloffice-build/pc-remote/")
            or path.startswith("openlocaloffice-build/noworld-bridge/")
            or path.startswith("scripts/production/")
        ):
            continue
        name = Path(path).name
        role = (
            "source transformation" if name.startswith(("apply-", "normalize-", "enable-"))
            else "regression check" if name.startswith(("test-", "android-runtime-"))
            else "test fixture generation" if name.startswith("create-")
            else "PC 3D integration" if "/pc-remote/" in path
            else "related product integration" if "/noworld-bridge/" in path
            else "production continuity" if path.startswith("scripts/production/")
            else "inspect before use"
        )
        result.append({
            "path": path, "role_from_filename": role,
            "referenced_in_ci": (name in workflow),
            "warning": "Role derived from filename. Inspect implementation before execution.",
        })
    # Include the currently executing program during initial staging.
    own = str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/")
    if all(x["path"] != own for x in result):
        result.append({
            "path": own, "role_from_filename": "production continuity",
            "referenced_in_ci": False, "warning": "New; not yet tracked.",
        })
    return result


def checks(data: dict, catalog: list[dict[str, object]]) -> list[str]:
    problems = []
    for file in MANDATORY:
        if not file.is_file():
            problems.append("missing mandatory file: " + str(file.relative_to(ROOT)))
    ids = set()
    authority_text = AUTHORITY.read_text(encoding="utf-8") if AUTHORITY.is_file() else ""
    if not data.get("tasks") or not isinstance(data["tasks"], list):
        problems.append("6★ has no task list")
    for task in data.get("tasks", []):
        ident = task.get("id")
        if not isinstance(ident, str) or ident in ids:
            problems.append("missing or duplicate stable task ID " + str(ident))
        ids.add(ident)
        if task.get("engineering_state") not in STATES:
            problems.append(f"{ident}: invalid engineering state")
        spec = task.get("requirement_ref")
        if not spec or spec not in authority_text:
            problems.append(f"{ident}: no indexed 7★ requirement {spec}")
        if "owner_verdict" not in task:
            problems.append(f"{ident}: owner verdict is missing (null is valid)")
        for field in ("verification", "next_action", "remaining", "automation", "implementation"):
            if field not in task:
                problems.append(f"{ident}: missing {field}")
        for source in task.get("implementation", {}).get("paths", []):
            if not (ROOT / source).is_file():
                problems.append(f"{ident}: source path unavailable: {source}")
    if len(catalog) < 10:
        problems.append("Automation catalog unexpectedly empty; inspect tracked scripts")
    return problems


def probe_device() -> dict:
    """Read only: package version, ADB transport and forward/reverse; NO files."""
    if not shutil.which("adb"):
        return {"available": False, "reason": "adb not installed"}
    commands = {
        "devices": ["devices", "-l"],
        "version": ["shell", "dumpsys", "package", "com.openlocal.office"],
        "reverse": ["reverse", "--list"],
        "process": ["shell", "pidof", "com.openlocal.office"],
    }
    out = {"available": True}
    for label, argv in commands.items():
        try:
            r = subprocess.run(["adb", *argv], text=True, capture_output=True,
                               timeout=12, check=False)
            value = r.stdout
            if label == "version":
                value = "\n".join(
                    line.strip() for line in value.splitlines()
                    if "versionCode=" in line or "versionName=" in line
                )
            # Do not persist private paths, identifiers or secrets in progress.
            elif label == "devices":
                value = "connected=" + str(sum(
                    1 for x in value.splitlines()[1:]
                    if re.match(r"^\S+\s+device(?:\s|$)", x)
                ))
            elif label == "reverse":
                value = "reverse_mappings=" + str(len([x for x in
                    value.splitlines() if x.strip()]))
            else:
                value = "process_running=" + str(bool(value.strip()))
            out[label] = {"ok": r.returncode == 0, "summary": value.strip()}
        except (FileNotFoundError, subprocess.TimeoutExpired):
            out[label] = {"ok": False, "summary": "unavailable or timed out"}
    return out


def atomic_record(args: argparse.Namespace, data: dict) -> dict:
    found = next((item for item in data["tasks"] if item["id"] == args.record), None)
    if found is None:
        raise ValueError("Unknown stable task ID; refusing to create an unreviewed requirement")
    if args.state not in STATES:
        raise ValueError("Invalid engineering state")
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", args.commit or ""):
        raise ValueError("A real Git SHA (7-40 hex chars) is required")
    rc, sha = git("rev-parse", "--verify", args.commit + "^{commit}")
    if rc or not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise ValueError("Commit does not resolve in this repo")
    # Prevent recording unrelated or unpublished history as current progress.
    rc, _ = git("merge-base", "--is-ancestor", sha, "HEAD")
    if rc:
        raise ValueError("Commit is not an ancestor of the current HEAD")
    previous = found["engineering_state"]
    found["engineering_state"] = args.state
    found["implementation"]["head_evidence_commit"] = sha
    history = found.setdefault("verification", {}).setdefault("history", [])
    event = {
        "date": dt.datetime.now(dt.timezone.utc).isoformat(),
        "commit": sha, "engineering_state": args.state,
        "evidence": args.evidence, "previous_engineering_state": previous,
    }
    history.append(event)
    found["verification"]["evidence"] = args.evidence
    found["next_action"] = args.next
    if args.remaining is not None:
        found["remaining"] = args.remaining
    # Owner verdict is neither accepted nor modified by this command.
    data.setdefault("change_log", []).append({
        "date": event["date"], "type": "ENGINEERING_PROGRESS",
        "task_id": found["id"], "commit": sha, "description": args.evidence,
    })
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=PROGRESS.parent,
        prefix=".progress-", suffix=".json", delete=False
    ) as stream:
        path = Path(stream.name)
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(path, PROGRESS)
    finally:
        if path.exists():
            path.unlink()
    return event


def main() -> int:
    # Windows PowerShell often defaults to cp1252. Never crash on 7-star labels.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
        sys.stderr.reconfigure(errors="backslashreplace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--check", action="store_true", help="Read-only 7★/6★/5★ check")
    ap.add_argument("--json", action="store_true", help="Machine-readable report")
    ap.add_argument("--catalog", action="store_true", help="All tracked automation scripts")
    ap.add_argument("--device", action="store_true", help="Read-only connected Android snapshot")
    ap.add_argument("--record", metavar="TASK_ID", help="Update one stable 6★ task (explicit)")
    ap.add_argument("--commit", help="Real commit on active development history")
    ap.add_argument("--state", choices=sorted(STATES))
    ap.add_argument("--evidence", help="What was actually implemented or verified")
    ap.add_argument("--next", help="Next concrete development action")
    ap.add_argument("--remaining", help="Current limitations; optional")
    args = ap.parse_args()
    if args.record and not all((args.commit, args.state, args.evidence, args.next)):
        ap.error("--record requires --commit --state --evidence --next")
    try:
        data = json.loads(PROGRESS.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"Cannot load 6★: {exc}", file=sys.stderr)
        return 2
    c = catalogue()
    rc, sha = git("rev-parse", "HEAD")
    _, branch = git("branch", "--show-current")
    issues = checks(data, c)
    event = None
    if args.record:
        if issues:
            print("Cannot write invalid 6★ state: " + "; ".join(issues), file=sys.stderr)
            return 2
        try:
            event = atomic_record(args, data)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    high = [x for x in data.get("tasks", [])
            if x["engineering_state"] in
            {"AWAITING_USER_TEST", "TECHNICALLY_BLOCKED", "PARTIALLY_INTEGRATED",
             "INTEGRATED_UNTESTED", "NOT_IMPLEMENTED"}]
    output = {
        "repo": data.get("repository"), "branch": branch,
        "commit": sha if rc == 0 else None,
        "recorded_branch": data.get("active_branch"),
        "validation": {"passed": len(issues) == 0, "problems": issues},
        "tasks": len(data.get("tasks", [])), "attention": [
            {"id": x["id"], "state": x["engineering_state"],
             "next": x.get("next_action")} for x in high
        ],
        "automation_count": len(c),
        "delivery": data.get("delivery"),
    }
    if args.catalog:
        output["automation_catalog"] = c
    if args.device:
        output["device"] = probe_device()
    if event:
        output["record"] = event
    if args.json or args.catalog:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"{output['repo']} — {branch} @ {sha[:12] if sha else 'unknown'}")
        print(f"7★/6★/5★ validation: {'PASS' if not issues else 'FAIL'}; "
              f"{output['tasks']} tasks, {len(c)} registered scripts")
        for issue in issues:
            print("  ISSUE:", issue)
        for task in high:
            print(f"  {task['id']}: {task['engineering_state']} — {task['next_action']}")
        if args.device:
            print("Read-only ADB:", json.dumps(output["device"], ensure_ascii=False))
        if event:
            print(f"6★ recorded {args.record} at {event['commit'][:12]}")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
