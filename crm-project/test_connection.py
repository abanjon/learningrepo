# File: test_connection.py
import psycopg2
from pyscopg2.extras import execute_batch

# Connection parameters
db_config = {
    "host": "127.0.0.1",
    "port": "5432",
    "database": "crm_dev",
    "user": "postgres",
    "password": "dev123",
}

# Connect to PostgreSQL
print("Connecting to PostgreSQL...")
conn = psycopg2.connect(**db_config)
print("Connected successfully!")

# Create a cursor object
cursor = conn.cursor()

# Execute a test query
cursor.execute("SELECT version();")


# Fetch and print result
result = cursor.fetchone()
print("\nPostgreSQL version:")
print(result[0])

cursor.execute(
    "CREATE TABLE IF NOT EXISTS test_users (id serial PRIMARY KEY, name VARCHAR(255));"
)


# cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)", (100, "abc'def"))

users = {("Aban",), ("ADMIN",), ("DEV",)}

cursor.executemany("INSERT INTO test_users (name) VALUES (%s)", users)

conn.commit()

cursor.execute("SELECT * FROM test_users;")

test_result = cursor.fetchall()
for item in test_result:
    print(item)


# Close cursor and connection
cursor.close()
conn.close()
print("\nConnection closed.")
