import psycopg2
import csv
from datetime import datetime

class QueryRunner:
    """
    Executes SQL queries and exports results.
    """

    def __init__(self, db_config):

        self.conn = psycopg2.connect(**db_config)
        self.cursor = self.conn.cursor()
        print("QueryRunner initialized")


    def run_query(self, sql, params=None):
        """
        Execute Query and return results as list of dicts.
        Args:
            sql: SQL query string.
            params: Optional tuple of parameters for %s placeholders
                    Example: ("New", 5) for "WHERE status = %s LIMIT %s"
        Returns:
            List of dicts [{'column': value, ...}, ...]
        """

        self.cursor.execute(sql, params)
        columns = [desc[0] for desc in self.cursor.description]
        rows = self.cursor.fetchall()
        results = [dict(zip(columns, row)) for row in rows]

        return results

    def export_to_csv(self, sql, output_file, params=None):
        """
        Run query and export results to CSV file.
        Args:
            sql: SQL query to execute
            output_file: Path to output CSV file
            params: Optional query paramaters
        Returns:
            Number of rows exported
        """

        results = self.run_query(sql, params)

        if not results:
            print(f"No results to export to {output_file}")
            return 0

        with open(output_file, 'w', newline='') as f:
            fieldnames = list(results[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        print(f"Exported {len(results)} rows to {output_file}")
        return len(results)

    def get_summary_stats(self, table_name):
        """
        Get quick stats about a table.
        """
        stats = {}
        stats['total_rows'] = self.run_query(
            f"SELECT COUNT(*) as count FROM {table_name}"
        )[0]['count']

        column_info = self.run_query(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s
        """, (table_name,))
        stats['columns'] = column_info

        return stats

    def close(self):
        """
        Close database connection.
        """
        self.cursor.close()
        self.conn.close()
        print("Connection closed")



