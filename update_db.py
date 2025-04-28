# update_db.py
import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# ALTER TABLE 실행
cursor.execute("ALTER TABLE messages ADD COLUMN reply TEXT;")
conn.commit()
conn.close()

print("✅ Database updated successfully!")
