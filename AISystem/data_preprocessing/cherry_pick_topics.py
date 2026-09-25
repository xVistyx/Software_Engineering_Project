import pandas as pd
import json
import os
import re
import random
import time
from bs4 import BeautifulSoup

script_dir = os.path.dirname(os.path.abspath(__file__))
aisystem_dir = os.path.join(script_dir, "..")

random.seed(42)

TOPICS = [
    "Reference/Education",
    "Computers/Software",
    "Society/Law",
    "Health/Medicine",
    "Science/Social_Sciences",
    "Arts/Music",
    "Science/Math",
]

BAD_TITLES = {"", "untitled", "untitled document", "home", "welcome", "loading", "loading...", "welcome!"}

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

def extract_title_fast(html):
    match = TITLE_RE.search(html)
    if not match:
        return ""
    raw = match.group(1)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw

def is_valid_title(title):
    return title.strip().lower() not in BAD_TITLES and len(title.strip()) > 0

def get_full_record_by_uid(target_uid, filepath):
    """Scan the file once to find one specific record's full html. Used sparingly, on demand."""
    with open(filepath, "r") as f:
        for line in f:
            record = json.loads(line)
            if record["uid"] == target_uid:
                return record
    return None

# --- Step 0: load Curlie labels ---
df = pd.read_csv(os.path.join(aisystem_dir, "curlie.csv.gz"), compression="gzip")
df_en = df[df['lang'] == 'en'].copy()
df_en['two_level'] = df_en['label'].apply(lambda x: '/'.join(x.split('/')[2:4]))
df_en['top_level'] = df_en['label'].apply(lambda x: x.split('/')[2] if len(x.split('/')) > 2 else '')
english_uids = set(df_en['uid'])

# --- Step 1: fast single pass — regex title extraction only, no DOM parsing ---
print("Scanning html_content_english.jsonl for valid titles (fast regex pass)...")
html_path = os.path.join(script_dir, "html_content_english.jsonl")

uid_title = {}
checked = 0
start = time.time()

with open(html_path, "r") as f:
    for line in f:
        record = json.loads(line)
        uid = record["uid"]
        if uid not in english_uids:
            continue
        checked += 1
        title = extract_title_fast(record["html"])
        if is_valid_title(title):
            uid_title[uid] = title
        if checked % 50000 == 0:
            elapsed = time.time() - start
            rate = checked / elapsed
            remaining = (len(english_uids) - checked) / rate if rate > 0 else 0
            print(f"  scanned {checked}, {len(uid_title)} valid titles, ~{remaining/60:.1f} min remaining")

print(f"Done in {(time.time()-start)/60:.1f} min. {len(uid_title)} valid-title pages out of {checked} checked.\n")
valid_uids = set(uid_title.keys())

df_matched = df_en[df_en['uid'].isin(valid_uids)].copy()

topic_top_levels = set(t.split('/')[0] for t in TOPICS)
unrelated_pool = df_matched[~df_matched['top_level'].isin(topic_top_levels)]
easy_no_pool = unrelated_pool.sample(len(TOPICS), random_state=42)

picks = []
used_uids = set()

for i, topic in enumerate(TOPICS):
    top_level = topic.split('/')[0]

    same_cat = df_matched[(df_matched['two_level'] == topic) & (~df_matched['uid'].isin(used_uids))]
    easy_yes = same_cat.sample(min(2, len(same_cat)), random_state=42)
    for _, row in easy_yes.iterrows():
        picks.append({"topic": topic, "tier": "easy_yes", "uid": row['uid'], "url": row['url'], "label": row['label']})
        used_uids.add(row['uid'])

    same_top_diff_sub = df_matched[(df_matched['top_level'] == top_level) & (df_matched['two_level'] != topic) & (~df_matched['uid'].isin(used_uids))]
    if len(same_top_diff_sub) > 0:
        hard_no = same_top_diff_sub.sample(1, random_state=42)
        for _, row in hard_no.iterrows():
            picks.append({"topic": topic, "tier": "hard_no", "uid": row['uid'], "url": row['url'], "label": row['label']})
            used_uids.add(row['uid'])
    else:
        print(f"WARNING: no hard-no candidates found for {topic}")

    easy_no_row = easy_no_pool.iloc[i]
    picks.append({"topic": topic, "tier": "easy_no", "uid": easy_no_row['uid'], "url": easy_no_row['url'], "label": easy_no_row['label']})
    used_uids.add(easy_no_row['uid'])

    # --- interactive ambiguous selection ---
    print("\n" + "=" * 80)
    print(f"TOPIC: {topic}  —  finding an AMBIGUOUS candidate")
    print("=" * 80)

    candidate_pool = df_matched[
        (df_matched['top_level'] == top_level) &
        (df_matched['two_level'] != topic) &
        (~df_matched['uid'].isin(used_uids))
    ].sample(frac=1, random_state=random.randint(0, 99999))

    chosen_uid = None
    chosen_row = None
    for _, row in candidate_pool.iterrows():
        uid = row['uid']
        print(f"\n[Topic: {topic}]")
        print(f"Curlie label: {row['label']}")
        print(f"Title: {uid_title[uid]}")
        print(f"URL: {row['url']}")
        answer = input("Accept as ambiguous? (y/n): ").strip().lower()
        used_uids.add(uid)
        if answer == 'y':
            chosen_uid = uid
            chosen_row = row
            break

    if chosen_uid:
        picks.append({"topic": topic, "tier": "ambiguous", "uid": chosen_row['uid'], "url": chosen_row['url'], "label": chosen_row['label']})
        print(f"Accepted for {topic}: {uid_title[chosen_uid]}")
    else:
        picks.append({"topic": topic, "tier": "ambiguous", "uid": None, "url": None, "label": "NO SUITABLE CANDIDATE FOUND"})
        print(f"No candidate accepted for {topic} — leaving blank.")

picks_df = pd.DataFrame(picks)
picks_df.to_csv(os.path.join(script_dir, "eval_set_candidates.csv"), index=False)
print(f"\nBuilt {len(picks_df)} picks ({picks_df['uid'].isna().sum()} unresolved)")

# --- Step 2: second pass — pull full HTML only for the final chosen uids ---
target_uids = set(picks_df['uid'].dropna())
print(f"Fetching full HTML for {len(target_uids)} chosen pages...")

found = {}
with open(html_path, "r") as infile:
    for line in infile:
        record = json.loads(line)
        if record["uid"] in target_uids:
            found[record["uid"]] = record
        if len(found) == len(target_uids):
            break

with open(os.path.join(script_dir, "eval_set_html.jsonl"), "w") as outfile:
    for uid in target_uids:
        if uid in found:
            outfile.write(json.dumps(found[uid]) + "\n")
        else:
            print(f"WARNING: uid {uid} not found")

print(f"Saved {len(found)} matched HTML records to eval_set_html.jsonl")