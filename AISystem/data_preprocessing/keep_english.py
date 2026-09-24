import pandas as pd
import gzip
import json
import os

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

#english label's uid
df = pd.read_csv(os.path.join(data_dir, "curlie.csv.gz"), compression="gzip")
df_en = df[df['lang'] == 'en']
english_uids = set(df_en['uid'])
print(f"English-labeled uids: {len(english_uids)}")

#run through html file
with gzip.open(os.path.join(data_dir, "html_content.json.gz"), "rt") as infile, \
     open("html_content_english.jsonl", "w") as outfile:
    kept = 0
    for i, line in enumerate(infile):
        record = json.loads(line)
        if record["uid"] in english_uids:
            outfile.write(line)
            kept += 1
        if i % 50000 == 0:
            print(f"scanned {i}, kept {kept}")

print(f"English pages: {kept}")