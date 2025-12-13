import os
import sys
from pathlib import Path

import pytest

from effectful_tools import check_demo_docs, check_doc_headers, check_mermaid_metadata


def test_check_header_requires_purpose(tmp_path: Path) -> None:
    path = tmp_path / "doc.md"
    path.write_text(
        "# Title\n\n"
        "**Status**: Authoritative source\n"
        "**Supersedes**: none\n"
        "**Referenced by**: none\n\n"
        "Body without purpose\n",
        encoding="utf-8",
    )

    errors = check_doc_headers.check_header(path, strict=True)

    assert any("Purpose" in err for err in errors)


def test_check_header_reference_only_requires_authoritative_reference(tmp_path: Path) -> None:
    path = tmp_path / "doc.md"
    path.write_text(
        "# Title\n\n"
        "**Status**: Reference only\n"
        "**Supersedes**: none\n"
        "**Referenced by**: none\n\n"
        "> **Purpose**: Reference doc missing authoritative pointer.\n",
        encoding="utf-8",
    )

    errors = check_doc_headers.check_header(path, strict=True)

    assert any("Authoritative Reference" in err for err in errors)


def test_demo_overlay_requires_base_link_and_deltas(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    docs_dir = tmp_path / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)
    base_doc = docs_dir / "guide.md"
    base_doc.write_text(
        "# Guide\n\n"
        "**Status**: Authoritative source\n"
        "**Supersedes**: none\n"
        "**Referenced by**: none\n\n"
        "> **Purpose**: Base SSoT.\n",
        encoding="utf-8",
    )

    demo_dir = tmp_path / "demo" / "healthhub" / "documents"
    demo_dir.mkdir(parents=True, exist_ok=True)
    overlay = demo_dir / "guide.md"
    overlay.write_text(
        "# Guide\n\n"
        "**Status**: Reference only\n"
        "**Supersedes**: none\n"
        "**Referenced by**: none\n\n"
        "> **Purpose**: Overlay without base link.\n\n"
        "## Deltas\n\n"
        "- none\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(check_demo_docs, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(check_demo_docs, "DEMO_DIR", tmp_path / "demo")
    monkeypatch.setenv("PYTHONPATH", str(Path.cwd()))
    monkeypatch.setenv("PATH", os.environ.get("PATH", ""))
    monkeypatch.setattr(sys, "argv", ["check_demo_docs"])

    exit_code = check_demo_docs.main()
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "Base Standard link" in out


def test_demo_canonical_mermaid_requires_base_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    docs_dir = tmp_path / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)
    base_doc = docs_dir / "canonical.md"
    base_doc.write_text(
        "# Canonical\n\n"
        "**Status**: Authoritative source\n"
        "**Supersedes**: none\n"
        "**Referenced by**: none\n\n"
        "> **Purpose**: Base canonical diagram.\n\n"
        "## Model\n\n"
        "```mermaid\n"
        "flowchart TB\n"
        "  %% kind: ADT\n"
        "  %% id: core.result.Result\n"
        "  %% summary: Result ADT\n"
        "  Result -->|variant| Ok\n"
        "  Result -->|variant| Err\n"
        "```\n",
        encoding="utf-8",
    )

    demo_dir = tmp_path / "demo" / "healthhub" / "documents"
    demo_dir.mkdir(parents=True, exist_ok=True)
    overlay = demo_dir / "canonical.md"
    overlay.write_text(
        "# Canonical\n\n"
        "**Status**: Reference only\n"
        "**Supersedes**: none\n"
        "**Referenced by**: none\n\n"
        "> **Purpose**: Demo diagram missing base id.\n\n"
        "## Model\n\n"
        "```mermaid\n"
        "flowchart TB\n"
        "  %% kind: ADT\n"
        "  %% id: demo.result.Result\n"
        "  %% summary: Demo Result ADT\n"
        "  Result -->|variant| Ok\n"
        "  Result -->|variant| Err\n"
        "```\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(check_mermaid_metadata, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(check_mermaid_metadata, "DEMO_DIR", tmp_path / "demo")
    monkeypatch.setattr(sys, "argv", ["check_mermaid_metadata"])

    exit_code = check_mermaid_metadata.main()
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "missing %% base-id" in out
