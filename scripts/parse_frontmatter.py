#!/usr/bin/env python3
"""Extract YAML frontmatter from a SKILL.md.

Usage: parse_frontmatter.py <path-to-SKILL.md>
Output: JSON with keys name, description, version (version defaults to "1.0.0").
Exits 1 if no frontmatter or required fields missing.
"""
import json
import sys
import yaml

if len(sys.argv) != 2:
    print("usage: parse_frontmatter.py <SKILL.md>", file=sys.stderr)
    sys.exit(2)

text = open(sys.argv[1]).read()
if not text.startswith("---"):
    print(f"{sys.argv[1]}: no frontmatter", file=sys.stderr)
    sys.exit(1)

# Split on first two --- markers
parts = text.split("---", 2)
if len(parts) < 3:
    print(f"{sys.argv[1]}: malformed frontmatter", file=sys.stderr)
    sys.exit(1)

meta = yaml.safe_load(parts[1]) or {}
name = meta.get("name")
if not name:
    print(f"{sys.argv[1]}: missing 'name'", file=sys.stderr)
    sys.exit(1)

# Description may be a multi-line block scalar — normalize to single line
desc = (meta.get("description") or f"Personal Claude skill: {name}").strip().replace("\n", " ")
version = str(meta.get("version") or "1.0.0")

json.dump({"name": name, "description": desc, "version": version}, sys.stdout)
