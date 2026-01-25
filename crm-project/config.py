# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "crm_dev",
    "user": "postgres",
    "password": "dev123",
}


# Directory paths
PATHS = {
    "input": "data/input",
    "processed": "data/processed",
    "failed": "data/failed",
    "reports_daily": "reports/daily",
    "reports_errors": "reports/errors",
    "logs": "logs/",
}


# Validations
ALLOWED_INDUSTRIES = [
    "Technology",
    "Healthcare",
    "Finance",
    "Manufacturing",
    "Retail",
    "Education",
    "Other",
]

VALID_STATUSES = ["New", "Contacted", "Qualified", "Proposal Sent", "Converted", "Lost"]

# Logging
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = "logs/etl_pipeline.log"
ERROR_LOG_FILE = "logs/etl_errors.log"  # <-- ADD THIS LINE
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
