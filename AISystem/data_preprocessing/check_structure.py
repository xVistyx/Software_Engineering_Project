import json
import os
from bs4 import BeautifulSoup
from collections import Counter

script_dir = os.path.dirname(os.path.abspath(__file__))

tag_presence = Counter()
content_lengths = {"title": [], "meta_description": [], "first_paragraph": []}
total_checked = 0

with open(os.path.join(script_dir, "eval_set_html.jsonl"), "r") as f:
    for line in f:
        record = json.loads(line)
        soup = BeautifulSoup(record["html"], "html.parser")
        total_checked += 1

        # presence checks
        title_tag = soup.find("title")
        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        heading_tag = soup.find(["h1", "h2", "h3", "h4"])
        para_tag = soup.find("p")
        og_title_tag = soup.find("meta", attrs={"property": "og:title"})
        og_desc_tag = soup.find("meta", attrs={"property": "og:description"})
        jsonld_tag = soup.find("script", attrs={"type": "application/ld+json"})

        if title_tag: tag_presence['has_title'] += 1
        if meta_desc_tag: tag_presence['has_meta_description'] += 1
        if heading_tag: tag_presence['has_heading'] += 1
        if para_tag: tag_presence['has_paragraph'] += 1
        if og_title_tag: tag_presence['has_og_title'] += 1
        if og_desc_tag: tag_presence['has_og_description'] += 1
        if jsonld_tag: tag_presence['has_jsonld'] += 1

        # content length checks (quality signal, not just presence)
        if title_tag:
            content_lengths["title"].append(len(title_tag.get_text(strip=True)))
        if meta_desc_tag:
            content_lengths["meta_description"].append(len(meta_desc_tag.get("content", "").strip()))
        if para_tag:
            content_lengths["first_paragraph"].append(len(para_tag.get_text(strip=True)))

        # flag suspiciously thin/placeholder titles
        if title_tag:
            title_text = title_tag.get_text(strip=True).lower()
            if title_text in ("", "untitled", "home", "loading...", "loading"):
                tag_presence['suspicious_title'] += 1

print(f"Checked {total_checked} pages\n")

print("--- Presence ---")
for tag, count in tag_presence.items():
    print(f"{tag}: {count}/{total_checked} ({100*count/total_checked:.1f}%)")

print("\n--- Content length (chars) ---")
for field, lengths in content_lengths.items():
    if lengths:
        avg = sum(lengths) / len(lengths)
        print(f"{field}: avg={avg:.0f}, min={min(lengths)}, max={max(lengths)}, n={len(lengths)}")
    else:
        print(f"{field}: no data")