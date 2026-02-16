# validator.py

import logging
import re
from datetime import datetime

from exceptions import BatchValidationError, FieldValidationError

# configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class OrderValidator:
    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

    def __init__(self):
        self.valid_orders = []
        self.errors_by_record = {}  # record_index -> list of FieldValidationError

    def validate_email(self, email: str) -> str:
        email = str(email).strip()
        if not self.EMAIL_REGEX.match(email):
            raise FieldValidationError("customer_email", email, "invalid email format")

        return email

    def validate_amount(self, amount) -> float:
        try:
            val = float(amount)
        except (ValueError, TypeError):
            raise FieldValidationError("total_amount", amount, "must be a number")

        if val <= 0:
            raise FieldValidationError("total_amount", val, "must be greater than zero")

        return val

    def validate_record(self, index: int, record: dict) -> dict | None:
        errors = []
        cleaned = {}

        # validate email
        try:
            cleaned["customer_email"] = self.validate_email(
                record.get("customer_email")
            )
        except FieldValidationError as e:
            errors.append(e)

        # validate amount
        try:
            cleaned["total_amount"] = self.validate_amount(record.get("total_amount"))
        except FieldValidationError as e:
            errors.append(e)

        # static fields
        cleaned["order_date"] = record.get("order_date")
        cleaned["status"] = record.get("status", "pending")

        if errors:
            self.errors_by_record[index] = errors
            logger.warning("Record %d failed: %s", index, [str(e) for e in errors])
            return None

        return cleaned

    def process_batch(self, records: list[dict]):
        logger.info("Processing batch of %d records", len(records))

        for i, record in enumerate(records):
            cleaned = self.validate_record(i, record)
            if cleaned:
                self.valid_orders.append(cleaned)

        if self.errors_by_record:
            logger.info(
                "Batch complete with %d invalid records", len(self.errors_by_record)
            )
        else:
            logger.info("Batch complete: all records valid")
