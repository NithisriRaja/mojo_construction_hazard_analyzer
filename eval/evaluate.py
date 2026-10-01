"""
Score result folders against eval/ground_truth.json.

  recall        expected hazards found (matched by regex on title+description)
  category acc  of the found ones, how many have the reference category
  false claims  hits on known-false 'must_not' patterns
  extra         findings not matched to any expected hazard (review by hand:
                they may be valid hazards the reference list does not cover)

Usage:
    python eval/evaluate.py results/v1_run1 results/v4_run1 ...
    python eval/evaluate.py results/v4_run1 --detail
"""
import argparse
import json
import re
import sys
from pathlib import Path

GROUND_TRUTH = Path(__file__).with_name("ground_truth.json")


def _text(h: dict) -> str:
    return f"{h['title']} {h['description']}"


def score(run_dir: Path, truth: dict, detail: bool) -> dict:
    tot = {"expected": 0, "found": 0, "cat_ok": 0, "false": 0, "findings": 0, "extra": 0}
    for image, gt in truth.items():
        f = run_dir / f"{image}.json"
        if not f.exists():
            print(f"  missing result: {f.name}", file=sys.stderr)
            continue
        hazards = json.loads(f.read_text(encoding="utf-8"))["hazards"]
        used = set()
        lines = []
        for exp in gt["expected"]:
            tot["expected"] += 1
            hits = [i for i, h in enumerate(hazards) if i not in used and re.search(exp["match"], _text(h), re.I)]
            # prefer a hit that already has the reference category
            idx = next((i for i in hits if hazards[i]["category"] == exp["category"]), hits[0] if hits else None)
            if idx is None:
                lines.append(f"    MISS   {exp['id']}")
                continue
            used.add(idx)
            tot["found"] += 1
            got = hazards[idx]["category"]
            if got == exp["category"]:
                tot["cat_ok"] += 1
                lines.append(f"    ok     {exp['id']}")
            else:
                lines.append(f"    CAT    {exp['id']}: got '{got}', want '{exp['category']}'")
        for bad in gt["must_not"]:
            for h in hazards:
                if re.search(bad["match"], _text(h), re.I):
                    tot["false"] += 1
                    lines.append(f"    FALSE  {bad['id']}: {h['title']}")
        extra = [h for i, h in enumerate(hazards) if i not in used]
        tot["findings"] += len(hazards)
        tot["extra"] += len(extra)
        if detail:
            print(f"  {image}")
            print("\n".join(lines))
            for h in extra:
                print(f"    extra  [{h['severity']}] {h['category']} | {h['title']}")
    return tot


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--detail", action="store_true")
    args = ap.parse_args()
    truth = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))["images"]

    rows = []
    for run in args.runs:
        if args.detail:
            print(f"== {run}")
        t = score(Path(run), truth, args.detail)
        rows.append((run, t))

    print(f"\n{'run':28} {'recall':>9} {'category acc':>13} {'false claims':>13} {'findings':>9} {'extra':>6}")
    for run, t in rows:
        recall = f"{t['found']}/{t['expected']}"
        cat = f"{t['cat_ok']}/{t['found']}"
        print(f"{Path(run).name:28} {recall:>9} {cat:>13} {t['false']:>13} {t['findings']:>9} {t['extra']:>6}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
