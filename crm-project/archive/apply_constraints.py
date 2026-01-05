import psycopg2
from data_loader import CSVLoader

db_config = {
    "host": "localhost",
    "database": "crm_dev",
    "user": "postgres",
    "password": "dev123"
}

conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

with open('add_constraints.sql', 'r') as f:
    sql = f.read()
    cursor.execute(sql)

conn.commit()
print("Constraints added successfully")
cursor.close()
conn.close()
