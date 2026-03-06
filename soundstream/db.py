# db.py
import psycopg2


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="soundstream_dev",
        user="postgres",
        password="postgres",
    )
