#!/usr/bin/env python3
"""Consent-gated, non-destructive installation of bundled Codex Practices Skills.

Python 3.11+ on Linux/macOS. Does not run project code or make network calls.
AGENTS/Behavior Q&A, MCP trust policies and fact-owner maps remain guided tasks.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import uuid

# module: package skill directory, installed skill name, scope
MODULES = {
    3: ("project-memory", "project-memory", "project"),
    4: ("permissions", "permissions-guardrails", "global"),
    5: ("external-guardrails", "external-guardrails", "global"),
    6: ("skills-management", "skills-management", "global"),
    7: ("verification", "verification", "project"),
    8: ("multi-agent", "multi-agent", "project"),
    9: ("model-efficiency", "model-efficiency", "project"),
    10: ("mcp-management", "mcp-management", "project"),
    11: ("project-inventory", "project-inventory", "project"),
}
DEPENDENCIES = {5: (4,), 8: (3,), 10: (4, 5), 11: (3,)}
CONFIRM_INSTALL = "INSTALL_APPROVED_CODEX_PRACTICES"
CONFIRM_ROLLBACK = "ROLLBACK_CODEX_PRACTICES"
MAX_FILE = 1024 * 1024
MAX_TOTAL = 6 * 1024 * 1024


class SetupError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def paths(project_arg: str, package: Path) -> tuple[Path, Path, Path]:
    project = Path(project_arg).expanduser().resolve(strict=True)
    if not project.is_dir() or project == package:
        raise SetupError("Choose a real target project, not the Codex Practices package")
    global_skills = Path.home().resolve() / ".agents" / "skills"
    local_skills = project / ".agents" / "skills"
    return project, global_skills, local_skills


def assert_no_links(path: Path, stop: Path) -> None:
    """Reject symlinked managed directories from the scope root downward."""
    cursor = path
    while cursor != stop:
        if cursor.is_symlink():
            raise SetupError("Symlinked managed path: " + str(cursor))
        if stop not in cursor.parents:
            raise SetupError("Managed path escapes expected scope")
        cursor = cursor.parent


def contents(directory: Path, expected_name: str | None = None) -> dict[str, bytes]:
    if directory.is_symlink() or not directory.is_dir():
        raise SetupError("Missing, unsafe or non-directory Skill: " + str(directory))
    found = {}
    total = 0
    for file in sorted(directory.rglob("*")):
        if file.is_symlink():
            raise SetupError("Symlink inside Skill: " + str(file))
        if file.is_dir():
            continue
        if not file.is_file():
            raise SetupError("Unexpected Skill entry: " + str(file))
        relative = file.relative_to(directory).as_posix()
        data = file.read_bytes()
        total += len(data)
        if len(data) > MAX_FILE or total > MAX_TOTAL or len(found) >= 100:
            raise SetupError("Skill exceeds bounded installer limits: " + str(directory))
        found[relative] = data
    frontmatter = found.get("SKILL.md", b"")
    if expected_name is not None:
        try:
            header = frontmatter.decode("utf-8").split("---", 2)
            actual = re.search(r"(?m)^name:\s*(\S+)\s*$", header[1]).group(1)
        except (UnicodeError, IndexError, AttributeError):
            raise SetupError("Missing or invalid Skill frontmatter in " + str(directory)) from None
        if actual != expected_name:
            raise SetupError("Skill name mismatch: expected " + expected_name)
    return found


def fingerprint(files: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for relative, data in sorted(files.items()):
        encoded = relative.encode("utf-8")
        h.update(len(encoded).to_bytes(4, "big"))
        h.update(encoded)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def present_modules(package: Path) -> list[int]:
    return [n for n, (folder, _, _) in MODULES.items()
            if (package / "skills" / folder / "SKILL.md").is_file()]


def selected_modules(spec: str, package: Path) -> list[int]:
    if spec == "available":
        requested = set(present_modules(package))
    elif spec == "all":
        requested = set(MODULES)
    else:
        try:
            requested = {int(x.strip()) for x in spec.split(",")}
        except ValueError:
            raise SetupError("Use comma-separated module numbers 3..11") from None
        if not requested or requested - set(MODULES):
            raise SetupError("Unknown module number")
    pending = list(requested)
    while pending:
        n = pending.pop()
        for dependency in DEPENDENCIES.get(n, ()):
            if dependency not in requested:
                requested.add(dependency)
                pending.append(dependency)
    return sorted(requested)


def build_plan(project_arg: str, spec: str, package: Path | None = None) -> dict:
    package = package or package_root()
    project, global_root, local_root = paths(project_arg, package)
    targets = []
    for number in selected_modules(spec, package):
        folder, name, scope = MODULES[number]
        original = package / "skills" / folder
        target_root = global_root if scope == "global" else local_root
        other_root = local_root if scope == "global" else global_root
        target = target_root / name
        assert_no_links(target, Path.home().resolve() if scope == "global" else project)
        assert_no_links(other_root / name, project if scope == "global" else Path.home().resolve())
        entry = {"module": number, "name": name, "scope": scope,
                 "source": str(original), "destination": str(target),
                 "dependencies": list(DEPENDENCIES.get(number, ()))}
        if not (original / "SKILL.md").is_file():
            entry.update(status="unavailable", detail="Not included in this package checkout")
        else:
            files = contents(original, name)
            entry["sha256"] = fingerprint(files)
            entry["files"] = len(files)
            if (other_root / name).exists() or (other_root / name).is_symlink():
                entry.update(status="conflict", detail="Same Skill already present in the other scope")
            elif target.exists() or target.is_symlink():
                if target.is_symlink() or not target.is_dir():
                    entry.update(status="conflict", detail="Target is a symlink or non-directory")
                else:
                    try:
                        same = fingerprint(contents(target, name)) == entry["sha256"]
                    except SetupError:
                        same = False
                    entry.update(status="unchanged" if same else "conflict",
                                 detail="Installed content matches" if same else "Existing Skill differs; never overwrite")
            else:
                entry.update(status="create", detail="New Skill; no user files replaced")
        targets.append(entry)
    summary = {
        "version": 1,
        "project": str(project),
        "package": str(package),
        "modules": targets,
        "guided_setup": [
            "1+2: run one existing AGENTS.md / Behavior Rules interview from recipes/setup-agents-md.md, only if needed; never overwrite user instructions silently",
            "4: profile and infrastructure permissions require separate session consent",
            "10: MCP trust policy, executable/version vetting and actual config apply are separate opt-in operations",
            "11: fact-owners.toml needs real approved owner paths; never copy example records blindly",
            "Real Codex CLI tests and integration verification are deferred until explicitly approved",
        ],
        "changes_user_config": False,
        "runs_tests": False,
        "runs_project_code": False,
        "downloads_packages": False,
        "replaces_existing_skills": False,
    }
    summary["plan_sha256"] = sha(canonical(summary))
    return summary


def state_dir() -> Path:
    return Path.home().resolve() / ".local" / "state" / "codex-practices" / "unified-installer"


def ensure_private_state(root: Path) -> None:
    home = Path.home().resolve()
    assert_no_links(root, home)
    if not root.exists():
        root.mkdir(parents=True, mode=0o700)
    if not root.is_dir() or root.is_symlink():
        raise SetupError("Installer state must be a regular directory")
    st = root.stat()
    if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) & 0o077:
        raise SetupError("Installer state directory must be owned by current user and private")


def write_json(path: Path, data: dict) -> None:
    fd, temporary = tempfile.mkstemp(prefix=".installer-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(canonical(data) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def create_skill(entry: dict, project: Path, package: Path) -> None:
    scope_root = (Path.home().resolve() if entry["scope"] == "global" else project)
    destination = Path(entry["destination"])
    assert_no_links(destination, scope_root)
    if destination.exists() or destination.is_symlink():
        raise SetupError("Install destination appeared or changed: " + str(destination))
    original = Path(entry["source"])
    files = contents(original, entry["name"])
    if fingerprint(files) != entry["sha256"]:
        raise SetupError("Source Skill changed since approval; create a new plan")
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    assert_no_links(destination, scope_root)
    temporary = Path(tempfile.mkdtemp(prefix=".codex-practices-", dir=parent))
    try:
        for relative, data in files.items():
            path = temporary / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
        if destination.exists() or destination.is_symlink():
            raise SetupError("Install destination changed; manual review required")
        os.rename(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def install(project_arg: str, spec: str, expected_sha: str, confirmation: str) -> dict:
    if confirmation != CONFIRM_INSTALL or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        raise SetupError("Installation needs explicit confirmation and plan SHA-256")
    plan = build_plan(project_arg, spec)
    if plan["plan_sha256"] != expected_sha:
        raise SetupError("Plan changed; review current preview and confirm again")
    blockers = [x for x in plan["modules"] if x["status"] in ("conflict", "unavailable")]
    if blockers:
        raise SetupError("Plan has conflicts/unavailable modules: " +
                         ", ".join(str(x["module"]) for x in blockers))
    root = state_dir()
    ensure_private_state(root)
    lockpath = root / ".lock"
    if lockpath.is_symlink():
        raise SetupError("Symlinked installer lock")
    with lockpath.open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            # Re-evaluate AFTER locking to avoid proceeding with stale scope state.
            current = build_plan(project_arg, spec)
            if current["plan_sha256"] != expected_sha:
                raise SetupError("Plan changed during installation; no writes performed")
            record = {
                "version": 1, "project": current["project"],
                "plan_sha256": expected_sha, "status": "applying", "created": []
            }
            manifest = root / (uuid.uuid4().hex + ".json")
            write_json(manifest, record)
            try:
                for entry in current["modules"]:
                    if entry["status"] != "create":
                        continue
                    create_skill(entry, Path(current["project"]), package_root())
                    record["created"].append({
                        "module": entry["module"], "name": entry["name"],
                        "scope": entry["scope"], "destination": entry["destination"],
                        "sha256": entry["sha256"]
                    })
                    write_json(manifest, record)
            except Exception:
                record["status"] = "partial_manual_review"
                write_json(manifest, record)
                raise
            record["status"] = "applied"
            write_json(manifest, record)
            return {
                "status": "applied", "manifest": str(manifest),
                "created": [x["module"] for x in record["created"]],
                "unchanged": [x["module"] for x in current["modules"] if x["status"] == "unchanged"],
                "guided_setup_required": True,
                "tests_run": False,
            }
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def rollback(project_arg: str, manifest_arg: str, confirmation: str) -> dict:
    if confirmation != CONFIRM_ROLLBACK:
        raise SetupError("Rollback requires explicit confirmation")
    root = state_dir()
    if not root.is_dir() or root.is_symlink():
        raise SetupError("Private installer state not found")
    manifest = Path(manifest_arg).expanduser().absolute()
    if manifest.parent != root or manifest.is_symlink() or not manifest.name.endswith(".json"):
        raise SetupError("Only a manifest created in installer state can be used")
    lockpath = root / ".lock"
    if lockpath.is_symlink():
        raise SetupError("Symlinked installer lock")
    with lockpath.open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            record = json.loads(manifest.read_text(encoding="utf-8"))
            project, global_root, local_root = paths(project_arg, package_root())
            if record.get("version") != 1 or record.get("project") != str(project):
                raise SetupError("Manifest does not match this project")
            if record.get("status") not in ("applied", "partial_manual_review"):
                raise SetupError("Manifest already rolled back or invalid")
            created = record.get("created")
            if not isinstance(created, list):
                raise SetupError("Invalid rollback manifest")
            # Validate ALL destinations before deleting ANYTHING.
            destinations = []
            for entry in created:
                n = entry["module"]
                if type(n) is not int or n not in MODULES:
                    raise SetupError("Unknown rollback module")
                _, name, scope = MODULES[n]
                base = global_root if scope == "global" else local_root
                target = base / name
                if (entry["name"], entry["scope"], entry["destination"]) != (name, scope, str(target)):
                    raise SetupError("Rollback target mismatch")
                assert_no_links(target, Path.home().resolve() if scope == "global" else project)
                if fingerprint(contents(target, name)) != entry["sha256"]:
                    raise SetupError("Installed Skill changed; cannot remove automatically: " + str(target))
                destinations.append(target)
            for destination in reversed(destinations):
                shutil.rmtree(destination)
            record["status"] = "rolled_back"
            write_json(manifest, record)
            return {"status": "rolled_back", "removed": [str(x) for x in destinations],
                    "note": "Previously existing Skills and AGENTS/config files were never modified"}
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Confirmed target project, NOT package folder")
    parser.add_argument("--modules", default="available",
                        help="'available' (default), 'all', or comma-separated numbers 3..11")
    action = parser.add_subparsers(dest="action", required=True)
    action.add_parser("plan")
    apply_cmd = action.add_parser("apply")
    apply_cmd.add_argument("--expected-plan-sha", required=True)
    apply_cmd.add_argument("--confirm", required=True)
    action.add_parser("wizard")
    back = action.add_parser("rollback")
    back.add_argument("--manifest", required=True)
    back.add_argument("--confirm", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "plan":
            result = build_plan(args.project, args.modules)
        elif args.action == "apply":
            result = install(args.project, args.modules, args.expected_plan_sha, args.confirm)
        elif args.action == "wizard":
            if not sys.stdin.isatty():
                raise SetupError("Wizard requires an interactive terminal")
            available = present_modules(package_root())
            print("Available modules in this checkout: " + ", ".join(map(str, available)))
            choice = input("Select comma-separated modules [default: " + args.modules + "]: ").strip()
            spec = choice or args.modules
            current = build_plan(args.project, spec)
            print(json.dumps(current, ensure_ascii=False, indent=2))
            if any(x["status"] in ("conflict", "unavailable") for x in current["modules"]):
                raise SetupError("Resolve plan conflicts/missing modules first")
            answer = input("Type " + CONFIRM_INSTALL + " to install listed Skills: ")
            result = install(args.project, spec, current["plan_sha256"], answer.strip())
        else:
            result = rollback(args.project, args.manifest, args.confirm)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (SetupError, OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
