import pandas as pd
df = pd.read_csv("AISystem/curlie.csv.gz")
print(len(df), df.columns.tolist())
print(df.head(5).to_string())
print(df["lang"].value_counts(dropna=False).head(10))
print((df["lang"] == "en").sum(), "rows with lang == 'en'")
print(df["url"].isna().sum(), "missing url;", df["label"].isna().sum(), "missing label")
print(df["url"].astype(str).str.slice(0, 8).value_counts().head(8))