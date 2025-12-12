# Documentation Migration Plan

**Status**: Reference only\
**Supersedes**: none\
**Referenced by**: documentation_standards.md

> **Purpose**: Temporary, progress-tracked plan for migrating the documentation suite from the prior standards to the newly updated Documentation Standards.\
> **📖 Authoritative Reference**: [Documentation Standards](documentation_standards.md)

______________________________________________________________________

## 1. Scope and Objectives

- Bring all docs (including demos) into compliance with the updated standards covering SSoT metadata, naming/layout, canonical Mermaid, and delta-only overlays.
- Expand `poetry run check-code` so it gates both code and docs, running the full Markdown suite and custom validators described in the new standard.
- Close gaps introduced since the previous standards version (e.g., stronger enforcement, canonical diagrams, functional catalogue).

## 2. Baseline Delta (old vs new standard)

- **Tooling**: Old guide hinted at enforcement; new guide mandates `poetry run check-code` to run black, ruff, mypy, formatter, markdownlint, link checker, spell checker (optional), and all custom doc scripts plus functional catalogue check.
- **Metadata**: New guide requires exact header structure (title + Status/Supersedes/Referenced by + Purpose), status values, and Reference-only docs to include an Authoritative Reference line.
- **Naming/layout**: Snake_case enforced; forbidden artifacts enumerated; docs must live under `documents/` or whitelisted roots.
- **Mermaid**: Canonical ADT/state machine diagrams need structured metadata (`%% kind`, `%% id`, base-id for demos), strict DSL, and banning advanced features.
- **Demo overlays**: Must be delta-only, start with Base Standard link, and reference base canon for diagrams.
- **Functional catalogue**: Auto-generated, enforced via generator in check mode; participates in `check-code`.

## 3. Workstreams and Status

- [x] **Check-code expansion**: Update `poetry run check-code` to invoke formatter, markdownlint, link checker, spell checker (optional), and all custom scripts (`check_doc_filenames`, `check_doc_artifacts`, `check_doc_headers`, `check_doc_links`, `check_doc_crossrefs` if present, `check_doc_code_blocks`, `check_mermaid_metadata`, `check_demo_docs`, `generate_functional_catalogue --check`) after black/ruff/mypy. Document the exact command chain and ensure Docker image contains required binaries.
- [x] **Custom script coverage**: Verify each script exists, is wired into the check pipeline, and has failing tests/exit codes when violations occur. Add missing scripts or align behavior with the spec (e.g., Reference-only header rules, demo `base-id` enforcement).
- [x] **Container/tooling validation**: Rebuilt core and HealthHub images via compose, confirmed Poetry installs (with `check`/`test` or `dev`) and verified required tooling versions inside both containers (black, ruff, mypy, mdformat+plugins, pymarkdown, codespell).
- [ ] **Header compliance sweep**: Ensure all Markdown files start with required metadata block and Purpose blockquote; add Cross-References sections to authoritative docs; fix `Referenced by` lists where stale.
- [ ] **Naming/layout cleanup**: Enforce snake_case names (exceptions only for README/AGENTS/CLAUDE), remove/rename noncompliant files, and delete forbidden artifacts in doc directories.
- [ ] **Mermaid canon pass**: Update canonical ADT/state machine diagrams to the required DSL and metadata; remove forbidden syntax; add `base-id` for demo diagrams; validate with `check_mermaid_metadata`.
- [ ] **Demo overlay audit**: For each `demo/*/documents` file, ensure base link at top, delta-only content, and matching filenames; flag or trim duplicated content.
- [ ] **Functional catalogue**: Run/generate catalogue in check mode; ensure IDs are unique and cover all canonical diagrams; integrate regeneration into contributor workflow docs.
- [ ] **Docs cross-linking**: Refresh intra-doc links to match new SSoT locations/anchors; ensure no absolute GitHub links to this repo; add bidirectional links where needed.
- [ ] **Maintenance checklist alignment**: Update CLAUDE/README navigation to reference the new standards and this migration plan until completed; add reminders to run `poetry run check-code` before review.
- [ ] **Validation + sign-off**: After updates, run `poetry run check-code`; capture logs for PR description; freeze this plan once migration completes and remove/replace with a permanent changelog entry.

## 4. Known Risks / Open Questions

- Spell checker scope: decide dictionary/source and whether to enforce or warn.
- Link checker behavior on private/internal endpoints; may need allowlist.
- Demo overlay duplication detection heuristics (warning vs fail).
- Functional catalogue uniqueness across demo/base IDs and any existing collisions.

## 5. Markdown Checker Implementation Plan (detailed)

- **Technology choices (all Poetry-managed to avoid Node dependency)**:

  - Formatter: `mdformat` + plugins (`mdformat-gfm`, `mdformat-frontmatter`, `mdformat-footnote` if needed).
  - Linter: `pymarkdownlnt` (`pymarkdown` CLI) with config to mirror MD0xx rules from the standard; gate via `pymarkdown scan --config .pymarkdown.json .`.
  - Link checker: replace/extend `tools/verify_links.py` with `tools/check_doc_links.py` (anchor-aware, relative-only, forbids repo-absolute GitHub URLs) and optionally `pymarkdown` link validation.
  - Spell checker: `codespell` with repository dictionary; apply to `documents/` and `demo/*/documents/`.
  - Mermaid/headers/filenames/demo overlays/code blocks: implement as Python scripts under `tools/` per standard names; prefer `argparse` entrypoints with `--check` mode and clear exit codes.
  - Functional catalogue: `tools/generate_functional_catalogue.py --check` (write temp + diff).
  - Python tooling remains `black`, `ruff`, `mypy`.

- **Poetry/pyproject updates**:

  - Add dev dependencies: `mdformat`, `mdformat-gfm`, `mdformat-frontmatter`, `mdformat-footnote` (if used), `pymarkdownlnt`, `codespell`, and any custom-script helpers (`beautifulsoup4` or `markdown-it-py` if needed for link parsing).
  - Add console scripts/Poetry scripts for each checker (`check-doc-filenames`, `check-doc-headers`, etc.) to simplify orchestration.
  - Configure `pymarkdown` via `.pymarkdown.json` (rule enables/ignores matching the standard; enforce MD040/MD046/MD048, disallow HTML MD033, etc.).
  - Configure `codespell` via `pyproject.toml` or `setup.cfg` with allowlist (Effectful/BBY/SpectralMC terms).

- **Dockerfile changes (`docker/Dockerfile`)**:

  - Ensure system packages include any parser needs (likely none beyond `build-essential`).
  - After `poetry install --with dev`, the image will carry mdformat/pymarkdown/codespell; no Node required.
  - Optionally add a `RUN mdformat --version && pymarkdown --version && codespell --version` sanity check to fail fast during build.

- **New/updated scripts (under `tools/`)**:

  - `check_doc_filenames.py`: enforce snake_case, allowed dirs, forbid versioned names.
  - `check_doc_artifacts.py`: forbid backups/temp/txt in doc dirs.
  - `check_doc_headers.py`: enforce title + Status/Supersedes/Referenced by + Purpose; require Cross-References for authoritative; enforce Reference-only authoritative link.
  - `check_doc_links.py`: resolve relative links + anchors, forbid repo-absolute GitHub URLs, ensure descriptive link text.
  - `check_doc_crossrefs.py`: validate Cross-References contents vs headers/anchors.
  - `check_doc_code_blocks.py`: enforce fenced languages and first-line comment; block `Any`/`cast`/`# type: ignore` outside “Wrong” examples.
  - `check_mermaid_metadata.py`: enforce canonical DSL, `%% kind/id/base-id`, uniqueness, and banned constructs.
  - `check_demo_docs.py`: base link at top, delta-only check (warning/fail toggle), filename parity with base.
  - `generate_functional_catalogue.py`: scan canonical diagrams, enforce uniqueness, emit `documents/engineering/functional_catalogue.md`; `--check` mode for CI.
  - Shared helpers module (e.g., `tools/doc_utils.py`) for anchor generation/link resolution to avoid duplication.
  - Update `tools/check_code.py` (or replace with `tools/run_check_code.py`) to orchestrate the full chain with clear step logging and fail-fast behavior.

- **Configuration files**:

  - `.pymarkdown.json`: rule set matching §6; enable MD013 if desired with 120/100 thresholds; disable MD041 overrides only if necessary.
  - `.codespellrc`: skip paths (e.g., `poetry.lock`), custom words.
  - `.mdformat.toml` or `pyproject.toml` section to pin plugins and line length.
  - `tools/` configs for custom scripts if they need allowlists (e.g., `tools/check_doc_links_allowlist.json`).

- **CI/local entrypoint (`poetry run check-code`)**:

  - Sequence: `black` → `ruff` → `mypy` → `mdformat --check documents demo` → `pymarkdown scan` → `codespell` → `check_doc_*` scripts → `check_mermaid_metadata` → `check_demo_docs` → `generate_functional_catalogue --check`.
  - Ensure non-zero exit on any failure; provide summarized failures per stage.
  - Document the command in `documents/documentation_standards.md` and `documents/engineering/code_quality.md` as the single gate.

- **Testing/validation of the checker**:

  - Add unit tests in `tests/unit/tools/` for each script (fixture markdown violating specific rules).
  - Add integration test for the pipeline entrypoint using temporary directories.
  - Run `poetry run check-code` in CI (Dockerized) and ensure it runs within existing compose service (`docker-compose -f docker/docker-compose.yml exec effectful ...`).

## 6. Script/File Layout (planned)

```text
tools/
  check_code.py                    # orchestrates black → ruff → mypy → mdformat → pymarkdown → codespell → custom checks → catalogue
  doc_utils.py                     # shared helpers: anchor generation, link resolution, frontmatter parsing
  check_doc_filenames.py
  check_doc_artifacts.py
  check_doc_headers.py
  check_doc_links.py
  check_doc_crossrefs.py           # optional/if present per spec
  check_doc_code_blocks.py
  check_mermaid_metadata.py
  check_demo_docs.py
  generate_functional_catalogue.py
configs/
  .pymarkdown.json                 # linter rules
  .mdformat.toml (or pyproject)    # formatter plugins
  .codespellrc                     # dictionary and ignores
documents/engineering/functional_catalogue.md   # generated (check mode compares)
```

## 7. `poetry run check-code` entrypoint updates

- Replace existing sequence in `tools/check_code.py` with:
  1. `black effectful tests tools`
  1. `ruff check effectful tests tools`
  1. `mypy effectful tests tools`
  1. `mdformat --check documents demo` (and any other doc roots)
  1. `pymarkdown scan --config configs/.pymarkdown.json documents demo`
  1. `codespell --config configs/.codespellrc documents demo`
  1. Custom scripts (all exit non-zero on failure):
     - `python -m tools.check_doc_filenames`
     - `python -m tools.check_doc_artifacts`
     - `python -m tools.check_doc_headers`
     - `python -m tools.check_doc_links`
     - `python -m tools.check_doc_crossrefs` (if retained)
     - `python -m tools.check_doc_code_blocks`
     - `python -m tools.check_mermaid_metadata`
     - `python -m tools.check_demo_docs`
  1. `python -m tools.generate_functional_catalogue --check`
- Add structured logging for each step and fail-fast behavior; surface a final summary.
- Update any Poetry script entry in `pyproject.toml` to point to `tools.check_code:main`.

## 8. Dependency and Docker updates

- **pyproject.toml (dev deps)**:
  - Add `mdformat`, `mdformat-gfm`, `mdformat-frontmatter`, `mdformat-footnote` (if used), `pymarkdownlnt`, `codespell`.
  - Add parser helpers if needed (`markdown-it-py`, `beautifulsoup4`) for link/anchor validation.
  - Ensure versions are pinned/compatible with Python 3.12.
- **Dockerfile (`docker/Dockerfile`)**:
  - No additional apt packages expected; retain `build-essential`.
  - After `poetry install --with dev`, the image will include the new dev deps.
  - Add optional verification step: `RUN mdformat --version && pymarkdown --version && codespell --version` to fail early during image build.

## 9. Build Artifact Compliance (per engineering/build_artifact_management.md)

- Treat all generated outputs from checks as build artifacts: formatter rewrites, linter caches, link-check temp files, and catalogue temp outputs must stay inside the container under `/opt/**` and remain untracked.
- Ensure `.gitignore` and `.dockerignore` continue to exclude build artifacts and caches (`dist/`, `build/`, `*.egg-info/`, `__pycache__/`, `.mypy_cache/`, `.pytest_cache/`, lockfiles).
- `generate_functional_catalogue.py --check` should write any temp output to `/opt` and compare to the tracked canonical file. Only copy updated content into `documents/engineering/functional_catalogue.md` during intentional updates; otherwise leave no residue in the repo.
- Custom scripts must avoid emitting files under the repo tree; if they need scratch space, use `/opt/check-docs` inside the container and ensure it is git-ignored.
- CI and local runs must not copy artifacts from the container back to the host.

## 10. Demo hierarchy alignment (e.g., `demo/healthhub/documents/documentation_standards.md`)

- Treat `documents/documentation_standards.md` as the SSoT; demo overlays must be delta-only:
  - Ensure `demo/healthhub/documents/documentation_standards.md` begins with `> **📖 Base Standard**: [../../documentation_standards.md]` (correct relative link) and lists only overrides for the demo context.
  - Mirror file naming and header metadata (Status/Supersedes/Referenced by + Purpose), with `Status` likely `Reference only` unless the demo introduces authoritative deltas; include `Authoritative Reference` link back to base.
  - If no deltas exist, explicitly state that the demo follows the base standard without changes.
  - Demo canonical Mermaid diagrams must include `%% base-id:` pointing to the base canonical IDs; `check_mermaid_metadata` will enforce this.
  - `check_demo_docs.py` should assert filename parity, base link presence, and delta-only posture to preserve hierarchy.

## 11. Scope Split: Effectful Core vs HealthHub Demo

- **Effectful core**:
  - Implement and wire the full doc checker suite and `poetry run check-code`.
  - Apply header/naming/Mermaid/code-block/link fixes across `documents/` (non-demo).
  - Generate/enforce `documents/engineering/functional_catalogue.md`.
  - Update CLAUDE/README references and contributor guidance to point to the new gate.
  - Ensure all canonical diagrams have `%% id:` (no `base-id`) and conform to the DSL.
- **HealthHub demo (`demo/healthhub/documents/`)**:
  - Add/verify Base Standard link at the top of each overlay doc; keep content delta-only.
  - Align filenames and headers with base; likely use `Status: Reference only` and include `Authoritative Reference` back to base.
  - For any demo-specific canonical diagrams, add `%% base-id:` pointing to the base ID; otherwise, delete or downgrade diagrams that duplicate base canon.
  - Run the same header/naming/code-block/link/mermaid checks; `check_demo_docs.py` should fail on missing base link or duplicate-heavy content.
  - Document HealthHub-specific exceptions (if any) inside the overlay, not in the base.

## 12. Targeted doc updates (code_quality.md, testing_architecture.md, testing.md)

- Audit these authoritative docs for new requirements: ensure header metadata, Purpose blockquote, and Cross-References compliance per Documentation Standards.
- Update their “Link Map”/cross-reference sections to align with the new SSoT structure and relative links (no absolute GitHub links).
- Ensure they reference the expanded `poetry run check-code` gate (Markdown + custom scripts) as the canonical pre-review step.
- Verify code examples follow fenced-language and first-line-comment rules, and include WRONG/RIGHT patterns when showing anti-patterns.
- Confirm any Mermaid diagrams follow the canonical subset (no banned constructs); add `%% kind`/`%% id` only if they are canonical and meant for the functional catalogue.
- Check that references to testing commands/documentation tooling point to the Docker-only entrypoints and avoid host execution.
- If demo overlays exist for these docs, ensure delta-only content with base link and `Status: Reference only`.

## 13. Next Actions (immediate)

- Wire `poetry run check-code` to the full doc suite and confirm failure modes locally.
- Run header + naming sweeps to surface bulk issues.
- Triage Mermaid and demo overlay violations, then regenerate the functional catalogue.

## Appendix: Phased Migration Plan with Validations

**Phase 1: Toolchain foundation**

- Actions: Add dev deps (mdformat/pymarkdown/codespell), configs, and new/updated scripts; update Dockerfile with version checks; wire `poetry run check-code` orchestrator.
- Validation: `poetry run check-code` fails on an intentional doc violation (e.g., bad header) and passes when fixed; `mdformat --version`, `pymarkdown --version`, and `codespell --version` succeed inside the container. **Status**: tool availability confirmed in both core (`effectful` service) and HealthHub (`healthhub` service) containers.

**Phase 2: Header/naming/layout sweep**

- Actions: Apply required metadata blocks and Cross-References to all authoritative docs; enforce snake_case and allowed directories; purge forbidden artifacts.
- Validation: `check_doc_headers.py`, `check_doc_filenames.py`, and `check_doc_artifacts.py` all pass across `documents/` and `demo/*/documents/`.

**Phase 3: Link and code block hygiene**

- Actions: Fix relative links/anchors, forbid repo-absolute GitHub links, and standardize fenced code blocks with first-line comments; apply to core and demo docs.
- Validation: `check_doc_links.py`, `check_doc_code_blocks.py`, and `pymarkdown scan` pass; spot-check that WRONG/RIGHT pairs are correctly labeled where escape hatches appear.

**Phase 4: Mermaid canon and catalogue**

- Actions: Update canonical diagrams to the required DSL, add `%% id` (and `%% base-id` in demos), remove banned constructs; regenerate functional catalogue.
- Validation: `check_mermaid_metadata.py` passes; `generate_functional_catalogue.py --check` is clean; catalogue diff matches diagram set.

**Phase 5: Demo overlays (HealthHub)**

- Actions: Ensure Base Standard links, delta-only content, filename parity, and demo canonical diagrams reference base via `%% base-id`.
- Validation: `check_demo_docs.py` passes; manual spot-check confirms overlays do not duplicate base content.

**Phase 6: Targeted doc refresh (code_quality/testing_architecture/testing)**

- Actions: Update link maps, references to expanded check-code gate, code block compliance, and any canonical diagrams; ensure Docker-only command guidance.
- Validation: Re-run `poetry run check-code`; manual review of these three docs for SSoT alignment and header compliance.

**Phase 7: Full gate + artifact compliance check**

- Actions: Run full `poetry run check-code` in Docker; ensure scratch paths stay under `/opt/**` and no artifacts leak to repo.
- Validation: `git status` clean; `.gitignore/.dockerignore` still exclude artifacts; no new files under repo root from check runs; command exits 0.
