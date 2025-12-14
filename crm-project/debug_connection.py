import psycopg2

dsn = "dbname=crm_dev user=postgres password=dev123 host=127.0.0.1 port=5432"

try:
    conn = psycopg2.connect(dsn)
    print("Connection successful!")
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    print(cursor.fetchone()[0])
    conn.close()
except Exception as e:
    print(f"Failed: {e}")
