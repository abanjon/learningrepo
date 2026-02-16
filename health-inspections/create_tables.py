# create_tables.py

from db import get_connection


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inspections (
        inspection_id SERIAL PRIMARY KEY,
        restaurant_name VARCHAR(200) NOT NULL,
        inspection_date DATE NOT NULL,
        score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100)
        );
    """)

    conn.commit()
    print("Table 'inspections' created.")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    create_tables()
