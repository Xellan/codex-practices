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


def config_audit(project=None):
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    cfg = home / "config.toml"
    candidates = [cfg] + ([project / ".codex" / "config.toml"] if project else [])
    report = []
    for file in candidates:
        if file.is_symlink():
            report.append({"path": str(file), "status": "symlink"})
        elif not file.exists():
            report.append({"path": str(file), "status": "missing"})
        else:
            try:
                with file.open("rb") as f:
                    settings = tomllib.load(f)
                report.append({"path": str(file), "status": "readable",
                               "permission_defaults": {k: settings[k] for k in ("sandbox_mode", "approval_policy") if k in settings}})
            except (OSError, tomllib.TOMLDecodeError):
                report.append({"path": str(file), "status": "invalid"})
    return {"files": report, "effective_permissions_verified": False,
            "warning": "Managed config, SSH, MCP and actual effective permissions require separate verification"}


def _confirm(message, token):
    print(message, file=sys.stderr)
    try:
        response = input("Type " + token + " to proceed (otherwise cancel): ")
    except (EOFError, KeyboardInterrupt):
        raise ValueError("Interactive confirmation cancelled") from None
    if response.strip() != token:
        raise ValueError("Interactive confirmation rejected")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", required=True)
    p.add_argument("--profile", choices=MODES)
    p.add_argument("--broad-infra", action="store_true")
    p.add_argument("--launch", action="store_true")
    p.add_argument("--interactive", action="store_true", help="Prompt for profile and session confirmation")
    p.add_argument("--confirm", default="")
    p.add_argument("--codex-bin", default="codex")
    p.add_argument("--risk-ack", default="")
    a = p.parse_args(argv)
    try:
        project = Path(a.project).expanduser().resolve(strict=True)
        if not project.is_dir():
            raise ValueError("Project is not a directory")
        suggested = recommend(project)
        if a.interactive and not a.launch:
            raise ValueError("--interactive requires --launch")
        if a.interactive and not sys.stdin.isatty():
            raise ValueError("--interactive requires a terminal")
        # No silent selection: launch needs an explicit profile or terminal choice.
        if a.launch and not a.profile and not a.interactive:
            raise ValueError("Choose --profile explicitly before launching")
        profile = a.profile or suggested
        if a.interactive and not a.profile:
            try:
                choice = input("Recommended " + suggested + "; choose review/development/infrastructure (or cancel): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                raise ValueError("Interactive profile selection cancelled") from None
            if choice not in MODES:
                raise ValueError("Profile selection cancelled or invalid")
            profile = choice
        flags = preview(project, profile, a.broad_infra)
        # Optional #5 scanner installed alongside this Skill. Fail closed on scan errors.
        scan_path = Path(__file__).resolve().parents[2] / "external-guardrails/scripts/external_scan.py"
        scan_risk = "unavailable"
        if scan_path.is_file() and not scan_path.is_symlink():
            scan_result = subprocess.run([sys.executable, str(scan_path), "--root", str(project)],
                                         text=True, capture_output=True)
            if scan_result.returncode not in (0, 3):
                raise ValueError("External scanner failed; review environment before launch")
            try:
                scan_risk = json.loads(scan_result.stdout)["risk"]
            except (ValueError, KeyError, TypeError):
                raise ValueError("External scanner produced invalid output")
        if scan_risk not in ("unavailable", "low", "medium", "high"):
            raise ValueError("External scanner returned unknown risk")
        if a.launch and scan_risk == "high" and a.risk_ack != "HIGH_RISK_REVIEWED":
            if a.interactive:
                _confirm("HIGH-risk external instructions detected; inspection alone cannot establish safety.", "HIGH_RISK_REVIEWED")
            else:
                raise ValueError("HIGH-risk external instructions found; review report and pass --risk-ack HIGH_RISK_REVIEWED to continue")
        data = {"recommended_profile": suggested, "selected_profile": a.profile,
                "broad_infrastructure": a.broad_infra, "codex_flags": flags,
                "config_audit": config_audit(project), "external_scan_risk": scan_risk,
                "critical_action_enforcement": "NOT_GUARANTEED",
                "limits": "Broad sandbox cannot guarantee separate approval for critical SSH/MCP/root actions; external controls required."}
        print(json.dumps(data, ensure_ascii=False, indent=2))
        if not a.launch:
            return 0
        audit = data["config_audit"]
        if any(item["status"] in ("symlink", "invalid") for item in audit["files"]):
            raise ValueError("Codex configuration requires manual review before launching")
        expected = "BROAD_INFRA_THIS_SESSION" if a.broad_infra else "LAUNCH_PROFILE"
        if a.interactive:
            _confirm("Review permissions above. Broad access is NOT a critical-operation approval gate.", expected)
        elif a.confirm != expected:
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
