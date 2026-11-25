"""Chunked schema/quality inspection for the Eclipse JDT CSV."""
import argparse
import pandas as pd
from collections import Counter

p = argparse.ArgumentParser()
p.add_argument("csv_path")
p.add_argument("--chunksize", type=int, default=25000)
a = p.parse_args()
missing, dist = Counter(), {c: Counter() for c in ["Severity", "Priority", "Status", "Resolution"]}
total = 0
for frame in pd.read_csv(a.csv_path, chunksize=a.chunksize, low_memory=False):
    total += len(frame)
    for c in frame.columns: missing[c] += frame[c].isna().sum()
    for c in dist:
        if c in frame: dist[c].update(frame[c].fillna("MISSING").astype(str).value_counts().to_dict())
print(f"Records: {total:,}; columns: {len(frame.columns)}")
print("Columns:", list(frame.columns))
print("Missing:", dict(missing))
for c, values in dist.items(): print(f"{c}: {dict(values)}")
