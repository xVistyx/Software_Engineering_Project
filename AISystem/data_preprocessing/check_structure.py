import json
from bs4 import BeautifulSoup
from collections import Counter

tag_presence = Counter()
total_checked = 0
sample_size = 200  # keep it small first, just to sanity check



with open("html_content_english.jsonl", "r") as f:
    for i, line in enumerate(f):
        if i >= sample_size:
            break
        record = json.loads(line)
        soup = BeautifulSoup(record["html"], "html.parser")

        total_checked += 1
        if soup.find(['h1', 'h2', 'h3', 'h4']):
            tag_presence['has_heading'] += 1
        if soup.find('p'):
            tag_presence['has_paragraph'] += 1
        if soup.find('title'):
            tag_presence['has_title'] += 1
        if soup.find('meta', attrs={'name': 'description'}):
            tag_presence['has_meta_description'] += 1

print(f"Checked {total_checked} pages")
for tag, count in tag_presence.items():
    print(f"{tag}: {count}/{total_checked} ({100*count/total_checked:.1f}%)")