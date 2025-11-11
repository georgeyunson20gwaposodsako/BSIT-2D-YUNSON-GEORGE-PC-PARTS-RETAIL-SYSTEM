import sqlite3

# Connect or create the database
conn = sqlite3.connect("pcstoreDB.db")
cursor = conn.cursor()

# Create the user table if it doesn’t exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
""")

conn.commit()
conn.close()

print("✅ Database and user table created successfully!")
