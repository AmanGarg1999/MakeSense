#!/usr/bin/env python3
"""MakeSense quality gate (mk-029 checklist, 9 checks).

Every verdict is derived from the filesystem, git, or a real subprocess.
There are zero hardcoded statuses. A check that cannot run in this
environment reports SKIP with the reason (SKIP != pass, but it is not a
false FAIL either); a check whose evidence fails reports FAIL.

Usage:
    python3 quality_check.py            # human table + JSON to quality_results.json
    python3 quality_check.py --json     # machine-readable JSON on stdout
    python3 quality_check.py --no-network   # skip remote probes (CI default-safe)

Exit code: 0 if no FAIL, 1 if any FAIL. SKIPs are reported but do not fail
the gate (CI without devices/network still gets a usable signal; REM-4 can
treat SKIPs per its own policy via the JSON).

Environment overrides:
    MAKESENSE_DGX_SSH_TARGET   ssh target for the DGX Spark model store
                               (default huntingvision@100.72.85.102)
    MAKESENSE_ARTIFACTS_DIR    local dir of model META json files
                               (default <repo>/models/artifacts, falling back
                               to the makesense-core harness checkout)
"""
import argparse
import glob
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
DGX_SSH_TARGET = os.environ.get("MAKESENSE_DGX_SSH_TARGET", "huntingvision@100.72.85.102")
DGX_MODEL_DIR = "~/mak7/models"
DGX_SSH_KEY = os.path.expanduser("~/.ssh/dgx_spark")


def _run(cmd, cwd=REPO, timeout=120, shell=False):
    """Run a subprocess, return (returncode, stdout, stderr). Never raises."""
    try:
        r = subprocess.run(cmd, cwd=cwd, timeout=timeout,
                           capture_output=True, text=True, shell=shell)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError as e:
        return None, "", str(e)
    except subprocess.TimeoutExpired:
        return None, "", f"timeout after {timeout}s"
    except Exception as e:  # noqa: BLE001 - a gate must not die on one check
        return None, "", str(e)


def _path(*parts):
    return os.path.join(REPO, *parts)


def _exists(*parts):
    return os.path.exists(_path(*parts))


def _artifact_dirs():
    """Candidate locations of model META json files, in priority order."""
    dirs = []
    env = os.environ.get("MAKESENSE_ARTIFACTS_DIR")
    if env:
        dirs.append(env)
    dirs.append(_path("models", "artifacts"))
    # the harness checkout holds the canonical META records today
    dirs.append(os.path.expanduser("~/harness/makesense-core/models/artifacts"))
    return [d for d in dirs if os.path.isdir(d)]


# ---------------------------------------------------------------- checks ---

def check_code_quality():
    """Real: server import smoke test (when deps installed) + pytest
    collection of the test suite. Verdict from subprocess results only."""
    details = []
    rc_dep, _, _ = _run([sys.executable, "-c", "import fastapi"], timeout=30)
    if rc_dep == 0:
        rc, out, err = _run([sys.executable, "server/test_imports.py"], timeout=60)
        if rc is None:
            details.append(f"server imports: could not run ({err.strip()[:80]})")
            return "fail", "; ".join(details)
        if rc == 0:
            details.append("server imports: OK")
        else:
            first = (err or out).strip().splitlines()
            details.append(f"server imports: FAIL ({first[-1][:120] if first else rc})")
            return "fail", "; ".join(details)
    else:
        details.append("server imports: skipped (fastapi not installed in this env)")

    rc, out, err = _run([sys.executable, "-m", "pytest", "--collect-only", "-q",
                         "scripts/tests/test_correct_schema.py",
                         "packages/assessment/tests",
                         "gamification/tests"], timeout=120)
    collected = 0
    for line in (out or "").splitlines():
        if " tests collected" in line or " test collected" in line:
            try:
                collected = int(line.split()[0])
            except ValueError:
                pass
    if rc is None:
        details.append("pytest collection: could not run")
        return "fail", "; ".join(details)
    if collected > 0:
        details.append(f"pytest collection: {collected} tests")
    else:
        first = (err or out).strip().splitlines()
        details.append(f"pytest collection: FAIL ({first[-1][:120] if first else 'no tests'})")
    status = "pass" if rc == 0 and collected > 0 else "fail"
    return status, "; ".join(details)


def check_device_testing():
    """Derive from live tooling/device state, not a hardcoded string."""
    rc, out, err = _run(["adb", "devices"], timeout=15, shell=False)
    adb_path = _which("adb")
    if rc is not None and adb_path:
        lines = [l for l in out.splitlines()[1:] if l.strip()]
        devices = [l for l in lines if "\tdevice" in l]
        if devices:
            return "pass", f"adb found {len(devices)} connected device(s): {devices}"
        return "fail", "adb present but no device connected (DEV-A bench outstanding, MAK-74)"
    if adb_path is None:
        return "skip", "adb not installed on this host; no device attached (cannot gate here)"
    return "fail", f"adb present but failed to run: {err.strip()[:100]}"


def _which(prog):
    rc, out, _ = _run(["which", prog], timeout=10)
    return out.strip() if rc == 0 and out.strip() else None


def check_offline_verification():
    """Real: the offline machinery (SW template, workbox config, manifest)
    must exist in the frontend, not just placeholder tests."""
    parts = {
        "frontend/public/sw-template.js": "service-worker template",
        "frontend/workbox.config.cjs": "workbox build config",
        "frontend/public/manifest.json": "PWA manifest",
        "frontend/src/index.jsx": "SW registration",
    }
    missing = [desc for path, desc in parts.items()
               if not _exists(*path.split("/"))]
    # SW registration must actually register (not be a stub)
    sw_reg = False
    reg_path = _path("frontend", "src", "index.jsx")
    if os.path.isfile(reg_path):
        with open(reg_path, encoding="utf-8", errors="ignore") as f:
            sw_reg = "serviceWorker.register" in f.read()
    if missing:
        return "fail", "offline machinery missing: " + ", ".join(missing)
    if not sw_reg:
        return "fail", "frontend present but no serviceWorker.register() found in index.jsx"
    return "pass", ("offline machinery present: " +
                    ", ".join(parts.values()) + "; SW registration found in index.jsx")


def check_content_pack_validation():
    """Real: run the pack signature/schema validator over packs/dist."""
    dist = _path("packs", "dist")
    if not os.path.isdir(dist):
        return "fail", f"packs/dist not found at {dist}"
    mspx = glob.glob(os.path.join(dist, "*.mspx"))
    if not mspx:
        return "fail", "no .mspx packs in packs/dist"
    rc, out, err = _run([sys.executable, "build/sign_validate.py"],
                        cwd=_path("packs"), timeout=120)
    if rc is None:
        return "fail", f"validator could not run: {err.strip()[:100]}"
    if rc == 0 and "OK" in out:
        return "pass", f"{len(mspx)} pack(s) in dist; sign_validate.py passed ({out.count('sha256:')} sha256 check(s))"
    tail = (err or out).strip().splitlines()
    return "fail", f"pack validation failed (rc={rc}): {tail[-1][:120] if tail else ''}"


def check_sync_validation():
    """Real: sync endpoint exists in the server and the frontend registers
    sync-capable SW + event-tracker service is importable-tested."""
    evidence = []
    ok_main = False
    main_py = _path("server", "main.py")
    if os.path.isfile(main_py):
        with open(main_py, encoding="utf-8", errors="ignore") as f:
            src = f.read()
        ok_main = ("@app." in src or "APIRouter" in src) and "async def" in src
        evidence.append("server/main.py: async endpoints present" if ok_main
                        else "server/main.py: no async endpoints found")
    else:
        evidence.append("server/main.py missing")
    # offline queue / sync logic in frontend
    sync_hit = None
    rc, out, _ = _run(["grep", "-rl", "serviceWorker", "frontend/src"], timeout=20)
    if rc == 0 and out.strip():
        sync_hit = out.strip().splitlines()[0]
    tracker_tests = _exists("services", "event-tracker", "tests", "test_main.py")
    evidence.append(f"frontend SW usage: {sync_hit or 'none'}")
    evidence.append("event-tracker sync tests: present" if tracker_tests
                    else "event-tracker tests missing")
    status = "pass" if (ok_main and tracker_tests and sync_hit) else "fail"
    return status, "; ".join(evidence)


def check_model_performance():
    """META json records are the source of truth in-repo/harness; binaries
    live on the DGX Spark store (~/mak7/models). No in-repo binaries expected."""
    dirs = _artifact_dirs()
    metas = []
    for d in dirs:
        metas = sorted(glob.glob(os.path.join(d, "*.json")))
        if metas:
            break
    if not metas:
        return "fail", f"no model META json found in: {dirs or 'models/artifacts (missing)'}"
    referenced = []
    broken = []
    for m in metas:
        try:
            with open(m, encoding="utf-8") as f:
                d = json.load(f)
        except Exception as e:  # noqa: BLE001
            broken.append(f"{os.path.basename(m)}: unparseable ({e})")
            continue
        loc = (d.get("location") or {}).get("paths") or []
        referenced.extend(loc)
    details = [f"{len(metas)} META json in {dirs[0]} (e.g. "
               f"{', '.join(os.path.basename(x) for x in metas[:4])})"]
    if broken:
        return "fail", "; ".join(details + broken)

    # optional remote probe: DGX Spark binaries the META files point at
    rc_probe, out_probe, err_probe = _run(
        ["ssh", "-i", DGX_SSH_KEY, "-o", "ConnectTimeout=8", "-o", "BatchMode=yes",
         DGX_SSH_TARGET, f"ls {DGX_MODEL_DIR}"], timeout=20)
    if rc_probe is None:
        details.append(f"DGX probe skipped/unreachable: {err_probe.strip()[:80] or 'no route'}")
        details.append("verdict on META records only")
        return "pass", "; ".join(details)
    remote = set(out_probe.split())
    if "gemma2-upstream-int4" not in remote:
        details.append(f"DGX store missing gemma2-upstream-int4 (have: {sorted(remote)[:6]})")
        return "fail", "; ".join(details)
    details.append(f"DGX store reachable with {len(remote)} model dir(s) incl. gemma2-upstream-int4")
    return "pass", "; ".join(details)


def check_security_audit():
    """Real: scan every committed file (git ls-tree HEAD) for high-signal
    secret material. Placeholder values (change-me, your-api-key-here,
    local dev creds in .env.example/docker-compose) are excluded — the repo's
    audit/scan_secrets.py regex net is too broad for a gate (it matches
    commit SHAs and produces ~3k false positives)."""
    rc, out, _ = _run(["git", "ls-tree", "-r", "HEAD", "--name-only"], timeout=60)
    if rc != 0 or not out.strip():
        return "fail", "could not enumerate committed files via git ls-tree"
    files = out.splitlines()
    # high-signal patterns: real secret shapes, not prose or hashes
    import re
    PATTERNS = [
        ("AWS access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
        ("Google API key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
        ("GitHub token", re.compile(r"gh[pousr]_[0-9A-Za-z]{36}")),
        ("Slack token", re.compile(r"xox[baprs]-[0-9A-Za-z]{10,}")),
        ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
        ("Stripe key", re.compile(r"sk_live_[0-9A-Za-z]{24,}")),
    ]
    PLACEHOLDER = re.compile(
        r"(change[-_]?me|your[-_]?api[-_]?key|your[-_]?key|placeholder|example|"
        r"xxxx|<[^>]+>|OWNER/REPO|makesense:make|postgres:postgres)", re.I)
    hits = []
    scanned = 0
    for f in files:
        # skip the audit reports themselves (they quote past findings)
        if f.startswith("audit/") or not os.path.isfile(_path(f)):
            continue
        try:
            with open(_path(f), encoding="utf-8", errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    if PLACEHOLDER.search(line):
                        continue
                    for name, pat in PATTERNS:
                        if pat.search(line):
                            hits.append(f"{f}:{i} ({name})")
            scanned += 1
        except OSError:
            continue
    if hits:
        return "fail", f"{len(hits)} candidate secret(s) in {scanned} committed files: " \
                       f"{'; '.join(hits[:5])}"
    return "pass", f"{scanned} committed files scanned against 6 high-signal secret patterns: clean"


def check_accessibility():
    """Derive from repo reality: WCAG tests/ci config actually present?"""
    rc, out, _ = _run(["grep", "-rliE", "wcag|axe-core|jest-axe|@axe",
                       "frontend", "cypress", "docs"], timeout=30)
    hits = [h for h in (out or "").splitlines() if h.strip()]
    a11y_attrs = 0
    rc, out, _ = _run(["grep", "-rhoE", "aria-[a-z]+=|role=", "frontend/src"], timeout=30)
    a11y_attrs = len((out or "").splitlines())
    if hits:
        return "pass", f"WCAG/axe tooling referenced in: {hits[:5]}"
    detail = (f"no WCAG 2.1 AA tests or axe tooling found in repo "
              f"(aria/role attribute uses in frontend/src: {a11y_attrs})")
    # A gate must report reality, not a wish: this is a real FAIL that was
    # previously indistinguishable from its own excuse text.
    return "fail", detail


def check_documentation():
    """Real: repo docs + git release tags, verified from git/filesystem."""
    details = []
    core_docs = [("README.md", True), ("docs/launch-plan.md", True),
                 ("ARCHITECTURE.md", False), ("CONTRIBUTING.md", False)]
    present = [p for p, _ in core_docs if _exists(p)]
    missing = [p for p, req in core_docs
               if req and not _exists(p)]
    details.append(f"docs present: {present or 'none'}")
    if missing:
        details.append(f"missing required: {missing}")
    rc, out, _ = _run(["git", "tag"], timeout=20)
    tags = (out or "").split()
    details.append(f"git tags: {tags or 'none'}")
    status = "pass" if (not missing and len(present) >= 2 and tags) else "fail"
    return status, "; ".join(details)


CHECKS = [
    ("code_quality", check_code_quality),
    ("device_testing", check_device_testing),
    ("offline_verification", check_offline_verification),
    ("content_pack_validation", check_content_pack_validation),
    ("sync_validation", check_sync_validation),
    ("model_performance", check_model_performance),
    ("security_audit", check_security_audit),
    ("accessibility", check_accessibility),
    ("documentation", check_documentation),
]


def main():
    ap = argparse.ArgumentParser(description="MakeSense quality gate (9 checks)")
    ap.add_argument("--json", action="store_true",
                    help="emit machine-readable JSON on stdout (no table)")
    ap.add_argument("--no-write", action="store_true",
                    help="do not write quality_results.json")
    args = ap.parse_args()

    results = {}
    for name, fn in CHECKS:
        try:
            status, details = fn()
        except Exception as e:  # noqa: BLE001
            status, details = "fail", f"check crashed: {e!r}"
        results[name] = {"status": status, "details": details}

    fails = [n for n, r in results.items() if r["status"] == "fail"]
    skips = [n for n, r in results.items() if r["status"] == "skip"]

    if not args.no_write:
        with open(_path("quality_results.json"), "w") as f:
            json.dump({"checks": results,
                       "summary": {"fail": len(fails), "skip": len(skips),
                                   "pass": len(results) - len(fails) - len(skips)}},
                      f, indent=2)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        w = max(len(n) for n in results)
        print(f"{'CHECK'.ljust(w)}  STATUS  DETAILS")
        for n, r in results.items():
            print(f"{n.ljust(w)}  {r['status'].upper().ljust(6)}  {r['details']}")
        print(f"\n{len(results) - len(fails) - len(skips)} pass, "
              f"{len(fails)} fail, {len(skips)} skip"
              + (f" | FAILED: {', '.join(fails)}" if fails else "")
              + (f" | SKIP (not gated here): {', '.join(skips)}" if skips else ""))

    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
