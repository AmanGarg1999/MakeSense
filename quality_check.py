import json
import os
import subprocess

# Quality gate checks
checks = {
    'code_quality': {'status': 'unknown', 'details': ''},
    'device_testing': {'status': 'unknown', 'details': ''},
    'offline_verification': {'status': 'unknown', 'details': ''},
    'content_pack_validation': {'status': 'unknown', 'details': ''},
    'sync_validation': {'status': 'unknown', 'details': ''},
    'model_performance': {'status': 'unknown', 'details': ''},
    'security_audit': {'status': 'unknown', 'details': ''},
    'accessibility': {'status': 'unknown', 'details': ''},
    'documentation': {'status': 'unknown', 'details': ''}
}

# 1. Code Quality - run tests
result = subprocess.run(['python3', '-m', 'pytest', 'scripts/tests/test_correct_schema.py', '-v', '--tb=short'], capture_output=True, text=True, timeout=60)
checks['code_quality']['status'] = 'pass' if result.returncode == 0 else 'fail'
checks['code_quality']['details'] = f'Return code: {result.returncode}'

# 2. Check if model artifacts exist
model_artifacts = os.path.exists('/home/huntingvision/workspace_drive/workspaces/MakeSense/models/artifacts')
checks['model_performance']['status'] = 'pass' if model_artifacts else 'fail'
checks['model_performance']['details'] = f'Models directory exists: {model_artifacts}'

# 3. Check content packs
content_packs = os.path.exists('/home/huntingvision/workspace_drive/workspaces/MakeSense/packs/dist')
checks['content_pack_validation']['status'] = 'pass' if content_packs else 'fail'
checks['content_pack_validation']['details'] = f'Packs dist exists: {content_packs}'

# 4. Check frontend build
frontend_dist = os.path.exists('/home/huntingvision/workspace_drive/workspaces/MakeSense/frontend/dist')
checks['code_quality']['details'] += f', Frontend dist: {frontend_dist}'

# 5. Check documentation
arch_doc = os.path.exists('/home/huntingvision/workspace_drive/workspaces/MakeSense/ARCHITECTURE.md')
contrib_doc = os.path.exists('/home/huntingvision/workspace_drive/workspaces/MakeSense/CONTRIBUTING.md')
checks['documentation']['status'] = 'pass' if (arch_doc and contrib_doc) else 'fail'
checks['documentation']['details'] = f'ARCHITECTURE.md: {arch_doc}, CONTRIBUTING.md: {contrib_doc}'

# 6. Check server imports
result = subprocess.run(['python3', 'server/test_imports.py'], capture_output=True, text=True)
checks['code_quality']['details'] += f', Server imports: {"OK" if result.returncode == 0 else "FAIL"}'

# 7. Device testing - no physical devices
checks['device_testing']['status'] = 'fail'
checks['device_testing']['details'] = 'No physical devices available for testing'

# 8. Offline verification - only placeholder tests
checks['offline_verification']['status'] = 'fail'
checks['offline_verification']['details'] = 'Only placeholder tests exist'

# 9. Sync validation - check if tests exist
sync_tests = os.path.exists('/home/huntingvision/workspace_drive/workspaces/MakeSense/scripts/tests/test_offline_scenarios.py')
checks['sync_validation']['status'] = 'pass' if sync_tests else 'fail'
checks['sync_validation']['details'] = f'Offline sync tests exist: {sync_tests}'

# 10. Security audit
checks['security_audit']['status'] = 'fail'
checks['security_audit']['details'] = 'Only DPDP wire scan placeholder'

# 11. Accessibility
checks['accessibility']['status'] = 'fail'
checks['accessibility']['details'] = 'No WCAG 2.1 AA tests implemented'

# 12. Check for GitHub releases
result = subprocess.run(['git', 'tag'], cwd='/home/huntingvision/workspace_drive/workspaces/MakeSense', capture_output=True, text=True)
has_tags = len(result.stdout.strip()) > 0
checks['documentation']['details'] += f', Git tags: {has_tags}'

# Write results
with open('/home/huntingvision/workspace_drive/workspaces/MakeSense/quality_results.json', 'w') as f:
    json.dump(checks, f, indent=2)

print(json.dumps(checks, indent=2))