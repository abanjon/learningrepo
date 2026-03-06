# create_tables.py
import psycopg2
from db import get_connection


def create_tables() -> None:
    conn: psycopg2.extensions.connection = get_connection()
    cursor: psycopg2.extensions.cursor = conn.cursor()

    queries: list[str] = [
        """
        CREATE TABLE IF NOT EXISTS artists (
        artist_id SERIAL PRIMARY KEY,
        name VARCHAR(150) NOT NULL,
        genre VARCHAR(100),
        country VARCHAR(100),
        year_formed SMALLINT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS albums (
        album_id SERIAL PRIMARY KEY,
        title VARCHAR(150) NOT NULL,
        artist_id BIGINT REFERENCES artists(artist_id),
        release_date DATE,
        record_label VARCHAR(200)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS tracks (
        track_id SERIAL PRIMARY KEY,
        title VARCHAR(150) NOT NULL,
        album_id BIGINT REFERENCES albums(album_id),
        duration_seconds SMALLINT CHECK (duration_seconds > 0),
        track_number BIGINT CHECK (track_number > 0)
        );
        """,
    ]

    try:
        for query in queries:
            cursor.execute(query)

        conn.commit()
        print("Tables created succesfully.")
    except Exception as e:
        print(f"An error occured: {e}")
        if conn:
            conn.rollback()

    finally:
        if conn:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    create_tables()
