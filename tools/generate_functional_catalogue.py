#!/usr/bin/env python3
"""Generate or check the functional catalogue from canonical mermaid diagrams."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import mdformat

from tools.doc_utils import CanonicalDiagram, DOCS_DIR, DEMO_DIR, anchorize, fenced_blocks


CATALOGUE_PATH = DOCS_DIR / "engineering" / "functional_catalogue.md"
SCRATCH_DIR = Path("/opt/check-docs")
MD_EXTENSIONS = ["gfm"]


def parse_canonical(path: Path) -> list[CanonicalDiagram]:
    diagrams: list[CanonicalDiagram] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for idx, lang, body in fenced_blocks(lines):
        if lang != "mermaid":
            continue
        metadata = {
            line.split(":", 1)[0].strip(): line.split(":", 1)[1].strip()
            for line in body
            if line.strip().startswith("%% ")
        }
        if "%% kind" not in metadata or "%% id" not in metadata:
            continue
        diagrams.append(
            CanonicalDiagram(
                kind=metadata["%% kind"],
                identifier=metadata["%% id"],
                summary=metadata.get("%% summary", ""),
                path=path,
                anchor=anchorize(lines[idx - 1].lstrip("#").strip())
                if idx > 0 and lines[idx - 1].startswith("##")
                else "",
                is_demo=path.is_relative_to(DEMO_DIR),
                base_id=metadata.get("%% base-id"),
            )
        )
    return diagrams


def load_all() -> list[CanonicalDiagram]:
    diagrams: list[CanonicalDiagram] = []
    for path in list(DOCS_DIR.rglob("*.md")) + list(DEMO_DIR.rglob("documents/**/*.md")):
        diagrams.extend(parse_canonical(path))
    return diagrams


def render_table(diagrams: list[CanonicalDiagram]) -> str:
    header = (
        "# Functional Catalogue\n\n"
        "**Status**: Authoritative source\n"
        "**Supersedes**: none\n"
        "**Referenced by**: engineering/architecture.md, engineering/code_quality.md\n\n"
        "> **Purpose**: Generated index of all ADTs and state machines defined in the codebase and documented via Mermaid.\n\n"
        "## Index\n\n"
        "| Kind | ID | Name | Module | Doc |\n"
        "| --- | --- | --- | --- | --- |\n"
    )
    base_dir = CATALOGUE_PATH.parent
    rows = []
    for d in sorted(diagrams, key=lambda x: x.identifier):
        module, _, name = d.identifier.rpartition(".")
        link_target = os.path.relpath(d.path, base_dir)
        if d.anchor:
            link_target = f"{link_target}#{d.anchor}"
        rows.append(
            f"| {d.kind} | {d.identifier} | {name} | {module} | [{d.path.name}]({link_target}) |"
        )
    footer = (
        "\n## Cross-References\n\n"
        "- [Documentation Standards](../documentation_standards.md)\n"
        "- [Architecture](architecture.md#cross-references)\n"
        "- [Code Quality](code_quality.md#cross-references)\n"
    )
    return header + "\n".join(rows) + "\n" + footer


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or check functional catalogue.")
    parser.add_argument("--check", action="store_true", help="Check mode (no write).")
    args = parser.parse_args()

    diagrams = load_all()
    identifiers = [d.identifier for d in diagrams]
    if len(identifiers) != len(set(identifiers)):
        print("❌ Duplicate canonical IDs detected.")
        return 1

    raw_content = "<!-- AUTO-GENERATED FILE. DO NOT EDIT BY HAND. -->\n\n" + render_table(diagrams)
    content = mdformat.text(raw_content, extensions=MD_EXTENSIONS)
    if args.check:
        if not CATALOGUE_PATH.exists():
            print(f"❌ Catalogue missing: {CATALOGUE_PATH}")
            return 1
        if CATALOGUE_PATH.read_text(encoding="utf-8") != content:
            scratch = SCRATCH_DIR / "functional_catalogue.md"
            scratch.parent.mkdir(parents=True, exist_ok=True)
            scratch.write_text(content, encoding="utf-8")
            print(
                f"❌ functional_catalogue.md is out of date. Regenerate (temp written to {scratch})."
            )
            return 1
        print("✅ functional_catalogue.md is up to date.")
        return 0

    CATALOGUE_PATH.write_text(content, encoding="utf-8")
    print(f"✅ Wrote {CATALOGUE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
