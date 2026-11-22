#!/usr/bin/env python3
# Copyright 2026 Barkha Gvalani
# SPDX-License-Identifier: Apache-2.0
"""Deterministic helpers for the readme-explainer skill.

Standard library only, so every host computes the same hashes.

Commands:
  version
  classify FILE
      Prints JSON describing what is at FILE: free, human, unreadable,
      edited, pending or owned.
  fingerprint --root DIR [--readme PATH]... [--child PATH]... [--extra PATH]...
      Prints the sha256 fingerprint of an explainer's inputs.
  stamp FILE --root DIR --source PATH (--pending | --fingerprint HEX)
      Replaces FILE's footer with a fresh one whose output hash matches
      the file. Writes FILE.
  check FILE
      Checks relative links and Mermaid diagram types. Prints JSON and
      exits 1 when a problem is found.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

VERSION = "1"
TOOL = "readme-explainer"

FOOTER_RE = re.compile(
    r"^<!-- readme-explainer v(?P<version>\d+) source: (?P<source>.+?) "
    r"fingerprint:(?P<fingerprint>PENDING|sha256:[0-9a-f]{64}) "
    r"output:sha256:(?P<output>[0-9a-f]{64}) -->$"
)
FOOTER_HINT = "<!-- readme-explainer"

ALLOWED_MERMAID = (
    "flowchart",
    "graph",
    "stateDiagram-v2",
    "sequenceDiagram",
    "timeline",
)

LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def normalize(text: str) -> str:
    """Normalize text so formatting noise does not change a hash."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def split_footer(text: str) -> tuple[str, str | None]:
    """Return (body, footer_line). footer_line is None if the last line is not a footer."""
    lines = normalize(text).rstrip("\n").split("\n")
    if lines and lines[-1].startswith(FOOTER_HINT):
        return "\n".join(lines[:-1]), lines[-1]
    return "\n".join(lines), None


def output_hash(body: str) -> str:
    return sha256(normalize(body))


def file_hash(path: Path) -> str:
    """Hash of a source file, or of an explainer's body without its footer."""
    body, _ = split_footer(read_text(path))
    return output_hash(body)


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def classify(path: Path) -> dict:
    if not path.exists():
        return {"state": "free"}
    text = read_text(path)
    body, footer = split_footer(text)
    if footer is None:
        if FOOTER_HINT in text:
            return {"state": "unreadable", "reason": "footer is not on the last line"}
        return {"state": "human"}
    match = FOOTER_RE.match(footer)
    if not match:
        return {"state": "unreadable", "reason": "footer cannot be parsed"}
    info = {
        "source": match["source"],
        "fingerprint": match["fingerprint"],
        "version": match["version"],
    }
    if match["output"] != output_hash(body):
        return {"state": "edited", **info}
    if match["fingerprint"] == "PENDING":
        return {"state": "pending", **info}
    return {"state": "owned", **info}


def fingerprint(root: Path, readmes: list[str], children: list[str], extras: list[str]) -> str:
    records = [f"template v{VERSION}"]
    for kind, paths in (("readme", readmes), ("child", children), ("extra", extras)):
        for item in paths:
            path = Path(item)
            if not path.is_absolute():
                path = root / path
            if not path.exists():
                raise FileNotFoundError(f"input not found: {item}")
            records.append(f"{kind} {file_hash(path)} {rel(path, root)}")
    records.sort(key=lambda r: r.encode("utf-8"))
    return "sha256:" + sha256("\n".join(records) + "\n")


def stamp(path: Path, source: str, fp: str) -> dict:
    body, _ = split_footer(read_text(path))
    body = normalize(body).rstrip("\n")
    footer = (
        f"<!-- {TOOL} v{VERSION} source: {source} fingerprint:{fp} "
        f"output:sha256:{output_hash(body)} -->"
    )
    path.write_text(body + "\n\n" + footer + "\n", encoding="utf-8")
    return classify(path)


def check(path: Path) -> dict:
    text = read_text(path)
    problems = []
    in_fence = False
    fence_lang = ""
    first_line_pending = False
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_fence:
                in_fence = True
                fence_lang = stripped[3:].strip()
                first_line_pending = fence_lang == "mermaid"
            else:
                in_fence = False
                first_line_pending = False
            continue
        if in_fence:
            if first_line_pending and stripped:
                first_line_pending = False
                kind = stripped.split()[0]
                if kind not in ALLOWED_MERMAID:
                    problems.append(
                        {"line": number, "problem": f"Mermaid type '{kind}' is not allowed"}
                    )
            continue
        for target in LINK_RE.findall(line):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
                continue
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            if not (path.parent / target_path).exists():
                problems.append({"line": number, "problem": f"broken link: {target}"})
    if in_fence:
        problems.append({"line": None, "problem": "code block is not closed"})
    return {"file": str(path), "ok": not problems, "problems": problems}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="explainer_tool.py")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("version")

    p_classify = sub.add_parser("classify")
    p_classify.add_argument("file")

    p_fp = sub.add_parser("fingerprint")
    p_fp.add_argument("--root", required=True)
    p_fp.add_argument("--readme", action="append", default=[])
    p_fp.add_argument("--child", action="append", default=[])
    p_fp.add_argument("--extra", action="append", default=[])

    p_stamp = sub.add_parser("stamp")
    p_stamp.add_argument("file")
    p_stamp.add_argument("--root", required=True)
    p_stamp.add_argument("--source", required=True)
    group = p_stamp.add_mutually_exclusive_group(required=True)
    group.add_argument("--pending", action="store_true")
    group.add_argument("--fingerprint")

    p_check = sub.add_parser("check")
    p_check.add_argument("file")

    args = parser.parse_args(argv)

    if args.command == "version":
        print(f"{TOOL} tool v{VERSION}")
        return 0
    if args.command == "classify":
        print(json.dumps(classify(Path(args.file))))
        return 0
    if args.command == "fingerprint":
        try:
            print(fingerprint(Path(args.root), args.readme, args.child, args.extra))
        except FileNotFoundError as err:
            print(str(err), file=sys.stderr)
            return 2
        return 0
    if args.command == "stamp":
        if args.fingerprint and not re.fullmatch(r"sha256:[0-9a-f]{64}", args.fingerprint):
            print("fingerprint must look like sha256:<64 hex>", file=sys.stderr)
            return 2
        source = rel(Path(args.root) / args.source, Path(args.root))
        fp = "PENDING" if args.pending else args.fingerprint
        print(json.dumps(stamp(Path(args.file), source, fp)))
        return 0
    if args.command == "check":
        result = check(Path(args.file))
        print(json.dumps(result))
        return 0 if result["ok"] else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
