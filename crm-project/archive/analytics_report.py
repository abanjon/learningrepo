import psycopg2
from datetime import datetime
import json
from query_runner import QueryRunner

db_config = {
    "host": "localhost",
    "database": "crm_dev",
    "user": "postgres",
    "password": "dev123"
}

def load_queries_from_file(filepath):
    with open(filepath, "r") as f:
        return f.read()

def parse_queries(sql_text):
    """
    Parses a SQL file containing named queries.

    Expected format:
    -- @query: query_name
    SELECT ...

    Returns:
        dict[str, str] -> {query_name: sql}
    """
    queries = {}
    current_name = None
    buffer = []

    for line in sql_text.splitlines():
        line = line.rstrip()

        if line.startswith("-- @query:"):
            # Save previous query if exists
            if current_name:
                queries[current_name] = "\n".join(buffer).strip()

            # Start new query
            current_name = line.split(":", 1)[1].strip()
            buffer = []
        else:
            buffer.append(line)

    # Capture last query
    if current_name:
        queries[current_name] = "\n".join(buffer).strip()

    return queries




if __name__ == "__main__":
    SQL_FILE = "queries.sql"

    runner = QueryRunner(db_config)

    sql_text = load_queries_from_file(SQL_FILE)
    queries = parse_queries(sql_text)

    print(f"Loaded {len(queries)} queries!")

    exports = []
    total_rows = 0

    for name, sql in queries.items():
        output_file = f"{name}.csv"
        row_count = runner.export_to_csv(sql, output_file)

        exports.append({
            "query": name,
            "file": output_file,
            "rows": row_count
        })

        total_rows += row_count


    metadata = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_queries": len(queries),
        "files": exports
    }

    with open("report_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    runner.close()
