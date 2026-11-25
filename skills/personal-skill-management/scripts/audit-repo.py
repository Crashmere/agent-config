#!/usr/bin/env python3
"""Audit the agent-config repository for skill validity, metadata budget, links, and hygiene."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
MAX_NAME_LENGTH = 64
RECOMMENDED_DESC_LENGTH = 160
BUDGET_WARN = 2200
BUDGET_LIMIT = 2400


def parse_frontmatter(content: str) -> tuple[dict[str, str], str] | tuple[None, str]:
    if not content.startswith("---\n"):
        return None, "missing opening YAML frontmatter delimiter"
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", content, re.DOTALL)
    if not match:
        return None, "missing closing YAML frontmatter delimiter"

    fm_text = match.group(1)
    body = content[match.end() :]
    keys: dict[str, str] = {}
    current_key: str | None = None
    multiline_lines: list[str] = []

    def finish_multiline() -> None:
        nonlocal current_key, multiline_lines
        if current_key is not None and multiline_lines:
            keys[current_key] = " ".join(x.strip() for x in multiline_lines if x.strip())
        multiline_lines = []

    for raw_line in fm_text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line[0].isspace():
            if current_key is not None and current_key != "metadata":
                multiline_lines.append(raw_line)
            continue
        finish_multiline()
        m = re.match(r"^([A-Za-z0-9_-]+):(.*)$", raw_line)
        if not m:
            return None, f"unrecognized frontmatter line: {raw_line!r}"
        key, val = m.group(1), m.group(2).strip()
        current_key = key
        if val in {">", ">-", "|", "|-", ""}:
            keys[key] = ""
        else:
            if len(val) >= 2 and val[0] == val[-1] and val[0] in {'"', "'"}:
                val = val[1:-1]
            keys[key] = val

    finish_multiline()
    return keys, body


def has_todo_outside_fences(body: str) -> bool:
    fence_marker: str | None = None
    fence_length = 0
    for line in body.splitlines():
        fence = re.match(r"^[ \t]*(?:(?:[-+*]|\d+[.)])[ \t]+)?(`{3,}|~{3,})(.*)$", line)
        if fence:
            marker = fence.group(1)
            if fence_marker is None:
                fence_marker = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_marker and len(marker) >= fence_length and not fence.group(2).strip():
                fence_marker = None
                fence_length = 0
            continue
        if fence_marker is None and re.fullmatch(r"[ ]{0,3}\[TODO:[^\n]*\][ \t]*", line):
            return True
    return False


def check_markdown_links(md_path: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    text = md_path.read_text(encoding="utf-8")
    for m in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        raw_target = m.group(1).strip()
        target = raw_target.split("#", 1)[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:", "file:")):
            continue
        resolved = (md_path.parent / target).resolve()
        if not resolved.exists():
            rel = md_path.relative_to(repo_root)
            errors.append(f"broken link in {rel}: {raw_target}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit personal skills and repository hygiene.")
    parser.add_argument("--skip-links", action="store_true", help="Skip running sync-skill-links.sh.")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    skills_dir = repo_root / "skills"
    readme_path = repo_root / "README.md"

    errors: list[str] = []
    warnings: list[str] = []

    readme_text = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
    skill_dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith("."))

    active_skills: set[str] = set()
    total_desc_chars = 0

    for sdir in skill_dirs:
        skill_md = sdir / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"orphan directory under skills/ without SKILL.md: skills/{sdir.name}")
            continue

        active_skills.add(sdir.name)
        content = skill_md.read_text(encoding="utf-8")
        fm, body_or_err = parse_frontmatter(content)
        if fm is None:
            errors.append(f"{sdir.name}: invalid frontmatter ({body_or_err})")
            continue

        unexpected = set(fm.keys()) - ALLOWED_FRONTMATTER_KEYS
        if unexpected:
            errors.append(f"{sdir.name}: unexpected frontmatter keys: {sorted(unexpected)}")

        name = fm.get("name", "").strip()
        if not name:
            errors.append(f"{sdir.name}: missing frontmatter name")
        elif name != sdir.name:
            errors.append(f"{sdir.name}: frontmatter name {name!r} does not match folder name")
        elif not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", name) or len(name) > MAX_NAME_LENGTH:
            errors.append(f"{sdir.name}: invalid hyphen-case name {name!r}")

        desc = fm.get("description", "").strip()
        if not desc:
            errors.append(f"{sdir.name}: missing frontmatter description")
        else:
            if desc.startswith("[TODO:") or "<" in desc or ">" in desc:
                errors.append(f"{sdir.name}: invalid description content")
            total_desc_chars += len(desc)
            if len(desc) > RECOMMENDED_DESC_LENGTH:
                warnings.append(f"{sdir.name}: description length {len(desc)} exceeds {RECOMMENDED_DESC_LENGTH}")

        if has_todo_outside_fences(body_or_err):
            errors.append(f"{sdir.name}: unfinished [TODO:...] placeholder in SKILL.md")

        openai_yaml = sdir / "agents" / "openai.yaml"
        if not openai_yaml.exists():
            errors.append(f"{sdir.name}: missing agents/openai.yaml")
        else:
            oy_text = openai_yaml.read_text(encoding="utf-8")
            if f"${sdir.name}" not in oy_text:
                warnings.append(f"{sdir.name}: agents/openai.yaml does not mention ${sdir.name}")

        expected_readme_link = f"./skills/{sdir.name}/SKILL.md"
        if expected_readme_link not in readme_text:
            errors.append(f"{sdir.name}: missing from README.md ({expected_readme_link})")

        errors.extend(check_markdown_links(skill_md, repo_root))

        refs_dir = sdir / "references"
        if refs_dir.is_dir():
            for md_file in sorted(refs_dir.rglob("*.md")):
                errors.extend(check_markdown_links(md_file, repo_root))
            for top_ref in sorted(refs_dir.glob("*.md")):
                rel_ref = f"references/{top_ref.name}"
                if rel_ref not in content and top_ref.name not in content:
                    warnings.append(f"{sdir.name}: {rel_ref} is not directly linked from SKILL.md")

    # Check README.md for stale skill entries
    for m in re.finditer(r"\./skills/([a-z0-9-]+)/SKILL\.md", readme_text):
        listed = m.group(1)
        if listed not in active_skills:
            errors.append(f"README.md references missing skill: {listed}")

    # Budget check
    if total_desc_chars > BUDGET_LIMIT:
        errors.append(f"description metadata budget exceeded: {total_desc_chars} / {BUDGET_LIMIT}")
    elif total_desc_chars > BUDGET_WARN:
        warnings.append(f"description metadata budget high: {total_desc_chars} / {BUDGET_LIMIT}")

    # Client symlink check
    link_summary = "skipped"
    if not args.skip_links:
        sync_script = script_dir / "sync-skill-links.sh"
        proc = subprocess.run(["bash", str(sync_script)], capture_output=True, text=True)
        out_lines = [l for l in proc.stdout.splitlines() if l.strip()]
        summary_lines = [l for l in out_lines if l.startswith("Summary:")]
        link_summary = summary_lines[-1] if summary_lines else f"exit={proc.returncode}"
        for l in out_lines:
            if l.startswith(("MISSING", "CONFLICT", "STALE")):
                errors.append(f"client link: {l}")

    print(f"Repository: {repo_root}")
    print(f"Skills audited: {len(active_skills)}")
    print(f"Description budget: {total_desc_chars} / {BUDGET_LIMIT} chars")
    print(f"Client links: {link_summary}")

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\nAudit passed with no errors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
