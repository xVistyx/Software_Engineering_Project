"""
Stage 1: sample links per topic from curlie.csv.gz.
Output: data/links.csv  (link_id, uid, url, domain, label, topic, role)
role = "study" for the topics, "negative" for the clearly irrelevant groups.
Run from anywhere:  python 1_sample_links.py
"""
import json
from pathlib import Path
from urllib.parse import urlparse
import pandas as pd

script_dir = Path(__file__).resolve().parent
cfg = json.load(open(script_dir / "dataset_config.json"))
out_dir = script_dir / cfg["output_dir"]
out_dir.mkdir(exist_ok=True)

#load and clean the dataset
df = pd.read_csv((script_dir / cfg["curlie_path"]).resolve())
print(f"{len(df)} rows in curlie.csv.gz")
df = df[df["lang"] == "en"]                                         # label language only
print(f"{len(df)} rows with lang == 'en'")
df = df.dropna(subset=["url", "label"]).copy()
df["url"] = df["url"].astype(str).str.strip()
df = df[df["url"] != ""]

# curlie urls are stored without a https so add https://
has_scheme = df["url"].str.match(r"^https?://", case=False)
df["url"] = df["url"].where(has_scheme, "https://" + df["url"])
df["domain"] = df["url"].map(lambda u: urlparse(u).netloc.lower().removeprefix("www."))
df = df[df["domain"] != ""]
df = df.drop_duplicates("url")
df["uid"] = df["uid"].astype(str)
print(f"{len(df)} usable rows after cleaning and de-duplication")

used_urls = set()
domain_counts = {}         

def pick(prefixes, n):
    mask = df["label"].map(lambda l: any(p in l for p in prefixes))
    sub = df[mask & ~df["url"].isin(used_urls)]
    sub = sub.sample(frac=1, random_state=cfg["seed"])                  # shuffle
    room = sub["domain"].map(lambda d: cfg["max_links_per_domain"] - domain_counts.get(d, 0))
    sub = sub[sub.groupby("domain").cumcount() < room]                  #cap per domain
    sub = sub.head(n)
    used_urls.update(sub["url"])
    for d in sub["domain"]:
        domain_counts[d] = domain_counts.get(d, 0) + 1
    return sub, int(mask.sum())

#sample
parts = []
for role, groups, n in [("study", cfg["topics"], cfg["links_per_topic"]),
                        ("negative", cfg["negatives"], cfg["links_per_negative_group"])]:
    for name, prefixes in groups.items():
        sub, matched = pick(prefixes, n)
        sub = sub.assign(topic=name, role=role)
        parts.append(sub)
        flag = "   <-- CHECK THE LABEL PATH" if matched == 0 else ("   <-- fewer than requested" if len(sub) < n else "")
        print(f"{role:8s} {name:18s} matched {matched:7d}  picked {len(sub):5d}{flag}")

links = pd.concat(parts, ignore_index=True)
links.insert(0, "link_id", [f"link_{i:05d}" for i in range(1, len(links) + 1)])
links = links[["link_id", "uid", "url", "domain", "label", "topic", "role"]]
links.to_csv(out_dir / "links.csv", index=False)
print(f"wrote {len(links)} links to {out_dir / 'links.csv'}")