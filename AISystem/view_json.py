import pandas as pd

mapping = pd.read_json("mapping.json.gz", orient="records", lines=True, compression="gzip")

# build reverse lookup: foreign label -> English label
label_to_english = {}
for _, row in mapping.iterrows():
    eng = row['english_label']
    for lang_name, foreign_label in row['matchings'].items():
        label_to_english[foreign_label] = eng

print(len(label_to_english))
print(label_to_english.get('/zh_TW/%E4%BC%91%E9%96%92/%E5%AF%B5%E7%89%A9'))