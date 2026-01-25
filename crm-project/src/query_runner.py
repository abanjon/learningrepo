# File: query_runner.py
import psycopg2
import csv


class QueryRunner:
    """
    Executes SQL queries and exports results.

    Design pattern: Separate query execution from business logic.
    This class handles database interaction, your app uses the results.
    """

    def __init__(self, db_config):
        """
        Initialize with database configuration.
        Don't connect yet - connection will be made in __enter__
        """
        self.db_config = db_config  # Store config
        self.conn = None  # Will be set in __enter__
        self.cursor = None  # Will be set in __enter__
        print("QueryRunner initialized (connection not yet established)")

    def __enter__(self):
        """
        Context manager entry point
        Called when using 'with QueryRunner()'
        """
        print("QueryRunner: Establishing connection...")
        self.conn = psycopg2.connect(**self.db_config)
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit point
        Always called, even if an error occurred
        """
        print("QueryRunner: Closing connection...")
        self.close()
        if exc_type:
            print(f"QueryRunner error: {exc_val}")
        return False

    def run_query(self, sql, params=None):
        """
        Execute query and return results as list of dictionaries.

        Args:
            sql: SQL query string
            params: Optional tuple of parameters for %s placeholders
                   Example: ("New", 5) for "WHERE status = %s LIMIT %s"

        Returns:
            List of dicts: [{'column': value, ...}, ...]

        Why dictionaries instead of tuples?
        - More readable: row['company_name'] vs row[0]
        - Self-documenting: know what each value represents
        - Resilient: column order changes don't break code
        """
        # Execute query with optional parameters
        # Using params prevents SQL injection attacks:
        #   SAFE:   cursor.execute("WHERE id = %s", (user_input,))
        #   UNSAFE: cursor.execute(f"WHERE id = {user_input}")
        self.cursor.execute(sql, params)

        # cursor.description is metadata about result columns
        # It's a tuple of tuples: ((name, type, size, ...), ...)
        # We only need the first element (name) from each tuple
        # List comprehension: [desc[0] for desc in self.cursor.description]
        columns = [desc[0] for desc in self.cursor.description]

        # Fetch all rows as tuples: [(val1, val2, ...), ...]
        rows = self.cursor.fetchall()

        # Transform tuples to dictionaries using zip
        # zip(columns, row) pairs each column name with its value
        # dict() converts pairs to dictionary
        # List comprehension does this for every row
        results = [dict(zip(columns, row)) for row in rows]

        return results

    def run_query_from_file(self, filepath, query_name):
        """
        Read SQL file, find named query, execute it.

        SQL file format:
        -- @query: query_name_here
        SELECT ...

        -- @query: another_query
        SELECT ...
        """
        # TODO: Read file, parse queries, find the one matching query_name, run it
        pass

    def export_to_csv(self, sql, output_file, params=None):
        """
        Run query and export results to CSV file.

        Args:
            sql: SQL query to execute
            output_file: Path to output CSV file
            params: Optional query parameters

        Returns:
            Number of rows exported

        Why separate export method?
        - Handles file I/O (different concern than querying)
        - Can add formatting/encoding logic here
        - Easier to test independently
        """
        # Get results as dictionaries
        results = self.run_query(sql, params)

        # Handle empty results gracefully
        if not results:
            print(f"No results to export to {output_file}")
            return 0

        # Open file in write mode
        # newline='' prevents extra blank lines on Windows
        with open(output_file, "w", newline="") as f:
            # Get column names from first result dictionary
            # .keys() returns all keys (column names)
            # list() converts to list for DictWriter
            fieldnames = list(results[0].keys())

            # DictWriter writes dictionaries to CSV
            # It knows to match dict keys to CSV columns
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            # Write header row (column names)
            writer.writeheader()

            # Write all data rows
            # writerows() takes list of dicts, writes each as row
            writer.writerows(results)

        print(f"Exported {len(results)} rows to {output_file}")
        return len(results)

    def get_summary_stats(self, table_name):
        """
        Get quick stats about a table.

        This is a convenience method - combines multiple queries
        into one function call. Demonstrates method composition.
        """
        stats = {}

        # Total row count
        stats["total_rows"] = self.run_query(
            f"SELECT COUNT(*) as count FROM {table_name}"
        )[0]["count"]

        # Column names and types
        column_info = self.run_query(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s
        """,
            (table_name,),
        )
        stats["columns"] = column_info

        return stats

    def close(self):
        """
        Close database connection.

        Always call this when done! Prevents resource leaks.
        Alternative: use context manager (we'll learn later).
        """
        self.cursor.close()
        self.conn.close()
        print("Connection closed")
