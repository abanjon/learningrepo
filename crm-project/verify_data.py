import psycopg2

db_config = {
    "host": "localhost",
    "database": "crm_dev",
    "user": "postgres",
    "password": "dev123",
}

conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

cursor.execute("SELECT * FROM leads ORDER BY id")
leads = cursor.fetchall()

print("All leads in database:")
print("-" * 80)
for lead in leads:
    print(f"ID: {lead[0]}")
    print(f"Company: {lead[1]}")
    print(f"Contact: {lead[2]}")
    print(f"Email: {lead[3]}")
    print(f"Industry: {lead[4]}")
    print(f"Status: {lead[5]}")
    print(f"Created At: {lead[6]}")
    print()

cursor.close()
conn.close()
