import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect("water_bot.db")

# Read the SQL file
with open("triggers.sql", "r") as f:
    sql_script = f.read()

# Execute the script
cursor = conn.cursor()
cursor.executescript(sql_script)

# Commit changes and close the connection
conn.commit()
conn.close()

print("Triggers and logic successfully applied!")
