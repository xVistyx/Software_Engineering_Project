import pandas as pd

df = pd.read_csv("curlie.csv.gz", compression="gzip")
print(df.head())
print(df.shape)

