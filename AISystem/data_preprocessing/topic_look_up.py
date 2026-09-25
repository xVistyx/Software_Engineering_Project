import pandas as pd
import json
import os

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

df = pd.read_csv(os.path.join(data_dir, "curlie.csv.gz"), compression="gzip")
df_en = df[df['lang'] == 'en']
uid_to_label = dict(zip(df_en['uid'], df_en['label']))

topics = []
with open("html_content_english.jsonl", "r") as f:
    for line in f:
        uid = json.loads(line)["uid"]
        label = uid_to_label.get(uid)
        if label:
            topics.append('/'.join(label.split('/')[2:4]))

print(f"Total topics collected: {len(topics)}")
result = pd.Series(topics).value_counts()
print(result.head(20))