"""Blind pairwise comparison against AMD's retired Track 2 references.

This is a directional regression check, not a reproduction of AMD's hidden
judge. Candidate labels are shuffled so the evaluator cannot prefer "new".
"""
from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

from openai import OpenAI


def _track2_references(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    start = text.index("***Track 2 sample tasks***")
    end = text.index("**Before You Submit**", start)
    return text[start:end]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("guide", type=Path)
    parser.add_argument("--seed", type=int, default=871)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    key = os.environ.get("CLIO_API_KEY", "").strip() or os.environ.get("NOVITA_API_KEY", "").strip()
    if not key:
        raise SystemExit("Set CLIO_API_KEY or NOVITA_API_KEY")

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    baseline_by_id = {row["task_id"]: row["captions"] for row in baseline}
    candidate_by_id = {row["task_id"]: row["captions"] for row in candidate}
    if baseline_by_id.keys() != candidate_by_id.keys():
        raise SystemExit("Candidate task IDs differ")

    rng = random.Random(args.seed)
    pairs: dict[str, dict[str, dict[str, str]]] = {}
    label_map: dict[tuple[str, str], str] = {}
    for task_id in sorted(baseline_by_id):
        pairs[task_id] = {}
        for style in baseline_by_id[task_id]:
            values = [baseline_by_id[task_id][style], candidate_by_id[task_id][style]]
            if rng.random() < 0.5:
                values.reverse()
                label_map[(task_id, style)] = "A"
            else:
                label_map[(task_id, style)] = "B"
            pairs[task_id][style] = {"A": values[0], "B": values[1]}

    prompt = f"""You are a strict video-caption benchmark evaluator.
The retired AMD Track 2 reference examples below define the expected factual
coverage and tone. For every task and style, choose caption A, caption B, or TIE.
Judge: factual alignment with the reference scene, concrete specificity,
natural English, and exact style strength. Penalize generic reusable jokes,
invented literal facts, awkward tech metaphors, verbosity, and weak sarcasm.
Do not reward a caption for resembling reference wording when it is less accurate.

Return JSON only with this shape:
{{"decisions": {{"v1": {{"formal": {{"winner":"A|B|TIE","reason":"short"}}, ...}}}},
 "summary": "short comparison"}}

REFERENCES:
{_track2_references(args.guide)}

BLIND PAIRS:
{json.dumps(pairs, ensure_ascii=False)}
"""
    client = OpenAI(api_key=key, base_url="https://api.novita.ai/openai", timeout=120)
    response = client.chat.completions.create(
        model="moonshotai/kimi-k2.6",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=6000,
        extra_body={"thinking": {"type": "disabled"}},
    )
    raw = response.choices[0].message.content or ""
    left = raw.find("{")
    right = raw.rfind("}")
    data = json.loads(raw[left : right + 1])

    counts = {"baseline": 0, "candidate": 0, "tie": 0}
    losses: list[dict[str, str]] = []
    for task_id, styles in data["decisions"].items():
        for style, decision in styles.items():
            winner = str(decision["winner"]).upper()
            if winner == "TIE":
                counts["tie"] += 1
            elif winner == label_map[(task_id, style)]:
                counts["candidate"] += 1
            else:
                counts["baseline"] += 1
                losses.append({
                    "task_id": task_id,
                    "style": style,
                    "reason": str(decision.get("reason", "")),
                })
    output = {"counts": counts, "candidate_losses": losses, "summary": data.get("summary", "")} if args.summary_only else {
        "counts": counts,
        "evaluation": data,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
