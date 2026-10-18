#!/usr/bin/env python3
"""Choose a subagent model from an explicitly verified allowlist; never edit Codex settings."""
import argparse
import json
from pathlib import Path
import re
import sys

TIERS = ("routine", "balanced", "advanced")
EFFORTS = {"low", "medium", "high", "xhigh"}
MODEL = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,99}$")


def read_catalog(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Catalog must be an existing regular file, not a symlink")
    if path.stat().st_size > 32_768:
        raise ValueError("Catalog exceeds 32 KiB")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"version", "tiers"} or data["version"] != 1:
        raise ValueError("Unsupported catalog schema/version")
    if not isinstance(data["tiers"], dict) or set(data["tiers"]) != set(TIERS):
        raise ValueError("Catalog must provide routine, balanced and advanced tiers")
    for tier in TIERS:
        entries = data["tiers"][tier]
        if not isinstance(entries, list) or len(entries) > 8:
            raise ValueError("Each tier requires an array of at most 8 candidates")
        for entry in entries:
            if (not isinstance(entry, dict) or set(entry) != {"model", "effort"}
                    or not isinstance(entry["model"], str) or not MODEL.fullmatch(entry["model"])
                    or entry["effort"] not in EFFORTS):
                raise ValueError("Invalid model candidate")
    return data["tiers"]


def choose(tier, catalog, available):
    # Never silently reduce the requested assurance tier. Only advance to stronger tiers.
    for current in TIERS[TIERS.index(tier):]:
        for entry in catalog[current]:
            if entry["model"] in available:
                return {"status": "selected", "requested_tier": tier,
                        "selected_tier": current, "model": entry["model"],
                        "reasoning_effort": entry["effort"]}
    return {"status": "inherit", "requested_tier": tier,
            "reason": "No confirmed compatible model; keep parent configuration"}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tier", choices=TIERS, required=True)
    p.add_argument("--catalog", required=True)
    p.add_argument("--available", nargs="*", default=[], help="Models confirmed available for THIS Codex installation")
    args = p.parse_args(argv)
    try:
        if any(not MODEL.fullmatch(s) for s in args.available):
            raise ValueError("Invalid model identifier in --available")
        result = choose(args.tier, read_catalog(args.catalog), set(args.available))
    except (OSError, ValueError, json.JSONDecodeError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
