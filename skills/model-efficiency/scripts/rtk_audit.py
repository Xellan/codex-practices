#!/usr/bin/env python3
"""Compare SAVED raw and RTK command outputs; never execute or rewrite commands."""
import argparse
import json
from pathlib import Path
import re
import sys

SIGNALS = re.compile(r"\b(error|fatal|failed|failure|warning|warn|denied|timeout|timed out|traceback|panic|critical)\b", re.I)


def read(path):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 2_000_000:
        raise ValueError("Input must be a regular, non-symlink file of <= 2 MB")
    return p.read_text(encoding="utf-8")


def exact_structure_equal(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(exact_structure_equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(exact_structure_equal(x, y) for x, y in zip(left, right))
    return left == right


def audit(raw, compact, raw_rc, compact_rc):
    result = {"raw_bytes": len(raw.encode()), "compressed_bytes": len(compact.encode())}
    if raw_rc != compact_rc:
        result.update(status="reject", reason="Exit code changed")
        return result
    if raw == compact:
        result.update(status="identical", reason="Byte-identical output")
        return result
    # JSON can be reformatted, but must preserve exact parsed values, lists and keys.
    try:
        a, b = json.loads(raw), json.loads(compact)
    except (ValueError, TypeError):
        pass
    else:
        if exact_structure_equal(a, b):
            result.update(status="equivalent_json", reason="Same parsed JSON value")
            return result
        result.update(status="reject", reason="Parsed JSON data changed")
        return result
    raw_signals = SIGNALS.findall(raw)
    compact_signals = SIGNALS.findall(compact)
    if len(compact_signals) < len(raw_signals):
        result.update(status="reject", reason="Diagnostic signal(s) may be missing")
        return result
    if not compact.strip() and raw.strip():
        result.update(status="reject", reason="Nonempty output became empty")
        return result
    result.update(status="review_required", reason="Text changed: manual completeness and semantic review required")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", required=True)
    p.add_argument("--compressed", required=True)
    p.add_argument("--raw-rc", type=int, required=True)
    p.add_argument("--compressed-rc", type=int, required=True)
    args = p.parse_args(argv)
    try:
        result = audit(read(args.raw), read(args.compressed), args.raw_rc, args.compressed_rc)
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in ("identical", "equivalent_json") else 1


if __name__ == "__main__":
    raise SystemExit(main())
