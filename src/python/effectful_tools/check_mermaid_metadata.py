#!/usr/bin/env python3
"""Validate canonical Mermaid diagrams."""

from __future__ import annotations

import sys
from pathlib import Path

from effectful_tools.doc_utils import (
    CanonicalDiagram,
    DOCS_DIR,
    DEMO_DIR,
    anchorize,
    default_arg_parser,
    fenced_blocks,
)


FORBIDDEN_TOKENS = {"==>", "-.->", "subgraph", "Note", "style", "classDef"}


def parse_canonical(path: Path) -> list[CanonicalDiagram]:
    diagrams: list[CanonicalDiagram] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for idx, lang, body in fenced_blocks(lines):
        if lang != "mermaid":
            continue
        content = "\n".join(body)
        # Only check for forbidden tokens if this is a canonical diagram
        if "%% kind" not in content or "%% id" not in content:
            continue
        if any(token in content for token in FORBIDDEN_TOKENS):
            raise ValueError(f"{path}:{idx+1}: forbidden mermaid token in canonical block")
        metadata = {
            line.split(":", 1)[0].strip(): line.split(":", 1)[1].strip()
            for line in body
            if line.strip().startswith("%% ")
        }
        kind = metadata.get("%% kind", "")
        identifier = metadata.get("%% id", "")
        summary = metadata.get("%% summary", "")
        base_id = metadata.get("%% base-id")
        is_demo = path.is_relative_to(DEMO_DIR)
        if is_demo and not base_id:
            raise ValueError(f"{path}:{idx+1}: demo canonical diagram missing %% base-id")
        if not identifier or not kind:
            raise ValueError(f"{path}:{idx+1}: canonical diagram missing kind or id")
        anchor = (
            anchorize(lines[idx - 1].lstrip("#").strip())
            if idx > 0 and lines[idx - 1].startswith("##")
            else ""
        )
        diagrams.append(
            CanonicalDiagram(
                kind=kind,
                identifier=identifier,
                summary=summary,
                path=path,
                anchor=anchor,
                is_demo=is_demo,
                base_id=base_id,
            )
        )
        if kind == "ADT" and (not body or body[0].strip() != "flowchart TB"):
            raise ValueError(f"{path}:{idx+1}: ADT canonical diagrams must start with flowchart TB")
        if kind == "StateMachine" and (not body or body[0].strip() != "stateDiagram-v2"):
            raise ValueError(
                f"{path}:{idx+1}: StateMachine canonical diagrams must start with stateDiagram-v2"
            )
    return diagrams


def main() -> int:
    parser = default_arg_parser("Validate canonical mermaid diagrams.")
    args = parser.parse_args()
    paths = args.paths or list(DOCS_DIR.rglob("*.md")) + list(DEMO_DIR.rglob("documents/**/*.md"))
    errors: list[str] = []
    seen_ids: set[str] = set()
    try:
        for path in paths:
            diagrams = parse_canonical(path)
            for diagram in diagrams:
                if diagram.identifier in seen_ids:
                    errors.append(f"{path}: duplicate canonical id {diagram.identifier}")
                seen_ids.add(diagram.identifier)
    except ValueError as exc:
        errors.append(str(exc))

    if errors:
        for err in errors:
            print(f"❌ {err}")
        return 1
    print("✅ Mermaid canonical diagrams are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
