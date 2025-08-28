import sqlite3

# Connect to your database
conn = sqlite3.connect("chat_history.db")
cursor = conn.cursor()

print("\n📋 TABLES IN DATABASE:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for t in tables:
    print("-", t[0])

print("\n📐 SCHEMA FOR EACH TABLE:")
for t in tables:
    print(f"\n--- {t[0]} ---")
    cursor.execute(f"PRAGMA table_info({t[0]});")
    for col in cursor.fetchall():
        # col format: (cid, name, type, notnull, dflt_value, pk)
        print(f"{col[1]} ({col[2]}) {'[PRIMARY KEY]' if col[5] == 1 else ''}")

print("\n✅ SAMPLE DATA FROM FEEDBACK TABLE:")
try:
    cursor.execute("SELECT * FROM feedback LIMIT 5;")
    for row in cursor.fetchall():
        print(row)
except:
    print("⚠️ No feedback table or no data found.")

print("\n✅ SAMPLE DATA FROM CHAT_HISTORY TABLE:")
try:
    cursor.execute("SELECT * FROM chat_history LIMIT 5;")
    for row in cursor.fetchall():
        print(row)
except:
    print("⚠️ No chat_history table or no data found.")

conn.close()
