import gzip
import json

with gzip.open("html_content.json.gz", "rt") as f:
    for i, line in enumerate(f):
        record = json.loads(line)
        print(record.keys())          # should show uid, html
        print(record["uid"])
        print(record["html"][:500])   # first 500 chars of the HTML
        if i >= 2:
            break