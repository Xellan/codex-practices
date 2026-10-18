#!/usr/bin/env python3
"""Small, dependency-free handoff writer for codex-practices (not a daemon)."""

import argparse
import contextlib
import fcntl
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

MARKER = "<!-- codex-practices:handoff:v1 -->"
DEFAULT_FILE = "docs/context/HANDOFF.md"


def fail(message: str) -> None:
    raise ValueError(message)


def locate(root_str: str, relative_str: str) -> Path:
    root = Path(root_str).expanduser().resolve(strict=True)
    if not root.is_dir():
        fail("Project root is not a directory")
    relative = Path(relative_str)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts or relative.suffix != ".md":
        fail("--file must be a relative .md path inside the project")
    path = root / relative
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            fail("Refusing symlink in handoff path: " + str(current))
    if path.exists() and not path.is_file():
        fail("Handoff path exists but is not a regular file")
    return path


def sha(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def read_owned(path: Path) -> str | None:
    if not path.exists():
        return None
    data = path.read_text(encoding="utf-8")
    if not data.startswith(MARKER + "\n"):
        fail("Existing handoff is not managed by codex-practices; review it before adopting")
    return data


def branch(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "branch", "--show-current"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        return (result.stdout.strip() if result.returncode == 0 else "") or "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def clean(value: str, limit: int = 2000) -> str:
    single_line = " ".join(value.strip().split())
    if not single_line or len(single_line) > limit:
        fail("Empty or oversized handoff field")
    return single_line


def bullets(items: list[str]) -> str:
    return "\n".join("- " + clean(item) for item in items) if items else "- None recorded"


def render(root: Path, args: argparse.Namespace) -> str:
    goal, next_step = clean(args.goal), clean(args.next_step)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return (
        f"{MARKER}\n# Project Handoff\n\n"
        f"Updated (UTC): {now}\nBranch: {clean(branch(root))}\nStatus: {args.status}\n\n"
        f"## Goal\n{goal}\n\n"
        f"## Completed\n{bullets(args.done)}\n\n"
        f"## Next step\n{next_step}\n\n"
        f"## Blockers\n{bullets(args.blocker)}\n\n"
        f"## Verification\n{bullets(args.check)}\n\n"
        f"## References\n{bullets(args.reference)}\n"
    )


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=".handoff-", suffix=".tmp", delete=False,
        ) as stream:
            temp_name = stream.name
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


@contextlib.contextmanager
def exclusive_parent_lock(parent: Path):
    """Serialize writers on Linux/macOS without creating persistent lock files."""
    parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage one active project handoff, on demand")
    parser.add_argument("--root", required=True, help="Explicit target project root")
    parser.add_argument("--file", default=DEFAULT_FILE, help="Relative handoff path under --root")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show", help="Display handoff and its SHA-256 for safe subsequent saves")
    sub.add_parser("check", help="Validate managed handoff exists and show its SHA-256")
    save = sub.add_parser("save", help="Replace snapshot after a meaningful milestone")
    save.add_argument("--goal", required=True)
    save.add_argument("--next-step", required=True)
    save.add_argument("--status", choices=["active", "blocked", "closed"], default="active")
    save.add_argument("--done", action="append", default=[])
    save.add_argument("--blocker", action="append", default=[])
    save.add_argument("--check", action="append", default=[])
    save.add_argument("--reference", action="append", default=[])
    save.add_argument("--expect-sha", help="Required for overwrite; from show/check output")
    args = parser.parse_args()
    try:
        path = locate(args.root, args.file)
        if args.command in ("show", "check"):
            old = read_owned(path)
            if old is None:
                print("No handoff yet. Create one after the first meaningful milestone.")
                return 3
            print("SHA256:", sha(old))
            print("PATH:", path)
            if args.command == "show":
                print(old, end="")
            return 0
        # Lock and re-check the digest before writing: different sessions must not
        # silently overwrite a newer milestone recorded by another writer.
        with exclusive_parent_lock(path.parent):
            old = read_owned(path)
            if old is not None:
                if not args.expect_sha or args.expect_sha != sha(old):
                    fail("Existing handoff changed or no --expect-sha provided; run show before saving")
            elif args.expect_sha:
                fail("Expected an existing handoff, but none was found")
            data = render(Path(args.root).expanduser().resolve(), args)
            if data == old:
                print("Unchanged:", path)
                return 0
            atomic_write(path, data)
            print("Saved:", path)
            print("SHA256:", sha(data))
            return 0
    except (ValueError, OSError, UnicodeError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
