import argparse, json, random
from pathlib import Path

from qwen_model import Qwen3Model

script_dir = Path(__file__).resolve().parent
read = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(script_dir / "model_config.json"))
    ap.add_argument("--data", default=str(script_dir / "dataset" / "data"))
    ap.add_argument("--limit", type=int, default=None, help="use only N train / N val / N test rows (dry run)")
    ap.add_argument("--epochs", type=int, default=None)
    args = ap.parse_args()
    data = Path(args.data)

    model = Qwen3Model(args.config)
    if args.epochs:
        model.training_config["num_train_epochs"] = args.epochs
    model.load()

    train_rows, val_rows, test_rows = (read(data / f"{s}.jsonl") for s in ("train", "val", "test"))
    if args.limit:
        train_rows, val_rows, test_rows = (r[: args.limit] for r in (train_rows, val_rows, test_rows))
    # train() takes file paths, so write the (possibly shortened) rows to a scratch copy
    tmp = script_dir / "_tmp_split"; tmp.mkdir(exist_ok=True)
    for name, rows in (("train", train_rows), ("val", val_rows)):
        with open(tmp / f"{name}.jsonl", "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)

    model.train(str(tmp / "train.jsonl"), str(tmp / "val.jsonl"))

    metrics = model.evaluate(test_rows, save_path="predictions_finetuned.csv")
    print(json.dumps(metrics, indent=2))
    with open(script_dir / "results_finetuned.json", "w") as f:
        json.dump(metrics, f, indent=2)