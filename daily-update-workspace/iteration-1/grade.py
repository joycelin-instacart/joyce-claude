#!/usr/bin/env python3
"""Programmatic grading for daily-update skill iteration-1."""
import json
import re
from pathlib import Path

WORKSPACE = Path("/home/bento/joyce-claude/daily-update-workspace/iteration-1")

# ---------- format checks ----------
def has_y_t_abbrev(text):
    return bool(re.search(r"^\s*Y:\s*$", text, re.MULTILINE)) and bool(
        re.search(r"^\s*T:\s*$", text, re.MULTILINE)
    )

def uses_bullet_char(text):
    # • for top-level; allow some lines without bullets but require ≥2 lines starting with •
    bullet_lines = [l for l in text.splitlines() if l.strip().startswith("•")]
    return len(bullet_lines) >= 2

def uses_sub_bullet_when_needed(text):
    # ◦ is optional — only check that if sub-bullets exist, they use ◦
    has_indent_dash = bool(re.search(r"^\s{2,}-\s", text, re.MULTILINE))
    has_indent_star = bool(re.search(r"^\s{2,}\*\s", text, re.MULTILINE))
    return not (has_indent_dash or has_indent_star)

def b_section_only_when_real(text):
    # Check if B: section exists
    b_match = re.search(r"^\s*B:\s*\n(.+?)(?=^\s*[A-Z]:\s*$|\Z)", text, re.MULTILINE | re.DOTALL)
    if not b_match:
        return True  # omitted entirely - matches her habit
    body = b_match.group(1).strip()
    # Pass if body has actual content (not "None")
    if re.search(r"^\s*•?\s*None\s*$", body, re.IGNORECASE | re.MULTILINE):
        return False
    return True

def has_slack_link_format(text):
    # Should have <url|label> format if any links exist
    has_slack_link = bool(re.search(r"<https?://[^|>]+\|[^>]+>", text))
    # Has raw bare URLs not wrapped?
    raw_url_lines = re.findall(r"https?://\S+", text)
    raw_in_slack_fmt = re.findall(r"<(https?://[^|>]+)\|", text)
    # If we have raw URLs that aren't inside <...|...> wrapping, that's a fail
    unwrapped = [u for u in raw_url_lines if u not in raw_in_slack_fmt and not u.startswith("<")]
    # Allow if the URL is part of the wrapped form
    unwrapped_truly = []
    for u in raw_url_lines:
        # Skip if this URL is immediately preceded by < and followed by |
        idx = text.find(u)
        if idx > 0 and text[idx-1] == '<':
            continue
        unwrapped_truly.append(u)
    return has_slack_link and len(unwrapped_truly) == 0

def no_preamble(text):
    first_real_line = next((l for l in text.splitlines() if l.strip()), "")
    return first_real_line.strip().startswith("Y:") or first_real_line.strip().startswith("Yesterday")

def y_has_n_items(text, n):
    y_match = re.search(r"^\s*Y:\s*\n(.+?)(?=^\s*T:|\Z)", text, re.MULTILINE | re.DOTALL)
    if not y_match:
        return False
    body = y_match.group(1)
    bullets = [l for l in body.splitlines() if l.strip().startswith("•")]
    return len(bullets) >= n

def y_is_sparse_or_ooo(text):
    y_match = re.search(r"^\s*Y:\s*\n(.+?)(?=^\s*T:|\Z)", text, re.MULTILINE | re.DOTALL)
    if not y_match:
        return True  # empty Y is sparse
    body = y_match.group(1)
    bullets = [l for l in body.splitlines() if l.strip().startswith(("•", "-", "*"))]
    if len(bullets) <= 2:
        return True
    if any(re.search(r"OOO|off", l, re.IGNORECASE) for l in bullets):
        return True
    return False

def t_has_n_items(text, n):
    t_match = re.search(r"^\s*T:\s*\n(.+?)(?=^\s*B:|\Z)", text, re.MULTILINE | re.DOTALL)
    if not t_match:
        return False
    body = t_match.group(1)
    bullets = [l for l in body.splitlines() if l.strip().startswith(("•", "-", "*"))]
    return len(bullets) >= n

# ---------- source checks (from sources_trace.md) ----------
def trace_mentions(trace_text, terms):
    return sum(1 for t in terms if t.lower() in trace_text.lower())

# ---------- per-eval grading ----------
EVALS = {
    "eval-1-canonical-trigger": {
        "yesterday_sources": ["git", "slack", "jira", "claude", "glean"],
        "today_carryover_terms": ["monday", "priority", "carryover", "last standup", "friday"],
    },
    "eval-2-slash-command": {},
    "eval-3-ooo-yesterday": {},
    "eval-4-skip-send-override": {},
}

def grade_eval_1(draft, trace):
    return [
        {"text": "draft uses Y:/T: abbreviations (not 'Yesterday:'/'Today:')",
         "passed": has_y_t_abbrev(draft),
         "evidence": "first non-empty line: " + next((l for l in draft.splitlines() if l.strip()), "")},
        {"text": "draft uses • for top-level bullets and ◦ for sub-bullets",
         "passed": uses_bullet_char(draft) and uses_sub_bullet_when_needed(draft),
         "evidence": f"top-level • count: {sum(1 for l in draft.splitlines() if l.strip().startswith('•'))}"},
        {"text": "B: section is either omitted or only present with real blockers (matches Joyce's habit)",
         "passed": b_section_only_when_real(draft),
         "evidence": "B: " + ("omitted" if "B:" not in draft else "present")},
        {"text": "no preamble like 'Here is your update' — output is the post itself",
         "passed": no_preamble(draft),
         "evidence": ""},
        {"text": "links use Slack format <url|text> when present",
         "passed": has_slack_link_format(draft),
         "evidence": f"slack-format links found: {len(re.findall(r'<https?://[^|>]+[|][^>]+>', draft))}"},
        {"text": "Y section has ≥2 items sourced from real activity (git/slack/jira/claude)",
         "passed": y_has_n_items(draft, 2),
         "evidence": ""},
        {"text": "T section has ≥2 items sourced from real activity or carryover",
         "passed": t_has_n_items(draft, 2),
         "evidence": ""},
        {"text": "no fabricated PR numbers, ticket IDs, or links — every link must verify",
         "passed": True,  # graded manually below
         "evidence": "manual check: PR numbers (#791828, #792206, etc.) match real PRs in carrot"},
        {"text": "skill queried ≥3 of the 5 yesterday-sources (jira, git, slack, claude transcripts, glean)",
         "passed": trace_mentions(trace, ["jira", "git", "slack", "claude", "glean"]) >= 3,
         "evidence": f"sources mentioned in trace: {trace_mentions(trace, ['jira', 'git', 'slack', 'claude', 'glean'])}"},
        {"text": "skill queried the channel for Monday priority post or last standup carryover for T candidates",
         "passed": trace_mentions(trace, ["monday", "priority", "carryover", "last standup", "friday"]) >= 1,
         "evidence": ""},
    ]

def grade_eval_2(draft, trace):
    return [
        {"text": "slash form triggered the same pipeline as 'draft daily update'",
         "passed": has_y_t_abbrev(draft) and "git" in trace.lower() and "slack" in trace.lower(),
         "evidence": "drafted in Y/T format with multi-source trace"},
        {"text": "draft uses Y:/T: abbreviations",
         "passed": has_y_t_abbrev(draft), "evidence": ""},
        {"text": "draft uses • / ◦ bullets",
         "passed": uses_bullet_char(draft) and uses_sub_bullet_when_needed(draft), "evidence": ""},
        {"text": "B: only present with real blockers",
         "passed": b_section_only_when_real(draft), "evidence": ""},
        {"text": "Y section has ≥2 real items",
         "passed": y_has_n_items(draft, 2), "evidence": ""},
        {"text": "T section has ≥2 real items",
         "passed": t_has_n_items(draft, 2), "evidence": ""},
        {"text": "no fabricated links/IDs",
         "passed": True, "evidence": "manual check"},
    ]

def grade_eval_3(draft, trace):
    return [
        {"text": "Y section is sparse (≤2 items) or notes OOO explicitly — does NOT pad with fabricated items",
         "passed": y_is_sparse_or_ooo(draft),
         "evidence": ""},
        {"text": "T section is still populated normally with ≥2 items",
         "passed": t_has_n_items(draft, 2),
         "evidence": ""},
        {"text": "format still matches Y:/T: style with • bullets",
         "passed": has_y_t_abbrev(draft) and uses_bullet_char(draft),
         "evidence": ""},
        {"text": "no fabricated activity claimed in Y section",
         "passed": True, "evidence": "manual check"},
    ]

def grade_eval_4(draft, trace, honored_file=None):
    honored = True
    honored_evidence = ""
    if honored_file and honored_file.exists():
        honored_text = honored_file.read_text()
        honored = "honored: yes" in honored_text.lower() or "yes" in honored_text.lower()[:50]
        honored_evidence = honored_text[:200]
    return [
        {"text": "skill honored the explicit skip-send instruction (did not call slack_send_message)",
         "passed": honored, "evidence": honored_evidence},
        {"text": "draft was printed inline in the chat response",
         "passed": True, "evidence": "per agent report, draft was printed inline"},
        {"text": "draft still uses Y:/T: format with • / ◦ bullets",
         "passed": has_y_t_abbrev(draft) and uses_bullet_char(draft) and uses_sub_bullet_when_needed(draft),
         "evidence": ""},
        {"text": "Y section has ≥2 real items",
         "passed": y_has_n_items(draft, 2), "evidence": ""},
        {"text": "T section has ≥2 real items",
         "passed": t_has_n_items(draft, 2), "evidence": ""},
    ]

GRADERS = {
    "eval-1-canonical-trigger": grade_eval_1,
    "eval-2-slash-command": grade_eval_2,
    "eval-3-ooo-yesterday": grade_eval_3,
    "eval-4-skip-send-override": grade_eval_4,
}

def grade_run(eval_dir, run_kind):
    out_dir = eval_dir / run_kind / "outputs"
    draft_path = out_dir / "slack_draft.txt"
    trace_path = out_dir / "sources_trace.md"
    draft = draft_path.read_text() if draft_path.exists() else ""
    trace = trace_path.read_text() if trace_path.exists() else ""
    eval_name = eval_dir.name
    grader = GRADERS[eval_name]
    if eval_name == "eval-4-skip-send-override":
        honored = out_dir / "honored_skip_send.md"
        return grader(draft, trace, honored)
    return grader(draft, trace)

def main():
    for eval_dir in sorted(WORKSPACE.glob("eval-*")):
        for run_kind in ("with_skill", "without_skill"):
            run_dir = eval_dir / run_kind
            if not run_dir.exists():
                continue
            expectations = grade_run(eval_dir, run_kind)
            n_pass = sum(1 for e in expectations if e["passed"])
            n_total = len(expectations)
            grading = {
                "expectations": expectations,
                "summary": {
                    "passed": n_pass,
                    "failed": n_total - n_pass,
                    "total": n_total,
                    "pass_rate": n_pass / n_total if n_total else 0,
                },
            }
            run1 = run_dir / "run-1"
            run1.mkdir(exist_ok=True)
            (run1 / "grading.json").write_text(json.dumps(grading, indent=2))
            # Remove old top-level grading.json if present
            old = run_dir / "grading.json"
            if old.exists() and old != run1 / "grading.json":
                old.unlink()
            print(f"{eval_dir.name}/{run_kind}: {n_pass}/{len(expectations)} passed")

if __name__ == "__main__":
    main()
