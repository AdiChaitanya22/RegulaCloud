import json
import os
import time
import hashlib
from typing import List, Dict, Any

def get_manifest():
    with open("benchmarks/manifest.json", "r") as f:
        return json.load(f)

def get_rl_states():
    with open("benchmarks/rl/states.json", "r") as f:
        return json.load(f)

def verify_hashes():
    with open("benchmarks/manifest.json", "rb") as f:
        m_hash = hashlib.sha256(f.read()).hexdigest()
    with open("benchmarks/rl/states.json", "rb") as f:
        r_hash = hashlib.sha256(f.read()).hexdigest()
    assert m_hash == "fccdecf583df9a3d655a7eb88eb593fedb292bc201c13189d2c1ce8a29096b9e", "Manifest hash mismatch"
    assert r_hash == "29b1eb0718e408681318b4918fbcaf96eb86cc2d55bd938c0437bdbd051146b5", "RL state hash mismatch"
    return m_hash, r_hash

def write_csv(path, headers, rows):
    with open(path, "w") as f:
        f.write(",".join(headers) + "\n")
        for row in rows:
            f.write(",".join(str(x) for x in row) + "\n")

def get_smoke_dir():
    d = f"benchmark_results/DEVELOPMENT-SMOKE-{int(time.time())}"
    os.makedirs(d, exist_ok=True)
    return d
