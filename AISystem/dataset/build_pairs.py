"""
Stage 3: combine pages and queries into labelled (query, page) pairs.

Reads:   data/pages.jsonl, queries.json, dataset_config.json ("pairs" section)
Writes:  data/queries.jsonl   one row per query phrasing
         data/pairs.jsonl     one row per (query, page) pair

Each pair carries the page fields (title, description, ...) so it can be fed straight to
Model.train / Model.evaluate: {"query", "page", "relevant", "tier"}.

Label meaning: relevant = True means "do not block", False means "block".

If data/page_reviews_*.jsonl exist (stage 4), only pages a human marked y or n are used:
  y = not a distraction -> relevant True      n = distraction -> relevant False      d = dropped
Without reviews, labels come from the Curlie topic alone (see tiers below).

Tiers:
  easy_yes     query of topic T + page of topic T                    -> relevant True
  easy_no      query of any topic + page from a distraction group    -> relevant False
               (Games, Sports, Shopping, Movies, ...)
  cross_topic  query of topic T + page of a different study topic    -> relevant True
               (a Chemistry page during a Physics session is not a distraction, so not blocked)
"""
import json, random
from pathlib import Path

script_dir = Path(__file__).resolve().parent
cfg = json.load(open(script_dir / "dataset_config.json"))
data_dir = script_dir / cfg["output_dir"]
pc = cfg["pairs"]
rng = random.Random(cfg["seed"])

queries = json.load(open(script_dir / cfg["queries_path"]))
study_topics = list(cfg["topics"])
missing = [t for t in study_topics if t not in queries]
if missing:
    raise SystemExit(f"queries.json has no phrasings for: {missing}")

# query table: stable ids, so pairs can point to them
query_rows = [
    {"query_id": f"q_{t}_{i + 1}", "topic": t, "text": text}
    for t in study_topics for i, text in enumerate(queries[t])
]
by_topic = {t: [q for q in query_rows if q["topic"] == t] for t in study_topics}

pages = [json.loads(l) for l in open(data_dir / "pages.jsonl", encoding="utf-8") if l.strip()]
print(f"{len(pages)} pages")

reviews = {}
# AI labels first, then human files: a human answer always overrides an AI answer for the same page
for rf in sorted(data_dir.glob("page_reviews_*.jsonl"), key=lambda f: (0 if "ai" in f.stem else 1, f.name)):
    for l in open(rf, encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            reviews[r["page_id"]] = r["verdict"]
if reviews:
    pages = [p for p in pages if reviews.get(p["page_id"]) in ("y", "n")]
    print(f"{len(reviews)} reviewed pages -> keeping {len(pages)} (y or n), dropping the rest")

pairs = []

def add(query, page, relevant, tier):
    pairs.append({
        "pair_id": f"pair_{len(pairs) + 1:06d}",
        "query_id": query["query_id"], "query": query["text"], "query_topic": query["topic"],
        "page_id": page["page_id"], "page_topic": page["topic"], "domain": page["final_domain"],
        "page": {k: page.get(k, "") for k in ("title", "description", "h1", "snippet")},
        "relevant": relevant, "tier": tier,
        "label_source": "rule", "needs_review": relevant is None,
    })

skipped = 0
for page in pages:
    # human verdict if there is one, otherwise guess from the Curlie group
    v = reviews.get(page["page_id"]) or ("y" if page["role"] == "study" else "n")
    own = by_topic.get(page["topic"]) if page["role"] == "study" else None
    if v == "y":
        if own:
            for q in rng.sample(own, min(pc["easy_yes_per_page"], len(own))):
                add(q, page, True, "easy_yes")
            other_topics, n_other = [t for t in study_topics if t != page["topic"]], pc["cross_topic_per_page"]
        else:   # a page from a distraction group that a human says is fine
            other_topics, n_other = study_topics, pc["easy_yes_per_page"] + pc["cross_topic_per_page"]
        for _ in range(n_other):
            add(rng.choice(by_topic[rng.choice(other_topics)]), page, True, "cross_topic")
    elif v == "n":
        # a different topic each time, so a distracting page is paired with many kinds of study goals
        for t in rng.sample(study_topics, min(pc["easy_no_per_page"], len(study_topics))):
            add(rng.choice(by_topic[t]), page, False, "easy_no")
    else:
        skipped += 1

with open(data_dir / "queries.jsonl", "w", encoding="utf-8") as f:
    for q in query_rows:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")
with open(data_dir / "pairs.jsonl", "w", encoding="utf-8") as f:
    for p in pairs:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

print(f"{len(query_rows)} queries, {len(pairs)} pairs ({skipped} pages skipped)")
for tier in ["easy_yes", "easy_no", "cross_topic"]:
    n = sum(p["tier"] == tier for p in pairs)
    if n:
        print(f"  {tier:12s} {n}")
print(f"wrote {data_dir / 'pairs.jsonl'}")