"""
Dataset Manifest & Verification Script
Calculates SHA-256 checksums, row counts, and schema summaries for synthetic dataset files.
"""

import os
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import json
import hashlib
import pandas as pd

DATA_FILES = [
    "train.csv",
    "train_oracle.csv",
    "val.csv",
    "val_oracle.csv",
    "test.csv",
    "test_oracle.csv"
]

def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def generate_manifest(data_dir: str = "data/synthetic", output_file: str = "data/synthetic/checksums.json"):
    manifest = {}
    print(f"Generating dataset manifest for files in {data_dir}...")
    
    for filename in DATA_FILES:
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            print(f"Warning: File {filepath} does not exist. Skipping.")
            continue
            
        sha256_hash = compute_sha256(filepath)
        df = pd.read_csv(filepath)
        
        manifest[filename] = {
            "size_bytes": os.path.getsize(filepath),
            "sha256": sha256_hash,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns)
        }
        print(f"  [OK] {filename}: {len(df)} rows | SHA-256: {sha256_hash[:12]}...")
        
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Dataset manifest written to {output_file}\n")

if __name__ == "__main__":
    generate_manifest()
