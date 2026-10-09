import hashlib, json, sys
from pathlib import Path
import jsonschema

dist = Path("dist")
mspx = dist / "cbse-class9-10-math-science-1.0.0.mspx"
h = hashlib.sha256(mspx.read_bytes()).hexdigest()
(disp := dist / (mspx.name + ".sha256")).write_text(h + "\n")

sig = {
    "pack_id": "cbse-class9-10-math-science",
    "version": "1.0.0",
    "file": mspx.name,
    "algorithm": "sha256",
    "sha256": h,
    "signer": "fleet-dev (sha256 content signature; ed25519 deferred to fleet KMS)",
    "signed_at": "2026-10-09T11:25:00+00:00",
}
(dist / (mspx.name + ".sig.json")).write_text(json.dumps(sig, indent=2))

lic = {
    "effective_license": "CC-BY-NC-SA-4.0",
    "license_url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "sources": [{"source": "NCERT", "url": "https://ncert.nic.in",
                 "license": "CC-BY-NC-SA-4.0"}],
    "packs": [sig["file"]],
}
(dist / "license.json").write_text(json.dumps(lic, indent=2))

# independent schema validation of the verified manifest
schema = json.loads(Path("/home/huntingvision/harness/makesense-core/packs/schema/pack-manifest-v0.schema.json").read_text())
man = json.loads((dist / "manifest.verify.json").read_text())
jsonschema.validate(man, schema)
print("schema validation: PASS")
n_text = sum(1 for c in man["index"] if c["kind"] == "text")
n_qa = sum(1 for c in man["index"] if c["kind"] == "qa")
print(f"chunks: {man['stats']['chunks']} (text={n_text}, qa={n_qa})")
print("sha256:", h)
print("OK")
