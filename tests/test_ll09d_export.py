"""LL-09d acceptance: transcript export (Python builder + PDF + API).

Core (no DB): the shared cross-language fixture must produce IDENTICAL
numbers through ll09d.transcript.build_transcript_document as it does
through the frontend builder in test_ll09d_transcript_export.mjs; the stdlib
PDF renderer must emit a structurally valid multi-object PDF.

Integration (needs DATABASE_URL, same convention as LL-09a/09b tests):
GET /api/export/transcript/{id}.json and .pdf end-to-end on a real pathway
built through the LL-09a API.

  DATABASE_URL=postgresql://makesense:***@localhost:55452/makesense
"""

import asyncio
import json
import os
import time
from pathlib import Path

import pytest

from ll09d.transcript import TRANSCRIPT_SCHEMA, build_transcript_document, letter_grade
from ll09d.pdf import render_transcript_pdf
from server.pathway_service import PATHWAY_LEVELS

FIXTURE = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "ll09d_transcript_fixture.json")
    .read_text()
)

PID = os.getpid()
USER_D = 950_000 + (PID % 50_000)


def hdr(user_id: int):
    return {"X-User-ID": str(user_id)}


# ---------------------------------------------------------------------------
# 1. Cross-language fixture contract
# ---------------------------------------------------------------------------

def test_python_builder_matches_shared_fixture():
    doc = build_transcript_document(
        FIXTURE["pathway"],
        transcript=FIXTURE["transcript"],
        level_row=FIXTURE["level_row"],
    )
    exp = FIXTURE["expected"]
    assert doc["schema"] == exp["schema"] == TRANSCRIPT_SCHEMA
    s = doc["summary"]
    assert s["total_records"] == exp["total_records"]
    assert s["completed"] == exp["completed"]
    assert s["completion_pct"] == exp["completion_pct"]
    assert s["credits_required"] == pytest.approx(exp["credits_required"])
    assert s["credits_earned"] == pytest.approx(exp["credits_earned"])
    assert s["gpa"] == exp["gpa"], "GPA must match the JS builder on the same input"
    assert len(s["credentials"]) == exp["credential_count"]
    assert len(doc["extra_entries"]) == exp["extra_count"]
    for pack, letter in exp["grade_letters"].items():
        rec = next(r for r in doc["records"] if r["content_pack_id"] == pack)
        assert rec["grade_letter"] == letter


def test_document_is_json_serialisable_without_datetimes():
    """asyncpg rows carry datetime/date; the doc must normalise them to str."""
    from datetime import datetime, timezone, date
    pathway = dict(FIXTURE["pathway"])
    pathway["started_at"] = datetime(2025, 8, 1, tzinfo=timezone.utc)
    pathway["target_completion"] = date(2029, 5, 1)
    doc = build_transcript_document(pathway, transcript=FIXTURE["transcript"])
    text = json.dumps(doc)          # raises if any non-serialisable leaked
    assert json.loads(text)["pathway"]["target_completion"] == "2029-05-01"
    assert doc["pathway"]["started_at"] == "2025-08-01T00:00:00Z"


def test_records_missing_curriculum_and_anti_join():
    doc = build_transcript_document(FIXTURE["pathway"], transcript=FIXTURE["transcript"])
    packs = [r["content_pack_id"] for r in doc["records"]]
    assert packs == ["cs101", "cs102", "math201", "ethics100", "capstone401"]
    pending = next(r for r in doc["records"] if r["content_pack_id"] == "capstone401")
    assert pending["completed"] is False and pending["grade_letter"] is None
    assert doc["extra_entries"][0]["flag"] == "not_in_curriculum"


def test_unknown_level_pathway_refuses_export():
    bad = dict(FIXTURE["pathway"], level=None)
    with pytest.raises(TypeError):
        build_transcript_document(bad)


def test_letter_grade_ladder_matches_js_mirror():
    cases = [(1, "A"), (0.93, "A"), (0.92, "A-"), (0.87, "A-"), (0.86, "B+"),
             (0.8, "B+"), (0.79, "B"), (0.73, "B"), (0.72, "B-"), (0.67, "B-"),
             (0.66, "C+"), (0.6, "C+"), (0.59, "C"), (0.53, "C"), (0.52, "D"),
             (0.4, "D"), (0.39, "F"), (0, "F")]
    for m, letter in cases:
        assert letter_grade(m) == letter, m


def test_zero_credit_gpa_is_none_not_crash():
    pathway = {"id": "x", "level": "micro",
               "curriculum": [{"content_pack_id": "a", "credits": 0}]}
    transcript = [{"content_pack_id": "a", "mastery_score": 0.9,
                   "completed_at": "2026-01-01T00:00:00Z",
                   "credential_issued": False, "credential_type": None}]
    doc = build_transcript_document(pathway, transcript=transcript)
    assert doc["summary"]["gpa"] is None


# ---------------------------------------------------------------------------
# 2. PDF renderer (stdlib, no external deps)
# ---------------------------------------------------------------------------

def test_pdf_renders_valid_single_page():
    doc = build_transcript_document(FIXTURE["pathway"], transcript=FIXTURE["transcript"],
                                    level_row=FIXTURE["level_row"])
    data = render_transcript_pdf(doc)
    assert data.startswith(b"%PDF-1.4")
    assert b"%%EOF" in data[-32:]
    assert data.count(b"/Type /Page ") >= 1
    # xref declared objects must all exist
    assert b"/Type /Catalog /Pages 2 0 R" in data
    assert b"Helvetica-Bold" in data
    # transcript content present
    assert b"B.Sc. Test Program" in data
    assert b"cs101" in data


def test_pdf_paginates_long_transcripts():
    curriculum = [
        {"content_pack_id": f"pack{i:03d}", "sequence": i, "required": True, "credits": 3}
        for i in range(120)
    ]
    transcript = [
        {"content_pack_id": f"pack{i:03d}", "mastery_score": 0.8,
         "completed_at": "2026-05-01T00:00:00Z", "credential_issued": False,
         "credential_type": None}
        for i in range(120)
    ]
    doc = build_transcript_document(
        {"id": "big", "level": "undergrad", "title": "Long degree", "curriculum": curriculum},
        transcript=transcript)
    data = render_transcript_pdf(doc)
    assert data.count(b"/Type /Page ") >= 3, "120 records must spill across pages"
    # Parens are PDF-escaped in string literals (_esc), so match the encoded form.
    assert data.count(b"Records \\(continued\\)") >= 2


def test_pdf_survives_unicode_and_parens():
    doc = build_transcript_document({
        "id": "u", "level": "certificate", "title": "Amalienbad (Wien) — 'Quoted' \\x",
        "curriculum": [{"content_pack_id": "dés:ünïcode", "sequence": 0, "credits": 1}],
    })
    data = render_transcript_pdf(doc)
    assert data.startswith(b"%PDF-1.4") and b"%%EOF" in data[-32:]


# ---------------------------------------------------------------------------
# 3. API integration (needs DATABASE_URL)
# ---------------------------------------------------------------------------

HAS_DB = bool(os.environ.get("DATABASE_URL"))


def _dsn():
    return os.environ["DATABASE_URL"]


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from server.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def pathway_with_transcript(client):
    """Create an undergrad pathway + transcript rows via the LL-09a API."""
    import asyncpg

    async def _up():
        conn = await asyncpg.connect(_dsn())
        try:
            await conn.execute(
                "INSERT INTO users (id, email) VALUES ($1, $2) ON CONFLICT (id) DO NOTHING",
                USER_D, f"ll09d-{time.time_ns()}@test.local")
        finally:
            await conn.close()

    asyncio.run(_up())

    body = {
        "level": "undergrad",
        "title": "LL-09d export pathway",
        "curriculum": [
            {"content_pack_id": "x:cs101", "sequence": 0, "credits": 4},
            {"content_pack_id": "x:cs102", "sequence": 1, "credits": 4},
            {"content_pack_id": "x:cap", "sequence": 2, "credits": 6},
        ],
    }
    res = client.post("/api/pathways", json=body, headers=hdr(USER_D))
    assert res.status_code == 200, res.text
    pid = res.json()["id"]
    for pack, mastery, cred in [("x:cs101", 0.91, False), ("x:cs102", 0.78, True)]:
        r = client.post(f"/api/pathways/{pid}/transcript", json={
            "content_pack_id": pack, "mastery_score": mastery,
            "credential_issued": cred, "credential_type": "mod" if cred else None,
        }, headers=hdr(USER_D))
        assert r.status_code == 200, r.text
    yield pid

    async def _clean():
        conn = await asyncpg.connect(_dsn())
        try:
            await conn.execute("DELETE FROM users WHERE id = $1", USER_D)  # cascades
        finally:
            await conn.close()

    asyncio.run(_clean())


@pytest.mark.skipif(not HAS_DB, reason="DATABASE_URL not set")
def test_export_json_api_matches_builder(client, pathway_with_transcript):
    pid = pathway_with_transcript
    res = client.get(f"/api/export/transcript/{pid}.json", headers=hdr(USER_D))
    assert res.status_code == 200, res.text
    doc = res.json()
    assert doc["schema"] == TRANSCRIPT_SCHEMA
    assert doc["pathway"]["level"] == "undergrad"
    assert doc["summary"]["completed"] == 2
    assert doc["summary"]["credits_earned"] == pytest.approx(8)
    # GPA = (0.91*4 + 0.78*4)/8*4 = 3.38
    assert doc["summary"]["gpa"] == pytest.approx(3.38, abs=0.01)
    assert doc["summary"]["credentials"][0]["credential_type"] == "mod"


@pytest.mark.skipif(not HAS_DB, reason="DATABASE_URL not set")
def test_export_pdf_api_streams_pdf(client, pathway_with_transcript):
    pid = pathway_with_transcript
    res = client.get(f"/api/export/transcript/{pid}.pdf", headers=hdr(USER_D))
    assert res.status_code == 200, res.text
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment" in res.headers.get("content-disposition", "")
    assert res.content.startswith(b"%PDF-1.4")
    assert b"LL-09d export pathway" in res.content


@pytest.mark.skipif(not HAS_DB, reason="DATABASE_URL not set")
def test_export_rejects_other_users_and_bad_ids(client, pathway_with_transcript):
    pid = pathway_with_transcript
    res = client.get(f"/api/export/transcript/{pid}.json", headers=hdr(USER_D + 777))
    assert res.status_code == 404
    res = client.get("/api/export/transcript/not-a-uuid.json", headers=hdr(USER_D))
    assert res.status_code == 422


@pytest.mark.skipif(not HAS_DB, reason="DATABASE_URL not set")
def test_export_active_route(client, pathway_with_transcript):
    res = client.get("/api/export/transcript/active.json", headers=hdr(USER_D))
    assert res.status_code == 200, res.text
    assert res.json()["pathway"]["id"] == pathway_with_transcript
