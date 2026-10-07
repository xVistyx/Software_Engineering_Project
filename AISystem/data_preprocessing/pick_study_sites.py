"""
Pick candidate study sites from the Curlie dataset, keeping their uid.

Put in AISystem/data_preprocessing/ and run:  python pick_study_sites.py
Output: study_sites_candidates.csv  (uid, topic, url, label, title, keep)
Open it, set keep=1 for the ones that are good (aim for 6 per topic = 60).
"""
import re, json, random
from pathlib import Path
import pandas as pd

script_dir = Path(__file__).resolve().parent
aisystem_dir = script_dir.parent

HTML_FILE = script_dir / "html_content_english.jsonl"
CSV_FILE = aisystem_dir / "curlie.csv.gz"
OUT_FILE = script_dir / "study_sites_candidates.csv"

SAMPLE_PER_TOPIC = 25   # drawn at random per topic, before title filtering
KEEP_PER_TOPIC = 10     # candidates left per topic after filtering (you trim to 6)
SEED = 42

# topic -> substring that must appear in the Curlie label
TOPICS = {
    "Mathematics":      "/Science/Math/",
    "Physics":          "/Science/Physics/",
    "Chemistry":        "/Science/Chemistry/",
    "Biology":          "/Science/Biology/",
    "Computer_Science": "/Computers/Computer_Science/",
    "History":          "/Society/History/",
    "Economics":        "/Science/Social_Sciences/Economics/",
    "Psychology":       "/Science/Social_Sciences/Psychology/",
    "Philosophy":       "/Society/Philosophy/",
    "Law":              "/Society/Law/",
}

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
UID_RE = re.compile(r'"uid"\s*:\s*"?([^",}\s]+)')
BAD_TITLES = ("untitled", "home", "welcome", "loading", "index of", "404", "error")

# 1. choose candidate rows from the csv (label language = English)
df = pd.read_csv(CSV_FILE)
df = df[df["lang"] == "en"]
df["uid"] = df["uid"].astype(str)

rows = []
for topic, key in TOPICS.items():
    sub = df[df["label"].str.contains(key, regex=False, na=False)]
    print(f"{topic}: {len(sub)} rows in csv")
    sub = sub.sample(n=min(SAMPLE_PER_TOPIC, len(sub)), random_state=SEED)
    for _, r in sub.iterrows():
        rows.append({"uid": r["uid"], "topic": topic, "url": r["url"], "label": r["label"]})

wanted = {r["uid"] for r in rows}
print(f"Looking up {len(wanted)} uids in {HTML_FILE.name} ...")

# 2. one pass over the big html file, stop as soon as all are found
titles = {}
with open(HTML_FILE, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        m = UID_RE.search(line[:200])
        if not m or m.group(1) not in wanted:
            continue
        uid = m.group(1)
        html = json.loads(line).get("html") or ""
        t = TITLE_RE.search(html)
        titles[uid] = re.sub(r"\s+", " ", t.group(1)).strip() if t else ""
        if len(titles) == len(wanted):
            break
print(f"Found html for {len(titles)} / {len(wanted)}")

# 3. drop missing/bad titles, keep up to KEEP_PER_TOPIC per topic
out, count = [], {}
random.seed(SEED)
random.shuffle(rows)
for r in rows:
    t = titles.get(r["uid"], "")
    if len(t) < 5 or t.lower().startswith(BAD_TITLES):
        continue
    if count.get(r["topic"], 0) >= KEEP_PER_TOPIC:
        continue
    count[r["topic"]] = count.get(r["topic"], 0) + 1
    out.append({**r, "title": t, "keep": ""})

out = pd.DataFrame(out).sort_values(["topic", "uid"])
out.to_csv(OUT_FILE, index=False)
print(out.groupby("topic").size())
print(f"Wrote {OUT_FILE}")