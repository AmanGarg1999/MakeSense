"""LL-05 ACCEPTANCE: run the rubric scorer live against a real artifact.

Usage: python3 scripts/assess_sample_run.py <rubric.json> <submission.json> <evidence_text_file>
Prints the scoring_result JSON. Endpoint via ASSESS_LLM_BASE_URL (default DGX 18300).
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from packages.assessment.evidence import validate_submission
from packages.assessment.llm_client import OpenAICompatClient
from packages.assessment.rubric import score_submission

rubric = json.loads(Path(sys.argv[1]).read_text())
sub_payload = json.loads(Path(sys.argv[2]).read_text())
evidence_text = Path(sys.argv[3]).read_text()

# ensure sha256s on artifacts match the actual evidence file
for a in sub_payload["evidence"].get("artifacts", []):
    a["sha256"] = hashlib.sha256(evidence_text.encode()).hexdigest()

sub = validate_submission(sub_payload)
model = OpenAICompatClient()
verdict = score_submission(rubric, sub, model, evidence_text)
print(json.dumps(verdict.result, indent=2))
print(f"--- passed={verdict.passed} human_escalation={verdict.human_escalation}", file=sys.stderr)
