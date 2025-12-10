import psycopg2


db_config = {
    "host" : "localhost",
    "database" : "crm_dev",
    "user" : "postgres",
    "password" : "dev123"
}


conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

with open('schema.sql', 'r') as f:
    schema_sql =f.read()
    
cursor.execute("DROP TABLE IF EXISTS leads;")
conn.commit()
    
print("Creating leads table...")
cursor.execute(schema_sql)
conn.commit()

print("Table created successfuly!")

cursor.execute("""
               SELECT column_name, data_type
               FROM information_schema.columns
               WHERE table_name = 'leads'
               """)

columns = cursor.fetchall()
print("\nTable Structure:")
for col in columns:
    print(f"  {col[0]}: {col[1]}")
    
cursor.close()
conn.close()