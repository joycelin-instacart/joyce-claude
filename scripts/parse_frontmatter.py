#!/usr/bin/env python3
"""Extract YAML frontmatter from a SKILL.md.

Usage: parse_frontmatter.py <path-to-SKILL.md>
Output: JSON with keys name, description, version (version defaults to "1.0.0").

Falls back gracefully when frontmatter is absent:
  - name: derived from the directory containing SKILL.md
  - description: extracted from the first H1 heading line after the title,
    or from the first non-blank non-heading paragraph
  - version: "1.0.0"
"""
import json
import os
import re
import sys
import yaml

if len(sys.argv) != 2:
    print("usage: parse_frontmatter.py <SKILL.md>", file=sys.stderr)
    sys.exit(2)

path = sys.argv[1]
text = open(path).read()

# --- derive fallback name from directory ---
skill_dir = os.path.dirname(os.path.abspath(path))
fallback_name = os.path.basename(skill_dir)

if text.startswith("---"):
    parts = text.split("---", 2)
    if len(parts) < 3:
        print(f"{path}: malformed frontmatter", file=sys.stderr)
        sys.exit(1)
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2]
else:
    meta = {}
    body = text

name = meta.get("name") or fallback_name

# Description may be a multi-line block scalar — normalize to single line
if meta.get("description"):
    desc = meta["description"].strip().replace("\n", " ")
else:
    # Try to extract a meaningful description from the body:
    # 1. First non-blank line that is not a heading marker itself
    # 2. Fall back to first paragraph sentence
    desc = ""
    lines = body.splitlines()
    # Skip the first H1 heading (the title), then look for the next
    # non-blank, non-heading line or a short paragraph
    skipped_h1 = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            if not skipped_h1:
                skipped_h1 = True
                continue
            # Another heading — stop; description would be too vague
            break
        # First non-blank, non-heading line after the title
        desc = stripped
        break
    if not desc:
        desc = f"Personal Claude skill: {name}"

version = str(meta.get("version") or "1.0.0")

json.dump({"name": name, "description": desc, "version": version}, sys.stdout)
