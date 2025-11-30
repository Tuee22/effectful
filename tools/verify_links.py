#!/usr/bin/env python3
"""Verify all internal links in documentation files."""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Root directory of the project
ROOT = Path(__file__).parent.parent

def find_markdown_files() -> List[Path]:
    """Find all markdown files in documents/ and root."""
    md_files = []

    # Documents directory
    for md_file in ROOT.glob("documents/**/*.md"):
        md_files.append(md_file)

    # Root markdown files
    for md_file in ROOT.glob("*.md"):
        md_files.append(md_file)

    return sorted(md_files)

def extract_links(content: str) -> List[str]:
    """Extract all markdown links from content."""
    # Pattern: [text](link)
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(pattern, content)
    return [link for _text, link in matches]

def verify_link(source_file: Path, link: str) -> Tuple[bool, str]:
    """Verify a link exists. Returns (is_valid, reason)."""
    # Skip external links (http/https)
    if link.startswith(('http://', 'https://', 'mailto:')):
        return (True, "external")

    # Skip anchors (same-file references)
    if link.startswith('#'):
        return (True, "anchor")

    # Handle relative paths
    if link.startswith('../'):
        # Relative to parent
        target = (source_file.parent.parent / link.lstrip('../')).resolve()
    elif link.startswith('./'):
        # Relative to current
        target = (source_file.parent / link.lstrip('./')).resolve()
    elif link.startswith('/'):
        # Absolute from root (treat as relative to project root)
        target = (ROOT / link.lstrip('/')).resolve()
    else:
        # Relative to current directory
        target = (source_file.parent / link).resolve()

    # Strip anchor from link
    if '#' in str(target):
        target = Path(str(target).split('#')[0])

    # Check if target exists
    if target.exists():
        return (True, "ok")
    else:
        return (False, f"not found: {target}")

def main() -> int:
    """Main verification logic."""
    print("🔍 Verifying documentation links...")
    print()

    md_files = find_markdown_files()
    print(f"Found {len(md_files)} markdown files")
    print()

    broken_links = []
    total_links = 0

    for md_file in md_files:
        content = md_file.read_text()
        links = extract_links(content)

        for link in links:
            total_links += 1
            is_valid, reason = verify_link(md_file, link)

            if not is_valid:
                broken_links.append((md_file, link, reason))

    # Report results
    print(f"✓ Verified {total_links} total links")
    print()

    if broken_links:
        print(f"❌ Found {len(broken_links)} broken links:")
        print()
        for source, link, reason in broken_links:
            rel_source = source.relative_to(ROOT)
            print(f"  {rel_source}")
            print(f"    → {link}")
            print(f"    → {reason}")
            print()
        return 1
    else:
        print("✅ All links valid!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
