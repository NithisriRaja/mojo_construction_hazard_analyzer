"""
CLI: detect construction hazards in one image or a folder of images.

Usage:
    python run_analysis.py                          # all images in "Mojo Site image file" -> results/
    python run_analysis.py "path/to/image.png"      # one image, prints JSON
    python run_analysis.py <folder> --out <dir>     # one JSON per image
    python run_analysis.py --provider domo          # use the Domo AI Gateway instead of Claude
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from construction_hazards import analyze_image, config
from construction_hazards.analyzer import analyze_image_with_draft
from construction_hazards import usage_log
from construction_hazards.claude_client import MEDIA_TYPES


def _run_one(path: Path, out_dir: Path, model: str | None, provider: str):
    t0 = time.time()
    try:
        result, draft = analyze_image_with_draft(path, model=model, provider=provider)
        (out_dir / f"{path.stem}.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        drafts = out_dir / "_drafts"  # step-1 output, kept to audit what verify changed
        drafts.mkdir(exist_ok=True)
        (drafts / f"{path.stem}.json").write_text(json.dumps(draft, indent=2, ensure_ascii=False), encoding="utf-8")
        return path, result, None, time.time() - t0
    except Exception as e:  # report and continue with the rest of the batch
        return path, None, str(e), time.time() - t0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", default=str(config.DEFAULT_IMAGE_DIR), help="Image file or folder")
    ap.add_argument("--out", default=str(config.DEFAULT_RESULTS_DIR), help="Output folder (folder runs)")
    ap.add_argument("--model", default=None, help=f"Override model (default: {config.CLAUDE_MODEL})")
    ap.add_argument("--provider", default=config.DEFAULT_PROVIDER, choices=config.PROVIDERS, help="claude or domo")
    ap.add_argument("--workers", type=int, default=2, help="Parallel images (folder runs)")
    args = ap.parse_args()

    target = Path(args.path)
    if target.is_file():
        print(json.dumps(analyze_image(target, model=args.model, provider=args.provider), indent=2, ensure_ascii=False))
        _print_totals()
        return 0

    images = sorted(p for p in target.iterdir() if p.suffix.lower() in MEDIA_TYPES)
    if not images:
        print(f"No images found in {target}", file=sys.stderr)
        return 1
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Provider: {args.provider} | Model: {args.model or (config.CLAUDE_MODEL if args.provider == 'claude' else config.DOMO_MODEL)} | {len(images)} images -> {out_dir}")

    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for path, result, err, dt in pool.map(lambda p: _run_one(p, out_dir, args.model, args.provider), images):
            if err:
                failures += 1
                print(f"  FAIL  {path.name} ({dt:.0f}s): {err}")
                continue
            sev = [h["severity"] for h in result["hazards"]]
            counts = {s: sev.count(s) for s in ("High", "Medium", "Low")}
            print(f"  OK    {path.name} ({dt:.0f}s): {len(sev)} hazards {counts}")

    _print_totals()
    return 1 if failures else 0


def _print_totals() -> None:
    t = usage_log.run_totals()
    print(f"Run {t['run_id']}: {t['calls']} API calls, {t['input_tokens']:,} input / {t['output_tokens']:,} output tokens, "
          f"est. cost ${t['cost_usd']:.4f}  (log: {usage_log.LOG_FILE})")


if __name__ == "__main__":
    sys.exit(main())
