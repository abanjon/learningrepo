# File: test_connection.py
import psycopg2

# Connection parameters
db_config = {
    "host": "localhost",
    "database": "crm_dev",
    "user": "postgres",
    "password": "dev123"
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

# Close cursor and connection
cursor.close()
conn.close()
print("\nConnection closed.")