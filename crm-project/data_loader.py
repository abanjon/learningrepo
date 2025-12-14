import csv
import psycopg2


class CSVLoader:
    """Loads CSV fies into PostgreSQL tables"""

    def __init__(self, db_config):
        """
        Initialize loader with database connection
        Args:
            db_config: Dictionary with connection parameters
        """
        # Create connection and store it in instance variable
        self.conn = psycopg2.connect(**db_config)
        self.cursor = self.conn.cursor()
        print("CSVLoader initialized and connected to database")

    def load_csv(self, filepath, table_name):
        """
        Load CSV file into specified table
        Args:
            filepath: Path to CSV file
            table_name: Name of database table to load into
        """
        print(f"Loading {filepath} into {table_name}...")

        with open(filepath, "r") as f:
            reader = csv.DictReader(f)

            row_count = 0

            for row in reader:
                company_name = row["company_name"]
                contact_person = row["contact_person"]
                email = row["email"]
                industry = row["industry"]
                status = row["status"]

                sql = """
              INSERT INTO leads (company_name, contact_person, email, industry, status)
              VALUES (%s, %s, %s, %s, %s)
          """

                self.cursor.execute(
                    sql, (company_name, contact_person, email, industry, status)
                )
                row_count += 1

        self.conn.commit()
        print(f"Loaded {row_count} rows succesfully")

    def get_row_count(self, table_name):
        """
        Get count of rows in table
        Args:
            table_name: Name of table to count
        Returns:
            Number of rows as integer
        """
        self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = self.cursor.fetchone()[0]
        return count

    def clear_table(self, table_name):
        """Delete all rows from table"""

        self.cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY")
        self.conn.commit()
        print(f"Cleared {table_name} table")

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()
        print("Connection Closed!")



if __name__ == "__main__":
    db_config = {
        "host": "localhost",
        "database": "crm_dev",
        "user": "postgres",
        "password": "dev123"
    }

    loader = CSVLoader(db_config)
    loader.load_csv('leads_sample.csv', 'leads')


    count = loader.get_row_count('leads')
    print(f"Total rows in leads table: {count}")

    loader.close()
