# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "crm_dev",
    "user": "postgress",
    "password": "dev123",
}


# Directory paths
PATHS = {
    "input": "data/input",
    "processed": "data/processed",
    "failed": "data/failed",
    "reports_daily": "reports/daily",
    "reports_errors": "reports/errors",
    "logs": "logs",
}


# Validations
ALLOWED_INDUSTRIES = []
VALID_STATUSES = []

# Logging
LOG_FILE = "logs/etl_pipeline.log"
LOG_FORMAT = ""
