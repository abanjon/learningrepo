# queries.py
import re

import psycopg2
import sqlparse as sqp
from db import get_connection


def parse_queries(filepath: str) -> dict:

    try:
        with open(filepath, "r") as file:
            content: str = file.read()
            queries: list[str] = sqp.split(content)
        print(queries)

    except FileNotFoundError:
        print(f"{filepath} was not found.")


if __name__ == "__main__":
    parse_queries("queries.sql")
