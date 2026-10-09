# CBSE Class 9-10 Math/Science content pack v1 (REM-1 / mk-025 rebuild)

Build pipeline (run from a workspace dir containing `pdfs/` with the NCERT
chapter PDFs fetched from https://ncert.nic.in/textbook/pdf/<code><nn>.pdf):

1. `extract_build_src.py` — pymupdf text extraction -> mspack source dir
   (`pack-src/manifest.json` + `content/*.json`, kinds: text + qa).
2. `embed.py` — all-MiniLM-L6-v2 384-dim normalized embeddings ->
   `pack-src/index/embeddings.npz`.
3. `mspack build pack-src -o dist/cbse-class9-10-math-science-1.0.0.mspx`
   (schema v0 envelope: AES-256-GCM, HKDF-SHA256, dev key unless
   `MS_MASTER_KEY` set).
4. `mspack verify` + `sign_validate.py` — schema validation, sha256
   signature, license metadata (CC-BY-NC-SA-4.0).

Provenance: Class 9 Ganita Ver 1.0 Part I (iemh1, 8 ch), Class 9 Science
Exploration (iesc1, 13), Class 10 Mathematics (jemh1, 13), Class 10
Science (jesc1, 13). Class 9 math ch 9-12 PDFs are 404 on ncert.nic.in
(verified 2026-10-09) — not available in English Part I numbering.
