"""
Zero-shot baseline: load Qwen3-4B (no adapter) and score it on the test set.

    python main.py                 # all of dataset/data/test.jsonl
    python main.py --limit 20      # quick smoke test on 20 pairs first
"""
import argparse
import json
from pathlib import Path

from qwen_model import Qwen3Model

script_dir = Path(__file__).resolve().parent

def read_jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(script_dir / "model_config.json"))
    ap.add_argument("--test", default=str(script_dir / "dataset" / "data" / "test.jsonl"))
    ap.add_argument("--limit", type=int, default=None, help="only use the first N test pairs")
    args = ap.parse_args()

    test_rows = read_jsonl(args.test)
    if args.limit:
        test_rows = test_rows[: args.limit]    
    print(f"{len(test_rows)} test pairs")

    model = Qwen3Model(args.config)
    model.load()

    metrics = model.evaluate(test_rows)
    print(json.dumps(metrics, indent=2))

    out = script_dir / "results_zero_shot.json"
    with open(out, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"saved {out}")