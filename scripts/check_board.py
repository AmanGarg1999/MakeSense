import subprocess
import json

result = subprocess.run(['hermes', 'kanban', 'list', '--json'], capture_output=True, text=True)
data = json.loads(result.stdout)

# Check for tenant field
tenants = set(t.get('tenant') for t in data)
print('Tenants:', tenants)

# Check for workflow_template_id
wt = set(t.get('workflow_template_id') for t in data)
print('Workflow templates:', wt)

# Check for project_id
pids = set(t.get('project_id') for t in data)
print('Project IDs:', pids)

# Check for any board/workspace filtering
# Print all unique workspace_kind and workspace_path
kinds = set(t.get('workspace_kind') for t in data)
print('Workspace kinds:', kinds)

paths = set(t.get('workspace_path') for t in data)
print('Workspace paths:', paths)