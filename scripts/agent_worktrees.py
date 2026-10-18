#!/usr/bin/env python3
"""Conservative, local Git worktree lifecycle for independently launched Codex workers.

No Codex/model calls, network, background process, force deletion, or protected-branch writes.
Requires Python 3.10+ and Git. This helper does not enforce process sandboxing.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,39}$")


class Failure(Exception):
    pass


def git(root, *args, check=True):
    p = subprocess.run(["git", "-C", str(root), "-c", "core.hooksPath=/dev/null", *args],
                       text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode:
        raise Failure(f"git {' '.join(args)}: {p.stderr.strip() or p.stdout.strip()}")
    return p


def name(value):
    if not ID.fullmatch(value):
        raise Failure("IDs must be 1-40 letters, digits, underscores or hyphens; start with a letter/digit")
    return value


def root_for(path):
    p = Path(path).expanduser().resolve(strict=True)
    top = git(p, "rev-parse", "--show-toplevel").stdout.strip()
    if Path(top).resolve() != p:
        raise Failure("--repo must identify the actual Git repository root")
    if git(p, "rev-parse", "--is-bare-repository").stdout.strip() != "false":
        raise Failure("Bare repositories are not supported")
    return p


def clean(path, include_ignored=False):
    args = ["status", "--porcelain=v1", "--untracked-files=all"]
    if include_ignored:
        args.append("--ignored")
    return not git(path, *args).stdout.strip()


def workspace(repo):
    parent = repo.parent / f".{repo.name}-codex-worktrees"
    if parent.is_symlink():
        raise Failure("Workspace root must not be a symlink")
    if parent.exists() and not parent.is_dir():
        raise Failure("Workspace root is not a directory")
    return parent


def paths(repo, run):
    base = workspace(repo)
    return base / run, base / run / "manifest.json"


def manifest(repo, run):
    run_dir, path = paths(repo, run)
    if run_dir.is_symlink() or path.is_symlink():
        raise Failure("Refusing symlinked run or manifest")
    if not path.is_file():
        raise Failure("Run not found; refusing to guess branch or worktree ownership")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or data.get("repo") != str(repo) or data.get("run") != run:
        raise Failure("Invalid run manifest")
    return data


def save(repo, run, data):
    run_dir, path = paths(repo, run)
    if run_dir.is_symlink() or path.is_symlink():
        raise Failure("Refusing symlinked state path")
    fd, tmp = tempfile.mkstemp(prefix=".manifest-", dir=run_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def get_tree(repo, data, worker):
    entry = data["trees"].get(worker)
    if not entry:
        raise Failure(f"Unknown worker: {worker}")
    branch, path = entry["branch"], Path(entry["path"])
    expected = paths(repo, data["run"])[0] / worker
    if path != expected or path.is_symlink() or not path.is_dir():
        raise Failure(f"Worktree missing or unsafe: {worker}")
    if Path(git(path, "rev-parse", "--show-toplevel").stdout.strip()).resolve() != path.resolve():
        raise Failure("Worktree Git root mismatch")
    if git(path, "symbolic-ref", "--short", "HEAD").stdout.strip() != branch:
        raise Failure("Unexpected branch checked out")
    return path, branch


def head(path):
    return git(path, "rev-parse", "HEAD").stdout.strip()


def prepare(repo, args):
    run = name(args.run)
    workers = [name(w) for w in args.workers]
    if not workers or len(set(workers)) != len(workers) or "integration" in workers:
        raise Failure("Specify distinct workers; 'integration' is reserved")
    if not clean(repo):
        raise Failure("Source checkout is dirty; preserve/reconcile its changes before preparing")
    base_sha = head(repo)
    run_dir, _ = paths(repo, run)
    if run_dir.exists() or run_dir.is_symlink():
        raise Failure("Run already exists; refusing to overwrite")
    planned = {w: {"branch": f"codex-ma/{run}/{w}", "path": str(run_dir / w)} for w in ["integration", *workers]}
    for w, entry in planned.items():
        if git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{entry['branch']}", check=False).returncode == 0:
            raise Failure(f"Branch already exists: {entry['branch']}")
    run_dir.mkdir(parents=True)
    for w, entry in planned.items():
        result = git(repo, "worktree", "add", "-b", entry["branch"], entry["path"], base_sha, check=False)
        if result.returncode:
            raise Failure(f"Prepare interrupted while creating {w}; preserve partial run for manual recovery: {result.stderr.strip()}")
    data = {"version": 1, "repo": str(repo), "run": run, "base": base_sha,
            "trees": planned, "verified": {}, "integrated": [], "integration_head": base_sha}
    save(repo, run, data)
    print(json.dumps({"base": base_sha, "worktrees": planned}, indent=2))


def verify(repo, args):
    data = manifest(repo, name(args.run))
    path, _ = get_tree(repo, data, args.worker)
    if not clean(path):
        raise Failure("Commit or remove all tracked/untracked changes before verification")
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        raise Failure("Supply an actual test command after -- (no shell interpolation)")
    sha = head(path)
    try:
        result = subprocess.run(command, cwd=path, timeout=args.timeout, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise Failure(f"Verification did not complete: {e}") from e
    if result.returncode != 0:
        raise Failure(f"Verification failed (exit {result.returncode}); no receipt issued")
    if head(path) != sha or not clean(path):
        raise Failure("Verification modified the checkout or HEAD; no receipt issued")
    data["verified"][args.worker] = {"sha": sha, "command": command}
    save(repo, data["run"], data)
    print(f"VERIFIED {args.worker} {sha}")


def integrate(repo, args):
    data = manifest(repo, name(args.run))
    target, _ = get_tree(repo, data, "integration")
    if head(target) != data["integration_head"] or not clean(target):
        raise Failure("Integration tree changed outside helper; reconcile manually")
    workers = [name(w) for w in args.workers]
    if not workers or len(set(workers)) != len(workers) or "integration" in workers:
        raise Failure("Specify distinct worker names")
    for w in workers:
        source, _ = get_tree(repo, data, w)
        sha = head(source)
        if not clean(source) or data["verified"].get(w, {}).get("sha") != sha:
            raise Failure(f"Worker {w} is dirty or lacks verification for its current HEAD")
        if w in data["integrated"]:
            raise Failure(f"Worker already integrated: {w}")
    for w in workers:
        branch = data["trees"][w]["branch"]
        result = git(target, "merge", "--no-ff", "--no-edit", branch, check=False)
        if result.returncode:
            git(target, "merge", "--abort", check=False)
            raise Failure(f"Merge of {w} failed; prior merges retained, this worker not integrated: {result.stderr.strip()}")
        data["integrated"].append(w)
        data["integration_head"] = head(target)
        data["verified"].pop("integration", None)
        save(repo, data["run"], data)
        print(f"INTEGRATED {w} into {data['trees']['integration']['branch']}")
    print("Run verify --worker integration -- <test command> before cleanup")


def status(repo, args):
    data = manifest(repo, name(args.run))
    for w in data["trees"]:
        try:
            path, branch = get_tree(repo, data, w)
            sha = head(path)
            verified = data["verified"].get(w, {}).get("sha") == sha
            print(f"{w}: {branch} {sha} verified={verified} clean={clean(path)} path={path}")
        except Failure as e:
            print(f"{w}: UNAVAILABLE ({e})")
    print(f"integrated={','.join(data['integrated']) or '-'}")


def cleanup(repo, args):
    data = manifest(repo, name(args.run))
    target, _ = get_tree(repo, data, "integration")
    target_sha = head(target)
    if (target_sha != data["integration_head"] or
            data["verified"].get("integration", {}).get("sha") != target_sha):
        raise Failure("Integration HEAD has not passed final verification")
    for w in data["trees"]:
        path, branch = get_tree(repo, data, w)
        if not clean(path, include_ignored=True):
            raise Failure(f"{w} contains tracked/untracked/ignored data; refusing cleanup")
        if w != "integration" and git(repo, "merge-base", "--is-ancestor", branch, data["trees"]["integration"]["branch"], check=False).returncode:
            raise Failure(f"{w} contains commits not present in integration branch")
    for w, entry in data["trees"].items():
        git(repo, "worktree", "remove", entry["path"])
        print(f"REMOVED worktree {w}; retained branch {entry['branch']}")
    print(f"Manifest retained: {paths(repo, data['run'])[1]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Absolute or relative Git repository root")
    subs = parser.add_subparsers(dest="action", required=True)
    p = subs.add_parser("prepare")
    p.add_argument("--run", required=True)
    p.add_argument("--workers", nargs="+", required=True)
    p = subs.add_parser("verify")
    p.add_argument("--run", required=True)
    p.add_argument("--worker", required=True)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("command", nargs=argparse.REMAINDER)
    p = subs.add_parser("integrate")
    p.add_argument("--run", required=True)
    p.add_argument("--workers", nargs="+", required=True)
    for action in ("status", "cleanup"):
        p = subs.add_parser(action)
        p.add_argument("--run", required=True)
    args = parser.parse_args()
    try:
        repo = root_for(args.repo)
        {"prepare": prepare, "verify": verify, "integrate": integrate,
         "status": status, "cleanup": cleanup}[args.action](repo, args)
    except (Failure, OSError, ValueError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
