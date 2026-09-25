import json
import os
from bs4 import BeautifulSoup

script_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(script_dir, "eval_set_html.jsonl"), "r") as f:
    for line in f:
        record = json.loads(line)
        soup = BeautifulSoup(record["html"], "html.parser")
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else "(NO TITLE)"
        print(f"UID {record['uid']}: {title}")