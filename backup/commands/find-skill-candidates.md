---
description: Analyze recent Claude Code prompt history in this project and surface candidates for new skills (or underused existing skills).
---

Invoke the `find-skill-candidates` skill. Follow its SKILL.md exactly:

1. Find the transcripts directory from cwd
2. Run `extract_prompts.py` (with `--days 60` if there are many prompts)
3. Run `list_existing_skills.py --project-root "$(pwd)"`
4. Cluster the prompts semantically
5. Apply the qualification filter
6. Present the structured report
7. Ask which to build
8. Hand off accepted candidates to skill-creator
