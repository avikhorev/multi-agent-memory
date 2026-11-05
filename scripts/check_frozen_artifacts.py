"""Check hashes of committed research inputs and raw measurements (stdlib only).

The manifest stores one SHA-256 digest per sorted group of files. Files are hashed
individually; each relative path and binary file digest contribute to the group
hash. The checker is read-only and does not fetch data or call a model.

  python3 scripts/check_frozen_artifacts.py
  python3 scripts/check_frozen_artifacts.py --print-current  # inspect for intentional refreeze
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("docs/frozen_artifacts.json")


def group_digest(root: Path, pattern: str) -> tuple[int, str]:
    """SHA256 over sorted (relative POSIX path, SHA256(file bytes)) records."""
    files = sorted(root.glob(pattern))
    digest = hashlib.sha256()
    for path in files:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"not a regular file: {path}")
        # NUL and LF delimiters ensure that paths and file hashes cannot merge.
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\n")
    return len(files), digest.hexdigest()


def validate(root: Path, manifest: dict) -> list[str]:
    errors = []
    if manifest.get("schema") != 1:
        return ["unknown manifest schema (expected 1)"]
    groups = manifest.get("groups")
    if not isinstance(groups, list) or not groups:
        return ["manifest must contain groups"]
    seen = set()
    for row in groups:
        if not isinstance(row, dict):
            errors.append("group is not an object")
            continue
        pattern = row.get("glob")
        if not isinstance(pattern, str) or not pattern or pattern.startswith("/") or ".." in Path(pattern).parts:
            errors.append(f"invalid glob: {pattern!r}")
            continue
        if pattern in seen:
            errors.append(f"duplicate group: {pattern}")
            continue
        seen.add(pattern)
        actual_n, actual_hash = group_digest(root, pattern)
        if actual_n != row.get("files") or actual_hash != row.get("sha256"):
            errors.append(f"{pattern}: expected {row.get('files')} files, SHA256 {row.get('sha256')}; "
                          f"got {actual_n} files, SHA256 {actual_hash}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--print-current", action="store_true", help="show calculated manifest; never overwrite it")
    args = ap.parse_args()
    root = args.root.resolve()
    path = args.manifest if args.manifest.is_absolute() else root / args.manifest
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if args.print_current:
            for group in manifest["groups"]:
                group["files"], group["sha256"] = group_digest(root, group["glob"])
            print(json.dumps(manifest, indent=2, ensure_ascii=False))
            return 0
        errors = validate(root, manifest)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Frozen artifacts: cannot check: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"Frozen artifacts: {error}", file=sys.stderr)
        return 1
    total = sum(row["files"] for row in manifest["groups"])
    print(f"Frozen artifacts: OK ({len(manifest['groups'])} groups, {total} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
