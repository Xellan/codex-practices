#!/usr/bin/env python3
"""Consent-gated, minimal pre-Codex permission launcher. Never edits user configuration."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

MODES = {
    "review": "read-only",
    "development": "workspace-write",
    "infrastructure": "workspace-write",
}


def recommend(path):
    names = {p.name.lower() for p in path.iterdir()}
    if names & {"terraform", "ansible", "k8s", "helm", "docker-compose.yml", "docker-compose.yaml"}:
        return "infrastructure"
    if names & {"src", "tests", "pyproject.toml", "package.json", "go.mod", "cargo.toml"}:
        return "development"
    return "review"


def preview(project, profile, broad):
    if broad and profile != "infrastructure":
        raise ValueError("Broad access is only eligible for an explicitly chosen infrastructure profile")
    mode = "danger-full-access" if broad else MODES[profile]
    return ["--cd", str(project), "--sandbox", mode, "--ask-for-approval", "on-request"]


def config_audit():
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    cfg = home / "config.toml"
    if cfg.is_symlink():
        return "config is a symlink: review manually"
    if not cfg.exists():
        return "no user config"
    try:
        with cfg.open("rb") as f:
            data = tomllib.load(f)
        return "config readable; CLI arguments override relevant defaults; managed policy may still restrict"
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return f"config unavailable or invalid: {exc.__class__.__name__}"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", required=True)
    p.add_argument("--profile", choices=MODES)
    p.add_argument("--broad-infra", action="store_true")
    p.add_argument("--launch", action="store_true")
    p.add_argument("--confirm", default="")
    p.add_argument("--codex-bin", default="codex")
    a = p.parse_args(argv)
    try:
        project = Path(a.project).expanduser().resolve(strict=True)
        if not project.is_dir():
            raise ValueError("Project is not a directory")
        suggested = recommend(project)
        # No silent selection: launch needs an explicit profile.
        if a.launch and not a.profile:
            raise ValueError("Choose --profile explicitly before launching")
        profile = a.profile or suggested
        flags = preview(project, profile, a.broad_infra)
        data = {"recommended_profile": suggested, "selected_profile": a.profile,
                "broad_infrastructure": a.broad_infra, "codex_flags": flags,
                "config_audit": config_audit(),
                "limits": "No guarantee on SSH/MCP/root actions; sandbox and managed policy are independent."}
        print(json.dumps(data, ensure_ascii=False, indent=2))
        if not a.launch:
            return 0
        expected = "BROAD_INFRA_THIS_SESSION" if a.broad_infra else "LAUNCH_PROFILE"
        if a.confirm != expected:
            raise ValueError("Launch requires --confirm " + expected)
        binary = shutil.which(a.codex_bin)
        if not binary:
            raise ValueError("Codex executable not found")
        return subprocess.run([binary, *flags], check=False).returncode
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
