from __future__ import annotations

import sys
from pathlib import Path

from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from tools import (
    check_demo_docs,
    check_doc_code_blocks,
    check_doc_headers,
    check_doc_links,
    check_mermaid_metadata,
    run_doc_checks,
)


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_check_demo_docs_requires_base_link(
    monkeypatch: MonkeyPatch, tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    docs_dir = tmp_path / "documents"
    demo_dir = tmp_path / "demo"
    base_doc = docs_dir / "engineering" / "architecture.md"
    overlay = demo_dir / "healthhub" / "documents" / "engineering" / "architecture.md"

    _write_file(base_doc, "# Base\n")
    _write_file(
        overlay,
        "# Architecture\n\n"
        "**Status**: Reference only\n"
        "**Supersedes**: none\n"
        "**Referenced by**: demo/healthhub/documents/readme.md\n\n"
        "> **Purpose**: Overlay doc\n\n"
        "## Deltas\n",
    )

    monkeypatch.setattr(check_demo_docs, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(check_demo_docs, "DEMO_DIR", demo_dir)
    monkeypatch.setattr(sys, "argv", ["prog", str(overlay)])

    assert check_demo_docs.main() == 1
    output = capsys.readouterr().out
    assert "missing Base Standard link" in output


def test_check_demo_docs_passes_with_base_link(
    monkeypatch: MonkeyPatch, tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    docs_dir = tmp_path / "documents"
    demo_dir = tmp_path / "demo"
    base_doc = docs_dir / "engineering" / "architecture.md"
    overlay = demo_dir / "healthhub" / "documents" / "engineering" / "architecture.md"

    _write_file(base_doc, "# Base\n")
    _write_file(
        overlay,
        "# Architecture\n\n"
        "**Status**: Reference only\n"
        "**Supersedes**: none **📖 Base Standard**: "
        "[architecture.md](../../../../documents/engineering/architecture.md)\n"
        "**Referenced by**: demo/healthhub/documents/readme.md\n\n"
        "> **Purpose**: Overlay doc. **📖 Base Standard**: "
        "[architecture.md](../../../../documents/engineering/architecture.md)\n"
        "> **📖 Authoritative Reference**: "
        "[architecture.md](../../../../documents/engineering/architecture.md)\n\n"
        "## Deltas\n"
        "- none\n",
    )

    monkeypatch.setattr(check_demo_docs, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(check_demo_docs, "DEMO_DIR", demo_dir)
    monkeypatch.setattr(sys, "argv", ["prog", str(overlay)])

    assert check_demo_docs.main() == 0
    output = capsys.readouterr().out
    assert "Demo overlays are valid" in output


def test_check_demo_docs_rejects_duplicated_content(
    monkeypatch: MonkeyPatch, tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    docs_dir = tmp_path / "documents"
    demo_dir = tmp_path / "demo"
    base_doc = docs_dir / "engineering" / "architecture.md"
    overlay = demo_dir / "healthhub" / "documents" / "engineering" / "architecture.md"

    base_body = "\n".join([f"Line {i}" for i in range(15)])
    _write_file(
        base_doc,
        "# Base\n\n"
        "**Status**: Authoritative source\n"
        "**Supersedes**: none\n"
        "**Referenced by**: x\n\n"
        "> **Purpose**: Base doc\n\n"
        f"{base_body}\n",
    )
    _write_file(
        overlay,
        "# Architecture\n\n"
        "**Status**: Reference only\n"
        "**Supersedes**: none **📖 Base Standard**: "
        "[architecture.md](../../../../documents/engineering/architecture.md)\n"
        "**Referenced by**: demo/healthhub/documents/readme.md\n\n"
        "> **Purpose**: Overlay doc. **📖 Base Standard**: "
        "[architecture.md](../../../../documents/engineering/architecture.md)\n"
        "> **📖 Authoritative Reference**: "
        "[architecture.md](../../../../documents/engineering/architecture.md)\n\n"
        "## Deltas\n"
        f"{base_body}\n",
    )

    monkeypatch.setattr(check_demo_docs, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(check_demo_docs, "DEMO_DIR", demo_dir)
    monkeypatch.setattr(sys, "argv", ["prog", str(overlay)])

    assert check_demo_docs.main() == 1
    output = capsys.readouterr().out
    assert "duplicates base content" in output


def test_check_doc_headers_requires_authoritative_reference_in_reference_docs(
    tmp_path: Path,
) -> None:
    path = tmp_path / "doc.md"
    _write_file(
        path,
        "# Title\n\n"
        "**Status**: Reference only\n"
        "**Supersedes**: none\n"
        "**Referenced by**: none\n\n"
        "> **Purpose**: Demo doc without authoritative link.\n",
    )
    errors = check_doc_headers.check_header(path, strict=True)
    assert any("Authoritative Reference" in err for err in errors)


def test_check_doc_links_flags_repo_absolute(
    monkeypatch: MonkeyPatch, tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    path = tmp_path / "doc.md"
    _write_file(
        path,
        "# Title\n\n"
        "**Status**: Authoritative source\n"
        "**Supersedes**: none\n"
        "**Referenced by**: none\n\n"
        "> **Purpose**: Links test\n\n"
        "[bad](https://github.com/effectful/effectful)\n"
        "## Cross-References\n"
        "- [self](#title)\n",
    )
    monkeypatch.setattr(sys, "argv", ["prog", str(path)])
    assert check_doc_links.main() == 1
    output = capsys.readouterr().out
    assert "github.com" in output


def test_check_mermaid_metadata_requires_base_id_for_demo(
    monkeypatch: MonkeyPatch, tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    demo_dir = tmp_path / "demo"
    docs_dir = tmp_path / "documents"
    path = demo_dir / "healthhub" / "documents" / "demo.md"
    _write_file(
        path,
        "# Demo\n\n"
        "**Status**: Reference only\n"
        "**Supersedes**: none\n"
        "**Referenced by**: none\n\n"
        "> **Purpose**: Demo\n\n"
        "## Diagram\n"
        "```mermaid\n"
        "flowchart TB\n"
        "  %% kind: ADT\n"
        "  %% id: demo.sample.Result\n"
        "  A --> B\n"
        "```\n"
        "## Deltas\n",
    )
    monkeypatch.setattr(check_mermaid_metadata, "DEMO_DIR", demo_dir)
    monkeypatch.setattr(check_mermaid_metadata, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(sys, "argv", ["prog", str(path)])
    assert check_mermaid_metadata.main() == 1
    output = capsys.readouterr().out
    assert "missing %% base-id" in output


def test_check_doc_code_blocks_forbidden_any(
    monkeypatch: MonkeyPatch, tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    path = tmp_path / "doc.md"
    _write_file(
        path,
        "# Title\n\n"
        "**Status**: Authoritative source\n"
        "**Supersedes**: none\n"
        "**Referenced by**: none\n\n"
        "> **Purpose**: Code blocks\n\n"
        "## Example\n"
        "```python\n"
        "def foo(x: Any) -> None:\n"
        "    return None\n"
        "```\n"
        "## Cross-References\n"
        "- [self](#title)\n",
    )
    monkeypatch.setattr(sys, "argv", ["prog", str(path)])
    assert check_doc_code_blocks.main() == 1
    output = capsys.readouterr().out
    assert "forbidden pattern" in output


def test_run_doc_checks_invokes_all_scripts(monkeypatch: MonkeyPatch) -> None:
    calls: list[list[str]] = []

    class FakeResult:
        returncode = 0

    def fake_run(command: list[str], check: bool = False) -> FakeResult:
        calls.append(list(command))
        return FakeResult()

    class FakeSubprocess:
        def run(self, command: list[str], check: bool = False) -> FakeResult:
            return fake_run(command, check)

    monkeypatch.setattr(run_doc_checks, "subprocess", FakeSubprocess())
    assert run_doc_checks.main() == 0
    assert any("check_doc_headers" in " ".join(call) for call in calls)
