# create_tables.py

from db import get_connection


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS artists (
        artist_id SERIAL PRIMARY KEY,


        )
        """)
