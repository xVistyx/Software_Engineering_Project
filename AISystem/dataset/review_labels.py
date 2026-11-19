"""
Compare your hand labels (data/page_reviews_1.jsonl, _2, ...) with the AI labels (data/page_reviews_ai.jsonl).

    python 4c_compare_reviews.py

Prints the agreement rate on the pages you reviewed, a confusion table, and the disagreements.
"""
import json, glob, collections
from pathlib import Path

script_dir = Path(__file__).resolve().parent
cfg = json.load(open(script_dir / "dataset_config.json"))
data_dir = script_dir / cfg["output_dir"]

def load(files):
    out = {}
    for f in files:
        for l in open(f, encoding="utf-8"):
            if l.strip():
                r = json.loads(l); out[r["page_id"]] = r["verdict"]
    return out

ai = load([data_dir / "page_reviews_ai.jsonl"])
human = load(sorted(p for p in data_dir.glob("page_reviews_*.jsonl") if "ai" not in p.stem))
pages = {json.loads(l)["page_id"]: json.loads(l) for l in open(data_dir / "pages.jsonl", encoding="utf-8") if l.strip()}

both = [p for p in human if p in ai]
print(f"{len(human)} human labels, {len(both)} also labelled by the AI")
if not both:
    raise SystemExit("nothing to compare yet")

agree = sum(human[p] == ai[p] for p in both)
print(f"\nexact agreement (y/n/d): {agree}/{len(both)} = {agree/len(both):.1%}")

# agreement on the labels that actually matter for training: y vs n, ignoring pages either side dropped
yn = [p for p in both if human[p] in "yn" and ai[p] in "yn"]
a2 = sum(human[p] == ai[p] for p in yn)
print(f"y-vs-n agreement (where both said y or n): {a2}/{len(yn)} = {a2/max(len(yn),1):.1%}")

# of the pages the AI wanted to keep (y/n), how many would you also keep?
kept = [p for p in both if ai[p] in "yn"]
print(f"AI kept {len(kept)}; you also kept {sum(human[p] in 'yn' for p in kept)}")

print("\nconfusion (rows = human, cols = AI)")
c = collections.Counter((human[p], ai[p]) for p in both)
print("      " + "".join(f"{k:>6}" for k in "ynd"))
for h in "ynd":
    print(f"  {h}   " + "".join(f"{c[(h,a)]:>6}" for a in "ynd"))

print("\ndisagreements (first 25):")
for p in [p for p in both if human[p] != ai[p]][:25]:
    pg = pages[p]
    print(f"  human={human[p]} ai={ai[p]} | {pg['topic']:<12} | {pg['final_domain'][:28]:<28} | {pg['title'][:55]}")