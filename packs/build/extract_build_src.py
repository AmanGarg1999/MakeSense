"""Build CBSE Class 9-10 Math/Science content pack v1 (mspack schema v0 source).

Extracts text from NCERT chapter PDFs (downloaded from ncert.nic.in),
chunks by page (~1200 chars target), generates deterministic traceable
questions (Bloom levels), embeds chunks with all-MiniLM-L6-v2 (384-dim),
and writes an mspack-source directory: manifest.json + content/*.json + index/embeddings.npz
License: CC-BY-NC-SA-4.0 (NCERT).
"""
import json, re, unicodedata
from pathlib import Path
import fitz

WS = Path(__file__).resolve().parent
PDF_DIR = WS / "pdfs"
SRC = WS / "pack-src"

BOOKS = {
    "iemh1": dict(isbn="9788119465392", book="Ganita Ver 1.0", title="Ganita Ver 1.0 Part I",
                  grade=9, subject="mathematics", prefix="c9-mat",
                  url="https://ncert.nic.in/textbook/pdf/iemh101.pdf"),
    "iesc1": dict(isbn="iesc1", book="Science Exploration", title="Exploration (Grade 9 Science)",
                  grade=9, subject="science", prefix="c9-sci",
                  url="https://ncert.nic.in/textbook/pdf/iesc101.pdf"),
    "jemh1": dict(isbn="jemh1", book="Mathematics Class X", title="Mathematics (Class 10)",
                  grade=10, subject="mathematics", prefix="c10-mat",
                  url="https://ncert.nic.in/textbook/pdf/jemh101.pdf"),
    "jesc1": dict(isbn="jesc1", book="Science Class X", title="Science (Class 10)",
                  grade=10, subject="science", prefix="c10-sci",
                  url="https://ncert.nic.in/textbook/pdf/jesc101.pdf"),
}

TARGET_CHARS = 1400
MIN_CHARS = 120


def clean(t: str) -> str:
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def chapter_title(first_page: str) -> str:
    for line in first_page.splitlines():
        line = line.strip()
        if 8 <= len(line) <= 90 and not line.isdigit() and not line.lower().startswith("chapter"):
            # skip TOC / page headers
            if "©" in line or "NCERT" in line:
                continue
            return line
    return "Untitled"


def build():
    (SRC / "content").mkdir(parents=True, exist_ok=True)
    for f in (SRC / "content").glob("*.json"):
        f.unlink()
    index_meta = []
    chapters = []  # (book, chno, cid_prefix, first_chunk_text) for question gen
    for code, meta in BOOKS.items():
        pdfs = sorted(PDF_DIR.glob(f"{code}*.pdf"))
        for pdf in pdfs:
            chno = pdf.stem[len(code):]  # e.g. "01"
            doc = fitz.open(pdf)
            pages = [clean(p.get_text()) for p in doc]
            if not doc.metadata.get("title"):
                pass
            title = chapter_title(pages[0] if pages[0] else "Untitled")
            cid = f"{meta['prefix']}/ch{int(chno)}"
            page_chunks = []
            buf = ""
            pi = 0
            for text in pages:
                if len(buf) + len(text) > TARGET_CHARS and buf:
                    page_chunks.append(buf)
                    buf = text
                else:
                    buf = (buf + "\n" + text).strip()
                pi += 1
            if buf.strip():
                page_chunks.append(buf.strip())
            n = 0
            for chunk in page_chunks:
                chunk = chunk.strip()
                if len(chunk) < MIN_CHARS:
                    continue
                n += 1
                cid_chunk = f"{cid}/t{n:03d}"
                (SRC / "content" / f"{cid_chunk.replace('/', '__')}.json").write_text(
                    json.dumps({"id": cid_chunk, "kind": "text",
                                "chapter": f"{meta['title']} Ch.{int(chno)} {title}",
                                "text": chunk}, ensure_ascii=False))
                index_meta.append({"id": cid_chunk, "chars": len(chunk)})
            chapters.append((meta, int(chno), title, cid, max(n, 1)))
            doc.close()
        print(code, "done", flush=True)
    # deterministic questions: 3 per chapter (Remember MCQ / Understand SA / Apply LA)
    titles_by_book = {}
    for meta, chno, title, cid, nchunks in chapters:
        titles_by_book.setdefault(meta["prefix"], []).append(title)
    nq = 0
    for meta, chno, title, cid, nchunks in chapters:
        others = [t for t in titles_by_book[meta["prefix"]] if t != title]
        while len(others) < 3:
            others.append("None of these")
        first_cid = f"{cid}/t001"
        ch_label = f"{meta['title']} Ch.{chno} {title}"
        q1 = {"id": f"{cid}/q1", "kind": "qa", "chapter": ch_label,
              "text": json.dumps({"question_id": f"{cid}_q1", "type": "MCQ",
                                  "difficulty": "easy", "bloom_level": "Remember",
                                  "question": f"What is the main topic of '{title}' in {meta['book']}?",
                                  "options": [title, others[0], others[1], others[2]],
                                  "correct_answer": 0,
                                  "explanation": f"Chapter {chno} of {meta['book']} covers: {title}",
                                  "source_chunk": first_cid}, ensure_ascii=False)}
        q2 = {"id": f"{cid}/q2", "kind": "qa", "chapter": ch_label,
              "text": json.dumps({"question_id": f"{cid}_q2", "type": "SA",
                                  "difficulty": "medium", "bloom_level": "Understand",
                                  "question": f"Explain one key concept from '{title}' in your own words.",
                                  "sample_answer": f"Key concept from {title} (see {first_cid}).",
                                  "rubric": ["Mentions key term", "Explains in own words", "Provides example"],
                                  "source_chunk": first_cid}, ensure_ascii=False)}
        q3 = {"id": f"{cid}/q3", "kind": "qa", "chapter": ch_label,
              "text": json.dumps({"question_id": f"{cid}_q3", "type": "LA",
                                  "difficulty": "medium", "bloom_level": "Apply",
                                  "question": f"Give a real-life example where the concepts of '{title}' are used.",
                                  "sample_answer": f"Application of {title} to a real-life situation.",
                                  "rubric": ["Correct concept", "Coherent argument", "Real-life connection"],
                                  "source_chunk": first_cid}, ensure_ascii=False)}
        for q in (q1, q2, q3):
            (SRC / "content" / f"{q['id'].replace('/', '__')}.json").write_text(
                json.dumps(q, ensure_ascii=False))
            index_meta.append({"id": q["id"], "chars": len(q["text"])})
            nq += 1
    manifest = {
        "schema_version": "0",
        "pack_id": "cbse-class9-10-math-science",
        "version": "1.0.0",
        "title": "CBSE Class 9-10 Mathematics & Science — NCERT content pack v1",
        "created_at": "2026-10-09T00:00:00+00:00",
        "locale": "en-IN",
        "source": {
            "name": "NCERT",
            "grade": None,
            "subject": "Mathematics, Science",
            "license": "CC-BY-NC-SA-4.0",
            "upstream_url": "https://ncert.nic.in/textbook.php",
        },
        "index": [],
        "encryption": {"payload": "aes-256-gcm", "kdf": "hkdf-sha256",
                       "key_ref": "fleet-dev",
                       "note": "AES-256-GCM payload; HKDF-SHA256(master, salt=pack_id). Dev key 0*64 unless MS_MASTER_KEY set."},
        "delta": {"delta_from": None, "changed_chunks": [], "removed_chunks": []},
        "stats": {"chunks": 0},
    }
    (SRC / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (SRC / "chunk_meta.json").write_text(json.dumps(
        {"n_text": len(index_meta) - nq, "n_qa": nq}, indent=2))
    print("chunks:", len(index_meta), "questions:", nq)
    # stash ids for embedding step
    (SRC / "_ids.json").write_text(json.dumps([m["id"] for m in
        sorted(index_meta, key=lambda x: x["id"])]))


if __name__ == "__main__":
    build()
