"""
Stage 5: split the pairs into train / val / test.

Reads:   data/pairs_reviewed.jsonl (if you ran stage 4 merge) else data/pairs.jsonl,
         data/queries.jsonl, dataset_config.json ("split" section)
Writes:  data/train.jsonl, data/val.jsonl, data/test.jsonl
         each row: {"pair_id", "query", "page": {...}, "relevant", "tier", ...}
         = the format Model.train / Model.evaluate expect.

Two things keep the test score honest:
  1. Split by DOMAIN: every page of a site lands in one split, so the model can't memorise a site.
  2. Held-out query phrasings: val and test use phrasings of the study goal that never appear in train.
     (Pairs keep their topic, but the query text is redrawn from the split's own phrasings.)
Pairs without a label (relevant = null) are dropped.
"""
import json, random
from collections import Counter
from pathlib import Path

script_dir = Path(__file__).resolve().parent
cfg = json.load(open(script_dir / "dataset_config.json"))
data_dir = script_dir / cfg["output_dir"]
sc = cfg["split"]
rng = random.Random(cfg["seed"])


def read_jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]

src = data_dir / "pairs_reviewed.jsonl"
if not src.exists():
    src = data_dir / "pairs.jsonl"
pairs = [p for p in read_jsonl(src) if p["relevant"] is not None]
pairs.sort(key=lambda p: p["pair_id"])
print(f"{len(pairs)} labelled pairs from {src.name}")

# --- 1. domains -> splits ---------------------------------------------------
domains = sorted({p["domain"] for p in pairs})
rng.shuffle(domains)
n_val, n_test = int(len(domains) * sc["val"]), int(len(domains) * sc["test"])
split_of = {}
for i, d in enumerate(domains):
    split_of[d] = "val" if i < n_val else "test" if i < n_val + n_test else "train"
print(f"{len(domains)} domains -> train {len(domains) - n_val - n_test}, val {n_val}, test {n_test}")

# --- 2. query phrasings -> splits (per topic) --------------------------------
held = sc["heldout_queries_per_topic"]
by_topic = {}
for q in read_jsonl(data_dir / "queries.jsonl"):
    by_topic.setdefault(q["topic"], []).append(q)
allowed = {"train": {}, "val": {}, "test": {}}
for topic, qs in by_topic.items():
    qs = sorted(qs, key=lambda q: q["query_id"])
    rng.shuffle(qs)
    k_test, k_val = held["test"], held["val"]
    if len(qs) <= k_test + k_val + 1:
        raise SystemExit(f"{topic}: only {len(qs)} phrasings, need more than {k_test + k_val + 1}")
    allowed["test"][topic] = qs[:k_test]
    allowed["val"][topic] = qs[k_test:k_test + k_val]
    allowed["train"][topic] = qs[k_test + k_val:]

# --- 3. assign pairs, redraw the query inside the split's phrasings ----------
splits = {"train": [], "val": [], "test": []}
for p in pairs:
    s = split_of[p["domain"]]
    q = rng.choice(allowed[s][p["query_topic"]])
    p["query_id"], p["query"] = q["query_id"], q["text"]
    splits[s].append(p)

# --- 4. optional class balance (downsample the bigger class) ----------------
for s in sc["balance"]:
    yes = [p for p in splits[s] if p["relevant"]]
    no = [p for p in splits[s] if not p["relevant"]]
    n = min(len(yes), len(no))
    print(f"balancing {s}: {len(yes)} relevant / {len(no)} block -> {n} / {n}")
    splits[s] = rng.sample(yes, n) + rng.sample(no, n)
    splits[s].sort(key=lambda p: p["pair_id"])

# --- 5. checks and output ----------------------------------------------------
dom = {s: {p["domain"] for p in v} for s, v in splits.items()}
assert not (dom["train"] & dom["val"] or dom["train"] & dom["test"] or dom["val"] & dom["test"]), "domain leak"
qid = {s: {p["query_id"] for p in v} for s, v in splits.items()}
assert not (qid["train"] & qid["val"] or qid["train"] & qid["test"] or qid["val"] & qid["test"]), "query leak"

for s, rows in splits.items():
    rng.shuffle(rows)
    with open(data_dir / f"{s}.jsonl", "w", encoding="utf-8") as f:
        for p in rows:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    tiers = Counter(p["tier"] for p in rows)
    yes = sum(p["relevant"] for p in rows)
    print(f"{s:5s} {len(rows):6d} pairs | relevant {yes}, block {len(rows) - yes} | "
          + ", ".join(f"{t} {n}" for t, n in sorted(tiers.items())))
print("checks passed: no domain or query phrasing appears in more than one split")