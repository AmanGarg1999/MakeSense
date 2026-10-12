"""LL-09d: dependency-free PDF renderer for the transcript document.

Hand-rolls a minimal PDF 1.4 (Helvetica, multi-page) so transcript export
needs no reportlab/fpdf wheel — the server image stays slim. Input is the
canonical document from ll09d.transcript.build_transcript_document, so PDF
and JSON exports can never disagree on numbers.

Layout: A4 portrait; one record row per line with page breaks when the
cursor reaches the bottom margin.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

PAGE_W, PAGE_H = 595, 842          # A4 @ 72dpi
MARGIN = 48
LEADING = 14                       # row pitch
BOTTOM = MARGIN + LEADING * 2

# column x-offsets for the records table
_COLS = "Content Pack|Seq|Req|Credits|Completed|Mastery|Grade|Credential"
_COL_X = [0, 250, 285, 320, 375, 450, 505, 540]


def _esc(s: str) -> str:
    """Escape a python str into PDF literal string content (WinAnsi-safe)."""
    out: List[str] = []
    for ch in s:
        o = ord(ch)
        if ch in "\\()":
            out.append("\\" + ch)
        elif 32 <= o <= 126:
            out.append(ch)
        else:
            repl = {"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
                    "\u2013": "-", "\u2014": "-", "\u2026": "..."}.get(ch)
            if repl:
                out.append(repl)
            elif 160 <= o <= 255:
                out.append(chr(o))
            else:
                out.append("?")
    return "".join(out)


def _text(x: float, y: float, size: int, s: str, bold: bool = False) -> str:
    font = "F2" if bold else "F1"
    return (f"BT /{font} {size} Tf 1 0 0 1 {x:.1f} {y:.1f} Tm "
            f"({_esc(s).encode('latin-1', 'replace').decode('latin-1')}) Tj ET\n")


def _fmt(v: Any) -> str:
    return "-" if v is None or v == "" else str(v)


class _PageBuilder:
    """Collects positioned text runs for the current page, flushing at breaks."""

    def __init__(self) -> None:
        self.pages: List[str] = []
        self.items: List[Tuple[float, float, int, str, bool]] = []
        self.y = float(PAGE_H - MARGIN)

    # -- cursor ops -------------------------------------------------------
    def title(self, s: str) -> None:
        self._place(20, s, True); self.y -= 26

    def sub(self, s: str) -> None:
        self._place(10, s, False); self.y -= LEADING

    def heading(self, s: str) -> None:
        self.y -= 8
        self._place(13, s, True); self.y -= 18

    def kv(self, s: str) -> None:
        self._place(9, s, False); self.y -= LEADING

    def gap(self) -> None:
        self.y -= 8

    def columns(self) -> None:
        for cx, col in zip(_COL_X, _COLS.split("|")):
            self.items.append((MARGIN + cx, self.y, 9, col, True))
        self.y -= LEADING + 4

    def row(self, cells: List[str]) -> None:
        for cx, cell in zip(_COL_X, cells):
            self.items.append((MARGIN + cx, self.y, 9, cell, False))
        self.y -= LEADING

    def _place(self, size: int, s: str, bold: bool) -> None:
        self.items.append((float(MARGIN), self.y, size, s, bold))

    # -- pagination -------------------------------------------------------
    def need(self, extra: int = 0) -> None:
        """Break the page when fewer than `extra` rows of room remain."""
        if self.y - extra * LEADING < BOTTOM:
            self.break_page()

    def break_page(self) -> None:
        self.pages.append("".join(
            _text(x, y, size, t, b) for x, y, size, t, b in self.items))
        self.items, self.y = [], float(PAGE_H - MARGIN)

    def finish(self) -> List[str]:
        if self.items or not self.pages:
            self.break_page()
        return self.pages


def render_transcript_pdf(doc: Dict[str, Any]) -> bytes:
    """Canonical transcript document -> PDF bytes (A4, one or more pages)."""
    pathway = doc.get("pathway", {}) or {}
    summary = doc.get("summary", {}) or {}
    records = doc.get("records", []) or []
    program = doc.get("program") or {}

    pb = _PageBuilder()
    pb.title("MakeSense Learning Transcript")
    pb.sub(f"{_fmt(pathway.get('level'))} pathway: {_fmt(pathway.get('title'))}")
    pb.sub(f"Pathway ID {_fmt(pathway.get('id'))}   User {_fmt(pathway.get('user_id'))}   "
           f"Status {_fmt(pathway.get('status'))}")
    pb.sub(f"Started {_fmt(pathway.get('started_at'))}   Target {_fmt(pathway.get('target_completion'))}   "
           f"Generated {_fmt(doc.get('generated_at'))}")
    pb.gap()
    pb.heading("Program Summary")
    pb.need(2)
    pb.kv(f"Completion         {_fmt(summary.get('completion_pct'))}%    "
          f"Records completed  {_fmt(summary.get('completed'))} / {_fmt(summary.get('total_records'))}")
    pb.kv(f"Credits earned     {_fmt(summary.get('credits_earned'))} / {_fmt(summary.get('credits_required'))}    "
          f"GPA (4.0 scale)    {_fmt(summary.get('gpa'))}")
    if program:
        pb.kv(f"Credit system      {_fmt(program.get('credit_system'))}    "
              f"Assessment        {_fmt(program.get('assessment_type'))}")
        pb.kv(f"Mentor model       {_fmt(program.get('mentor_model'))}    "
              f"Typical duration  {_fmt(program.get('typical_duration_weeks'))} weeks")
    creds = summary.get("credentials") or []
    pb.kv(f"Credentials issued {len(creds)}"
          + ("" if not creds else "    " + ", ".join(str(c.get("credential_type")) for c in creds[:4])))
    pb.gap()

    pb.heading("Records")
    pb.columns()
    for r in records:
        pb.need()
        if pb.y == PAGE_H - MARGIN:  # page just broke -> repeat table head
            pb.heading("Records (continued)")
            pb.columns()
        done = bool(r.get("completed"))
        pb.row([
            _fmt(r.get("content_pack_id"))[:34],
            _fmt(r.get("sequence")),
            "Yes" if r.get("required") else "No",
            _fmt(r.get("credits")),
            "Yes" if done else "No",
            _fmt(r.get("mastery_score")),
            _fmt(r.get("grade_letter")),
            _fmt(r.get("credential_type")) if r.get("credential_issued") else "-",
        ])

    extras = doc.get("extra_entries") or []
    if extras:
        pb.gap()
        pb.heading("Extra entries (not in curriculum)")
        for e in extras:
            pb.need()
            pb.kv(f"{_fmt(e.get('content_pack_id'))}  completed={e.get('completed')}  "
                   f"mastery={_fmt(e.get('mastery_score'))}  credential={_fmt(e.get('credential_type'))}")

    return _assemble(pb.finish())


def _assemble(page_streams: List[str]) -> bytes:
    """Wrap content streams into a minimal valid PDF 1.4 file."""
    n = len(page_streams)
    # id layout: 1 catalog, 2 pages tree, 3..n+2 page objects,
    # n+3/n+4 fonts, n+5..2n+4 content streams — consecutive, for any n >= 1
    page_ids = [3 + i for i in range(n)]
    font1, font2 = 3 + n, 4 + n
    cont_ids = [n + 5 + i for i in range(n)]

    objs: Dict[int, bytes] = {}
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[2] = f"<< /Type /Pages /Count {n} /Kids [{kids}] >>".encode()
    for i, pid in enumerate(page_ids):
        objs[pid] = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                     f"/Resources << /Font << /F1 {font1} 0 R /F2 {font2} 0 R >> >> "
                     f"/Contents {cont_ids[i]} 0 R >>").encode()
    objs[font1] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    objs[font2] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"
    for i, stream in enumerate(page_streams):
        data = stream.encode("latin-1", "replace")
        objs[cont_ids[i]] = (b"<< /Length " + str(len(data)).encode()
                             + b" >>\nstream\n" + data + b"\nendstream")

    max_id = max(objs)
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: Dict[int, int] = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref_at = len(out)
    out += f"0 {max_id + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for oid in range(1, max_id + 1):
        out += f"{offsets.get(oid, 0):010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_at}\n%%EOF\n").encode()
    return bytes(out)
