import csv
import psycopg2
import logging
from datetime import datetime
from validator import LeadValidator # Import our validator

# Configure logging (do this ONCE at module level, not in __init__)
logging.basicConfig(
    filename = 'etl_errors.log',
    level = logging.ERROR,
    format = '%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

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
        self.validator = LeadValidator() # Create validator instance
        print("CSVLoader initialized and connected to database")

    def load_csv(self, filepath, table_name):
      """
      Load CSV with validation.

      Returns:
          dict with stats: {
                'total_rows': int,
                'loaded': int,
                'failed': int,
                'errors': list of dicts
                }
      """
      print(f"Loading {filepath} into {table_name}...")
      logger.info(f"Starting load: {filepath} -> {table_name}")

      # Track stats
      stats = {
          'total_rows': 0,
          'loaded': 0,
          'failed': 0,
          'errors': []
      }

      with open(filepath, 'r') as f:
          reader = csv.DictReader(f)

          for row_num, row in enumerate(reader, start=1):
              stats['total_rows'] += 1

              # Validate before inserting
              if self.validator.validate_lead(row):
                  # Valid - insert to db
                  try:
                      sql = """
                          INSERT INTO leads (company_name, contact_person, email, industry, status)
                          VALUES (%s, %s, %s, %s, %s)
                      """
                      self.cursor.execute(sql, (
                          row['company_name'],
                          row.get('contact_person'),
                          row['email'],
                          row.get('industry'),
                          row.get('status', 'New')
                      ))
                      stats['loaded'] += 1

                  except Exception as e:
                      # Database error (e.g, duplicate key) - LOG IT
                      error_msg = f"Row {row_num}: Database error - {str(e)}"
                      logger.error(error_msg)
                      logger.error(f"   Data: {row}")

                      stats['failed'] += 1
                      stats['errors'].append({
                      'row': row_num,
                      'data': row,
                      'error': self.validator.get_errors()
                  })

              else:
                  # Invalid - log errors
                  error_msg = f"Row {row_num}: Validation failed"
                  logger.error(error_msg)
                  logger.error(f"   Errors: {self.validator.get_errors()}")
                  logger.error(f"   Data: {row}")

                  stats['failed'] += 1
                  stats['errors'].append({
                      'row': row_num,
                      'data': row,
                      'error': self.validator.get_errors()
                  })

          # Commit all successful inserts
          self.conn.commit()

      logger.info(f"Load complete: {stats['loaded']} loaded, {stats['failed']} failed")

      return stats

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
