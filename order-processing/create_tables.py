# create_tables.py
from db import get_connection


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
        order_id SERIAL PRIMARY KEY,
        customer_email VARCHAR(255) NOT NULL,
        order_date DATE NOT NULL,
        total_amount DECIMAL(10, 2) NOT NULL,
        status VARCHAR(50)
        );
    """)

    conn.commit()
    print("Table 'orders' created.")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    create_tables()
