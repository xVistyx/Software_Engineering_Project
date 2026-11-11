
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
    ap.add_argument("--adapter", default=None, help="path to a saved LoRA adapter to evaluate instead of zero-shot")
    ap.add_argument("--limit", type=int, default=None, help="only use the first N test pairs")
    args = ap.parse_args()

    test_rows = read_jsonl(args.test)
    if args.limit:
        test_rows = test_rows[: args.limit]      # test.jsonl is shuffled, so this is a random subset
    print(f"{len(test_rows)} test pairs")

    model = Qwen3Model(args.config)
    if args.adapter:
        model.config["model"]["adapter_path"] = args.adapter
    model.load()

    metrics = model.evaluate(test_rows)
    print(json.dumps(metrics, indent=2))

    out = script_dir / ("results_adapter.json" if args.adapter else "results_zero_shot.json")
    with open(out, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"saved {out}")