#!/usr/bin/env python3
import os
import re
import subprocess
import sys
from pathlib import Path

# Patterns to look for (common secrets)
PATTERNS = [
    ('AWS Access Key ID', r'AKIA[0-9A-Z]{16}'),
    ('AWS Secret Access Key', r'[0-9a-zA-Z/+]{40}'),
    ('Google API Key', r'AIza[0-9A-Za-z\\-_]{35}'),
    ('Firebase', r'AAAA[0-9A-Za-z\\-_]{35}'),
    ('GitHub Personal Access Token', r'ghp_[0-9a-zA-Z]{36}'),
    ('GitHub OAuth Access Token', r'gho_[0-9a-zA-Z]{36}'),
    ('GitHub Refresh Token', r'ghr_[0-9a-zA-Z]{76}'),
    ('GitHub App Token', r'ghs_[0-9a-zA-Z]{36}'),
    ('Slack Token', r'xox[baprs]-[0-9a-zA-Z]{10,48}'),
    ('Generic API Key', r'[0-9a-zA-Z]{32,45}'),
    ('Private Key', r'-----BEGIN [A-Z ]+ PRIVATE KEY-----'),
    ('Password in assignment', r'(?i)(password|passwd|pwd|secret|key|token|auth)[ \\t]*[=:][ \\t]*\\S{4,}'),
    ('Basic Auth', r'[a-zA-Z0-9_\\-]+:[a-zA-Z0-9_\\-]+@[^\\s]+'),
]

def scan_file(filepath):
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                for name, pattern in PATTERNS:
                    if re.search(pattern, line):
                        results.append((filepath, i, name, line.rstrip()))
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
    return results

def scan_git_history():
    # Get all file paths from git ls-tree
    cmd = ['git', 'ls-tree', '-r', 'HEAD', '--name-only']
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
        files = output.strip().split('\n')
    except subprocess.CalledProcessError:
        # Fallback to walking the working tree
        files = []
        for root, dirs, filenames in os.walk('.'):
            # Skip .git directory
            if '.git' in root:
                continue
            for f in filenames:
                files.append(os.path.join(root, f))
    all_results = []
    for f in files:
        if os.path.isfile(f):
            results = scan_file(f)
            all_results.extend(results)
    return all_results

def main():
    repo_root = Path('.')
    results = scan_git_history()
    report_path = repo_root / 'audit' / 'sensitive_data_report.txt'
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w') as out:
        if not results:
            out.write("No sensitive data patterns found.\n")
        else:
            out.write(f"Found {len(results)} potential sensitive data occurrences:\\n\\n")
            for filepath, line_num, pattern_name, line_content in results:
                out.write(f"File: {filepath}\\n")
                out.write(f"Line: {line_num}\\n")
                out.write(f"Pattern: {pattern_name}\\n")
                out.write(f"Content: {line_content}\\n")
                out.write("-" * 60 + "\\n")
    print(f"Report written to {report_path}")

if __name__ == '__main__':
    main()