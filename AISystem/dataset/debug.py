import pandas as pd
from pathlib import Path

script_dir = Path(__file__).resolve().parent
l = pd.read_csv(script_dir / "data" / "links.csv")
l = l[l["role"] == "study"]
l["sub"] = l["label"].str.split("/").str[3:6].str.join("/")
for t, g in l.groupby("topic"):
    print("\n==", t); print(g["sub"].value_counts().head(8).to_string())