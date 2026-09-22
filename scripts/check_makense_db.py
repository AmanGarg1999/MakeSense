import sqlite3
conn = sqlite3.connect('/home/huntingvision/.hermes/kanban/boards/makense/kanban.db')
cursor = conn.cursor()
cursor.execute('SELECT id, title, status FROM tasks ORDER BY id')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1][:80]} ({row[2]})')
conn.close()