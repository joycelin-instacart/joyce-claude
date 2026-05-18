#!/usr/bin/env python3
"""List existing Claude Code skills and slash commands available to the user.

Scans:
- ~/.claude/skills (user skills)
- ~/.claude/plugins/cache/**/skills (plugin skills, deduped)
- ~/.claude/commands (user-level slash commands)
- <project-root>/.claude/skills and <project-root>/.claude/commands (project-level)

Usage:
    python3 list_existing_skills.py [--project-root PATH]
"""
import argparse
import glob
import json
import os
import re
import sys


HOME = os.path.expanduser("~")
USER_SKILLS = os.path.join(HOME, ".claude", "skills")
PLUGIN_SKILLS_ROOT = os.path.join(HOME, ".claude", "plugins", "cache")
USER_COMMANDS = os.path.join(HOME, ".claude", "commands")


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    """Parse the YAML-ish frontmatter at the top of a SKILL.md file.

    Avoid pyyaml dependency; only need name/description. Handles single-line
    values and YAML block scalars ("description: |\\n  text\\n  more text").
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out = {}
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val in ("|", ">"):
                # Block scalar — collect indented continuation lines.
                buf = []
                i += 1
                while i < len(lines) and (lines[i].startswith((" ", "\t")) or lines[i] == ""):
                    buf.append(lines[i].lstrip())
                    i += 1
                out[key] = " ".join(s for s in buf if s).strip()
                continue
            out[key] = val
        i += 1
    return out


def collect_skill_file(path: str, source: str) -> dict | None:
    try:
        with open(path) as f:
            text = f.read(4096)  # frontmatter + a bit
    except OSError:
        return None
    fm = parse_frontmatter(text)
    name = fm.get("name") or os.path.basename(os.path.dirname(path))
    return {
        "name": name,
        "description": fm.get("description", ""),
        "source": source,
        "path": path,
    }


def collect_commands_from(dir_path: str, source: str) -> list:
    out = []
    for cmd_md in glob.glob(os.path.join(dir_path, "*.md")):
        name = os.path.basename(cmd_md).removesuffix(".md")
        desc = ""
        try:
            with open(cmd_md) as f:
                text = f.read(4096)
        except OSError:
            text = ""
        # Slash command files often have YAML frontmatter with description: ...
        fm = parse_frontmatter(text)
        if fm.get("description"):
            desc = fm["description"][:200]
        else:
            # Fall back to first non-empty, non-comment line outside frontmatter.
            body = FRONTMATTER_RE.sub("", text, count=1).lstrip()
            for line in body.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    desc = line[:200]
                    break
        out.append({"name": name, "description": desc, "source": source, "path": cmd_md})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=None,
                    help="A directory inside the project. Walks up from here to / looking for "
                         "any .claude/skills/ and .claude/commands/ dirs and includes all of them. "
                         "Use this when in a subdir of a monorepo so subproject-level skills are picked up.")
    args = ap.parse_args()

    skills = []

    # User-level skills
    for sk_md in glob.glob(os.path.join(USER_SKILLS, "*", "SKILL.md")):
        rec = collect_skill_file(sk_md, "user")
        if rec:
            skills.append(rec)
    # User skills without SKILL.md (just a name dir like ~/.claude/skills/daniel)
    for entry in glob.glob(os.path.join(USER_SKILLS, "*")):
        if os.path.isdir(entry) and not os.path.isfile(os.path.join(entry, "SKILL.md")):
            skills.append({
                "name": os.path.basename(entry),
                "description": "(no SKILL.md frontmatter found)",
                "source": "user",
                "path": entry,
            })

    # Plugin skills (path depth varies by plugin layout, so walk recursively)
    if os.path.isdir(PLUGIN_SKILLS_ROOT):
        for root, _, files in os.walk(PLUGIN_SKILLS_ROOT):
            if "SKILL.md" in files and os.path.basename(os.path.dirname(root)) == "skills":
                rec = collect_skill_file(os.path.join(root, "SKILL.md"), "plugin")
                if rec:
                    skills.append(rec)

    # Slash commands: always include user-level
    commands = collect_commands_from(USER_COMMANDS, "user")

    # Project-level skills/commands: walk up from --project-root to / collecting every
    # .claude/skills/ and .claude/commands/ we find. Handles monorepos where the
    # subproject sits below the git root.
    if args.project_root:
        path = os.path.abspath(args.project_root)
        seen = set()
        while True:
            proj_skills_dir = os.path.join(path, ".claude", "skills")
            if os.path.isdir(proj_skills_dir) and proj_skills_dir not in seen:
                seen.add(proj_skills_dir)
                for sk_md in glob.glob(os.path.join(proj_skills_dir, "*", "SKILL.md")):
                    rec = collect_skill_file(sk_md, "project")
                    if rec:
                        skills.append(rec)
                for entry in glob.glob(os.path.join(proj_skills_dir, "*")):
                    if os.path.isdir(entry) and not os.path.isfile(os.path.join(entry, "SKILL.md")):
                        skills.append({
                            "name": os.path.basename(entry),
                            "description": "(no SKILL.md frontmatter found)",
                            "source": "project",
                            "path": entry,
                        })
            proj_cmd_dir = os.path.join(path, ".claude", "commands")
            if os.path.isdir(proj_cmd_dir) and proj_cmd_dir not in seen:
                seen.add(proj_cmd_dir)
                commands.extend(collect_commands_from(proj_cmd_dir, "project"))
            parent = os.path.dirname(path)
            if parent == path:
                break
            path = parent

    # Dedupe by name across versions/cached plugin copies; prefer non-empty descriptions
    by_name: dict[str, dict] = {}
    for s in skills:
        key = s["name"]
        if key not in by_name:
            by_name[key] = s
        elif not by_name[key].get("description") and s.get("description"):
            by_name[key] = s
    deduped = list(by_name.values())

    out = {
        "skill_count": len(deduped),
        "command_count": len(commands),
        "skills": sorted(deduped, key=lambda s: (s["source"], s["name"])),
        "commands": sorted(commands, key=lambda c: c["name"]),
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
