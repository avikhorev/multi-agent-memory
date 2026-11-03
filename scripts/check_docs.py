"""Offline checks for hand-written Markdown docs and pinned source links.

Checks:
  - local Markdown/image paths and heading/explicit-id fragments;
  - GitHub source URLs pinned to commits of this repository (file and line range);
  - `make <target>` commands mentioned in documentation against Makefile targets.

External links are intentionally not fetched. Generated results/ Markdown is not linted.
Run from any directory: python3 scripts/check_docs.py
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
MD_LINK = re.compile(r"!?\[[^\]\n]*\]\((<[^>]+>|[^)\n]+)\)")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
EXPLICIT_ANCHOR = re.compile(r'<a\s+id=["\']([^"\']+)["\']\s*></a>')
MAKE_CALL = re.compile(r"\bmake\s+(?:-[a-zA-Z]+\s+)*([a-zA-Z][a-zA-Z0-9_-]*)\b")
MAKE_TARGET = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)(?:\s+[A-Za-z][A-Za-z0-9_-]*)*\s*:")
PINNED_URL = re.compile(
    r"^https://github\.com/avikhorev/multi-agent-memory/blob/"
    r"(?P<ref>[a-fA-F0-9]{7,40})/(?P<path>[^#?]+)(?:#(?P<anchor>[^?]+))?$"
)
MERMAID_URL = re.compile(r'\bclick\s+\S+\s+href\s+"(https?://[^\"]+)"')
LINE_ANCHOR = re.compile(r"^L(?P<start>[1-9][0-9]*)(?:-L(?P<end>[1-9][0-9]*))?$")


def markdown_files(root: Path) -> list[Path]:
    return sorted([*root.glob("*.md"), *(root / "docs").rglob("*.md")])


def visible_lines(source: str):
    """Return each Markdown line with a flag for fenced code blocks."""
    fence_char = None
    fence_length = 0
    for line in source.splitlines():
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fence_char is None:
                fence_char, fence_length = marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char, fence_length = None, 0
            yield line, False
        else:
            yield line, fence_char is None


def slug(text: str) -> str:
    """Approximate GitHub's Unicode-friendly heading-slug algorithm."""
    text = re.sub(r"<[^>]*>", "", text).replace("`", "")
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.strip().strip("#").strip().lower()
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def anchors_in(text: str) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for line, visible in visible_lines(text):
        if not visible:
            continue
        anchors.update(EXPLICIT_ANCHOR.findall(line))
        heading = HEADING.match(line)
        if heading:
            base = slug(heading.group(1))
            suffix = counts.get(base, 0)
            anchors.add(f"{base}-{suffix}" if suffix else base)
            counts[base] = suffix + 1
    return anchors


def is_within(path: Path, root: Path) -> bool:
    return path.is_relative_to(root.resolve())


def line_error(anchor: str, lines: int) -> str | None:
    match = LINE_ANCHOR.fullmatch(anchor)
    if not match:
        return f"unknown source-line anchor #{anchor}"
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    if end < start or end > lines:
        return f"line range #{anchor} is outside 1..{lines}"
    return None


def check_local(link: str, source: Path, root: Path, anchors: dict[Path, set[str]]) -> str | None:
    parsed = urlsplit(link)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path)
    # Skip URL-only anchors to the current file, but validate the heading.
    target = (source.parent / path).resolve() if path else source.resolve()
    if not is_within(target, root):
        return f"path escapes repository: {link}"
    if not target.exists():
        return f"missing target: {link}"
    fragment = unquote(parsed.fragment)
    if not fragment:
        return None
    if target.is_dir():
        return f"directory has no anchor #{fragment}: {link}"
    if target.suffix.lower() == ".md":
        if target not in anchors:
            anchors[target] = anchors_in(target.read_text(encoding="utf-8"))
        if fragment not in anchors[target]:
            return f"unknown Markdown anchor #{fragment}: {link}"
        return None
    if fragment.startswith("L"):
        return line_error(fragment, len(target.read_text(encoding="utf-8").splitlines()))
    return f"unrecognized non-Markdown anchor: {link}"


def check_pinned(link: str, root: Path, cache: dict[tuple[str, str], list[str] | None]) -> str | None:
    match = PINNED_URL.fullmatch(link)
    if not match:
        return None
    ref, path, anchor = match.group("ref"), unquote(match.group("path")), match.group("anchor")
    if path.startswith("/") or ".." in Path(path).parts:
        return f"invalid pinned path: {link}"
    key = ref, path
    if key not in cache:
        git = subprocess.run(["git", "-C", str(root), "show", f"{ref}:{path}"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        cache[key] = git.stdout.splitlines() if git.returncode == 0 else None
    lines = cache[key]
    if lines is None:
        return f"missing pinned snapshot (CI needs fetch-depth: 0): {link}"
    if not anchor:
        return None
    if anchor.startswith("L"):
        return line_error(anchor, len(lines))
    if path.endswith(".md"):
        if anchor not in anchors_in("\n".join(lines)):
            return f"unknown heading in pinned snapshot #{anchor}: {link}"
    return None


def make_targets(root: Path) -> set[str]:
    targets = set()
    for line in (root / "Makefile").read_text(encoding="utf-8").splitlines():
        if line.startswith("\t") or line.lstrip().startswith("#"):
            continue
        match = MAKE_TARGET.match(line)
        if match:
            # Supports the simple single-target recipes in this project's Makefile.
            targets.add(match.group(1))
    return targets


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    anchors: dict[Path, set[str]] = {}
    snapshot_cache: dict[tuple[str, str], list[str] | None] = {}
    targets = make_targets(root)
    for path in markdown_files(root):
        source = path.read_text(encoding="utf-8")
        for lineno, (line, visible) in enumerate(visible_lines(source), 1):
            for cmd in MAKE_CALL.findall(line):
                if cmd not in targets:
                    errors.append(f"{path.relative_to(root)}:{lineno}: unknown make target: {cmd}")
            urls = [m.group(1) for m in MD_LINK.finditer(line)] if visible else []
            # Mermaid click directives are links but not Markdown links; check them too.
            urls.extend(MERMAID_URL.findall(line))
            for raw in urls:
                url = raw.strip().strip("<>").split(' "', 1)[0]
                if url.startswith(("http://", "https://")):
                    error = check_pinned(url, root, snapshot_cache)
                elif url.startswith(("mailto:", "data:")):
                    continue
                else:
                    error = check_local(url, path, root, anchors)
                if error:
                    errors.append(f"{path.relative_to(root)}:{lineno}: {error}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        errors = validate(root)
    except (OSError, UnicodeError) as exc:
        parser.exit(1, f"Docs check failed: {exc}\n")
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"Documentation: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"Documentation: OK ({len(markdown_files(root))} Markdown files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
