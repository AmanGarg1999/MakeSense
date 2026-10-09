import sqlite3
conn = sqlite3.connect('/run/media/huntingvision/1c514555-9d09-44e0-8fcc-e90fcada2549/.hermes/profiles/dwight/cron/executions.db')
cursor = conn.cursor()
cursor.execute('SELECT job_id, status, error, started_at, finished_at FROM executions WHERE job_id = "981c7b9e01e0" ORDER BY started_at DESC LIMIT 10')
for row in cursor.fetchall():
    print(f'Job: {row[0]}')
    print(f'Status: {row[1]}')
    print(f'Error: {row[2]}')
    print(f'Started: {row[3]}')
    print(f'Finished: {row[4]}')
    print('---')