import psycopg2
from data_loader import CSVLoader

db_config = {
    "host": "localhost",
    "database": "crm_dev",
    "user": "postgres",
    "password": "dev123"
    }

loader = CSVLoader(db_config)

loader.clear_table("leads")

loader.load_csv('leads_large.csv', 'leads')

row_count = loader.get_row_count('leads')
print(f"Total rows in leads table: {row_count}")

conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

cursor.execute("SELECT * FROM leads ORDER BY id LIMIT 5")
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

loader.close()


