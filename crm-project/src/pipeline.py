import os
import shutil
import logging
import pandas as pd
from datetime import datetime

from src.data_loader import CSVLoader
from src.validator import LeadValidator
from src.query_runner import QueryRunner


logger = logging.getLogger(__name__)


class ETL:
    def __init__(self, config_params):
        """
        Initialize pipeline with configuration

        Create instance of:
        - CSVLoader (for loading data)
        - QueryRunner (for analytics)
        - LeadValidator (for validation)

        Set up logging
        Track statistics
        """
        self.config = config_params
        self.validator = LeadValidator()

        logger.info("Initialized Dependencies")

        self.total_files = 0
        self.total_rows = 0
        self.total_errors = 0

    def move_file(self, filepath, destination):
        filename = os.path.basename(filepath)
        dest_dir = self.config["paths"][destination]  # Use dictionary key access
        dest_path = os.path.join(dest_dir, filename)

        shutil.move(filepath, dest_path)
        logger.info(f"Moved {filename} to {destination}")

    def process_file(self, filepath):
        """Split CSV into valid and invalid rows, process separately"""
        logger.info(f"Splitting and processing {filepath}")

        try:
            # Read the CSV
            df = pd.read_csv(filepath, dtype=str)

            df = df.fillna("")

            valid_rows = []
            invalid_rows = []

            # Validate each row
            for idx, row in df.iterrows():
                row_dict = row.to_dict()
                if self.validator.validate_lead(row_dict):
                    valid_rows.append(row_dict)
                else:
                    invalid_rows.append(row_dict)

            # Process valid rows if any exist
            if valid_rows:
                valid_filename = f"valid_{os.path.basename(filepath)}"
                valid_filepath = os.path.join("data/processed", valid_filename)

                # Write valid rows to new CSV
                pd.DataFrame(valid_rows).to_csv(valid_filepath, index=False)

                # Load valid rows to database
                with CSVLoader(self.config["db_config"]) as loader:
                    stats = loader.load_csv(valid_filepath, "leads")
                    self.total_rows += stats["loaded"]
                    self.total_errors += stats["failed"]

            # Save invalid rows if any exist
            if invalid_rows:
                invalid_filename = f"invalid_{os.path.basename(filepath)}"
                invalid_filepath = os.path.join("data/failed", invalid_filename)
                pd.DataFrame(invalid_rows).to_csv(invalid_filepath, index=False)

            # Move original file to archive
            archive_dir = os.path.join(
                "data/archive", datetime.now().strftime("%Y%m%d")
            )
            os.makedirs(archive_dir, exist_ok=True)
            shutil.move(filepath, os.path.join(archive_dir, os.path.basename(filepath)))

            self.total_files += 1

        except Exception as e:
            logger.error(f"Error splitting {filepath}: {e}")
            self.move_file(filepath, "failed")

    def process_all_files(self):
        """Process all CSV files in input directory"""
        logger.info("Starting pipeline execution")

        input_dir = self.config["paths"][
            "input"
        ]  # Use dictionary key access, not dot notation
        print(f"Looking for files in: {input_dir}")

        csv_files = [f for f in os.listdir(input_dir) if f.endswith(".csv")]

        for filename in csv_files:
            filepath = os.path.join(input_dir, filename)
            self.process_file(filepath)

        logger.info("Pipeline execution complete")

    def generate_reports(self):
        """Generate all analytics reports"""
        logger.info("Generating reports")

        with QueryRunner(self.config["db_config"]) as runner:
            runner.export_to_csv(
                "SELECT status, COUNT(*) as count FROM leads GROUP BY status",
                "reports/daily/leads_by_status.csv",
            )

            runner.export_to_csv(
                "SELECT industry, COUNT(*) as count FROM leads GROUP BY industry",
                "reports/daily/leads_by_industry.csv",
            )

            # Error report (simpler version)
            runner.export_to_csv(
                """SELECT
                    'Total Rows' as metric,
                    COUNT(*) as value
                  FROM leads
                  UNION ALL
                  SELECT
                    'Rows by Status' as metric,
                    COUNT(*) as value
                  FROM leads
                  WHERE status IS NOT NULL
                  UNION ALL
                  SELECT
                    'Rows without Industry' as metric,
                    COUNT(*) as value
                  FROM leads
                  WHERE industry IS NULL OR industry = ''""",
                "reports/errors/data_quality_report.csv",
            )

        logger.info("Reports generated")

    def get_summary(self):
        """Return pipeline execution summary"""
        return {
            "files_processed": self.total_files,
            "total_rows_loaded": self.total_rows,
            "total_errors": self.total_errors,
        }
