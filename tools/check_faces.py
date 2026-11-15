"""Check generated review records against the canonical full face bank."""
from pathlib import Path
import hashlib, json
p = Path(__file__).resolve().parents[1] / "preview"
full = (p / "faces.bin").read_bytes()
review = (p / "review.bin").read_bytes()
manifest = json.loads((p / "manifest.json").read_text())
assert len(full) == 30 * 1024
assert len(review) == len(manifest["review_ids"]) * 1025
assert hashlib.sha256(review).hexdigest() == manifest["review_sha256"]
for i, n in enumerate(manifest["review_ids"]):
    record = review[i*1025:(i+1)*1025]
    assert record[0] == n
    assert record[1:] == full[(n-1)*1024:n*1024]
print("PASS: review IDs, frames and SHA256 match the full bank")
