import json
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

SRC = Path("pack-src")
ids = json.loads((SRC / "_ids.json").read_text())
assert ids == sorted(p.stem.replace("__", "/") for p in (SRC / "content").glob("*.json")), "id mismatch"
texts = []
for cid in ids:
    d = json.loads((SRC / "content" / (cid.replace("/", "__") + ".json")).read_text())
    t = d["text"]
    if d["kind"] == "qa":
        q = json.loads(t)
        t = q["question"]
    texts.append(t[:2000])
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
emb = model.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
assert emb.shape == (len(ids), 384)
(SRC / "index").mkdir(exist_ok=True)
np.savez_compressed(SRC / "index" / "embeddings.npz", ids=np.array(ids), emb=emb.astype(np.float32))
print("embeddings:", emb.shape)
