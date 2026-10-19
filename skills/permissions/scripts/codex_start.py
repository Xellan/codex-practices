#!/usr/bin/env python3
"""Read-only Codex profile adviser and consent-gated session launcher (Python 3.11+)."""
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
PROFILE_MENU = {"1": "review", "2": "development", "3": "infrastructure"}
RISK_TOKENS = {"high": "HIGH_RISK_REVIEWED", "incomplete": "INCOMPLETE_SCAN_REVIEWED"}


def recommend(path):
    """Use directory entries only; never execute project metadata."""
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
    """Inspect selected local config files; NEVER report secrets or claim effective runtime policy."""
    root = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
    configs = [("user", root / "config.toml")]
    if project is not None:
        configs.append(("project", Path(project) / ".codex" / "config.toml"))
    audit = {"scope": "partial: selected TOML files only; managed/system/CLI/runtime policy not verified",
             "files": [], "warnings": [], "errors": []}
    for label, path in configs:
        record = {"scope": label, "present": False}
        if (label == "project" and path.parent.is_symlink()) or path.is_symlink():
            audit["errors"].append(label + " config uses a symlink; manual inspection required")
            audit["files"].append(record)
            continue
        if not path.exists():
            audit["files"].append(record)
            continue
        record["present"] = True
        try:
            with path.open("rb") as f:
                cfg = tomllib.load(f)
            if not isinstance(cfg, dict):
                raise ValueError("invalid config structure")
            # Fixed allowlist; no strings, paths, MCP settings or environment values emitted.
            record["contains_legacy_sandbox"] = "sandbox_mode" in cfg
            record["contains_permission_profiles"] = any(k in cfg for k in ("permissions", "default_permissions", "permission_profiles"))
            record["contains_approval_policy"] = "approval_policy" in cfg
            if record["contains_legacy_sandbox"] and record["contains_permission_profiles"]:
                audit["warnings"].append(label + " config mixes sandbox_mode with permission settings; inspect precedence")
            if record["contains_permission_profiles"]:
                audit["warnings"].append(label + " config declares permission settings; CLI flags do not prove final runtime permissions")
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            audit["errors"].append(label + " config could not be audited: " + type(exc).__name__)
        audit["files"].append(record)
    if any(f["scope"] == "project" and f["present"] for f in audit["files"]):
        audit["warnings"].append("Project configuration may be applied in trusted repositories; verify effective policy inside Codex")
    return audit


def inspect_external(project):
    """Reuse optional #5 scanner; malformed scanner output never becomes 'clean'."""
    scan_path = Path(__file__).resolve().parents[2] / "external-guardrails/scripts/external_scan.py"
    if not scan_path.is_file() or scan_path.is_symlink():
        return {"risk": "unavailable", "incomplete": True, "notes": "external scanner not installed"}
    try:
        result = subprocess.run([sys.executable, str(scan_path), "--root", str(project)],
                                capture_output=True, text=True, timeout=15, check=False)
        if result.returncode not in (0, 3):
            raise ValueError("external scanner failed")
        data = json.loads(result.stdout)
        if not isinstance(data, dict) or data.get("risk") not in ("low", "medium", "high"):
            raise ValueError("invalid external scanner result")
        return {"risk": data["risk"], "incomplete": bool(data.get("truncated") or data.get("skipped")),
                "findings_count": len(data.get("findings", []))}
    except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
        raise ValueError("external preflight could not complete: " + type(exc).__name__) from exc


def resolve_binary(command):
    binary = shutil.which(command)
    if not binary:
        raise ValueError("Codex executable not found")
    return binary


def check_cli(binary):
    """Only Codex --help, no model calls. Verify exact flags before the session starts."""
    try:
        proc = subprocess.run([binary, "--help"], capture_output=True, text=True,
                              timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Codex CLI help probe failed: " + type(exc).__name__) from exc
    output = proc.stdout + "\n" + proc.stderr
    if proc.returncode != 0 or not all(flag in output for flag in ("--sandbox", "--ask-for-approval", "--cd")):
        raise ValueError("Installed CLI does not confirm required flags; launch refused")


def build_report(project, suggested, profile, broad, config, scan):
    selected = profile or suggested
    return {
        "recommended_profile": suggested,
        "selected_profile": profile,
        "broad_infrastructure": broad,
        "codex_flags": preview(project, selected, broad),
        "config_audit": config,
        "external_scan_risk": scan["risk"],
        "external_scan_incomplete": scan["incomplete"],
        "critical_actions": "NOT_ENFORCED: a broad shell/SSH/MCP/root session can execute destructive actions without a separate approval gate",
        "limits": "This is a local CLI preflight, not effective-policy attestation, credential isolation or a sandbox for remote tools.",
    }


def require_acks(scan, accepted):
    required = []
    if scan["risk"] == "high":
        required.append(RISK_TOKENS["high"])
    if scan["incomplete"]:
        required.append(RISK_TOKENS["incomplete"])
    missing = sorted(set(required).difference(accepted))
    if missing:
        raise ValueError("Preflight requires separate acknowledgement: " + ", ".join(missing))


def interactive_choice(suggested, provided):
    print("Profiles: [1] Review (read-only), [2] Development (workspace-write), [3] Infrastructure", file=sys.stderr)
    print("Recommended: " + suggested, file=sys.stderr)
    answer = input("Select 1/2/3 [Enter for recommended]: ").strip().lower()
    profile = PROFILE_MENU.get(answer, answer or suggested)
    if profile not in MODES:
        raise ValueError("Unrecognized profile")
    if provided and profile != provided:
        raise ValueError("Selected profile differs from explicit --profile; remove --profile to choose freely")
    broad = False
    if profile == "infrastructure":
        broad = input("Broad, unsandboxed infrastructure session? Type BROAD to enable, Enter for restricted: ").strip() == "BROAD"
    return profile, broad


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--profile", choices=MODES)
    parser.add_argument("--broad-infra", action="store_true")
    parser.add_argument("--interactive", action="store_true", help="TTY profile selection and launch with explicit approvals")
    parser.add_argument("--launch", action="store_true", help="Non-interactive launch with explicit profile and confirmation")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--risk-ack", action="append", default=[], help="Repeat for each preflight acknowledgement")
    args = parser.parse_args(argv)
    try:
        project = Path(args.project).expanduser().resolve(strict=True)
        if not project.is_dir():
            raise ValueError("Project is not a directory")
        suggested = recommend(project)
        if args.interactive and (args.launch or args.broad_infra or args.confirm or args.risk_ack):
            raise ValueError("--interactive cannot be combined with launch flags or acknowledgement tokens")
        if args.interactive and (not sys.stdin.isatty() or not sys.stdout.isatty()):
            raise ValueError("Interactive launch requires a real TTY")
        if args.launch and not args.profile:
            raise ValueError("Choose --profile explicitly before launching")
        profile = args.profile
        broad = args.broad_infra
        if args.interactive:
            profile, broad = interactive_choice(suggested, args.profile)
        config = config_audit(project)
        scan = inspect_external(project)
        report = build_report(project, suggested, profile, broad, config, scan)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not args.launch and not args.interactive:
            return 0
        # Configuration defects fail closed when attempting to launch; preview stays informative.
        if config["errors"]:
            raise ValueError("Configuration audit found errors; launch refused until resolved")
        accepted = list(args.risk_ack)
        if args.interactive:
            if scan["risk"] == "high":
                print("HIGH-RISK external instructions found; no source is trusted by this scan.", file=sys.stderr)
                accepted.append(input("Type HIGH_RISK_REVIEWED to continue: ").strip())
            if scan["incomplete"]:
                print("External scan is incomplete or unavailable.", file=sys.stderr)
                accepted.append(input("Type INCOMPLETE_SCAN_REVIEWED to continue: ").strip())
        require_acks(scan, accepted)
        expected = "BROAD_INFRA_THIS_SESSION" if broad else "LAUNCH_PROFILE"
        if args.interactive:
            if broad:
                print("WARNING: danger-full-access cannot guarantee critical-action approval for SSH/MCP/shell.", file=sys.stderr)
            confirmed = input("Type " + expected + " to launch: ").strip()
        else:
            confirmed = args.confirm
        if confirmed != expected:
            raise ValueError("Launch requires --confirm " + expected)
        binary = resolve_binary(args.codex_bin)
        check_cli(binary)
        return subprocess.run([binary, *report["codex_flags"]], check=False).returncode
    except (ValueError, OSError, EOFError, KeyboardInterrupt) as exc:
        print("ERROR: " + ("Cancelled" if isinstance(exc, (KeyboardInterrupt, EOFError)) else str(exc)), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
