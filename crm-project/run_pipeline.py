"""
* Main Entry Point for CRM ETL pipeline.
* Run this to process all CSV files in input directory
"""

import sys
import config

from src.pipeline import ETL
from logging_config import setup_logging


def main():
    """Execute ETL pipeline"""
    setup_logging()

    print("=" * 80)
    print("CRM ETL Pipeline")
    print("=" * 80)

    try:
        config_params = {
            "db_config": config.DB_CONFIG,  # Use config.DB_CONFIG (dot notation)
            "paths": config.PATHS,  # Use config.PATHS (dot notation)
            "validations": {
                "allowed_industries": config.ALLOWED_INDUSTRIES,  # Use dot notation
                "valid_statuses": config.VALID_STATUSES,  # Use dot notation
            },
        }

        print(f"Database: {config_params['db_config']['database']}")
        print(f"Input directory: {config_params['paths']['input']}")
        print(f"Valid statuses: {config_params['validations']['valid_statuses']}")

        pipeline = ETL(config_params)

        print("\nProcessing files..")
        pipeline.process_all_files()

        print("\nGenerating reports..")
        pipeline.generate_reports()

        summary = pipeline.get_summary()

        # Print results
        print("\n" + "=" * 80)
        print("PIPELINE SUMMARY")
        print("=" * 80)
        print(f"Files processed: {summary['files_processed']}")
        print(f"Total rows loaded: {summary['total_rows_loaded']}")
        print(f"Total errors: {summary['total_errors']}")
        print("=" * 80)

        return 0

    except Exception as e:
        print(f"\nPIPELINE FAILED: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
