# validator.py
import logging
import re
from datetime import datetime

from exceptions import RecordValidationError, ValidationError

# configure logging to both console and file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("validation.log", mode="w"),
    ],
)

logger = logging.getLogger(__name__)


class InspectionValidator:
    """Validates restaurant health inspection records."""

    # regex for inspector IDs: INS- followed by 4 digits
    INSPECTOR_ID_PATTERN = re.compile(r"^INS-\d{4}$")

    def __init__(self):
        self.valid_records = []
        self.invalid_records = []  # list of RecordValidationError

    def validate_required_field(self, field: str, value) -> str:
        if value is None:
            raise ValidationError(field, value, "field is required")
        cleaned = str(value).strip()
        if not cleaned:
            raise ValidationError(field, value, "field cannot be empty")
        return cleaned

    def validate_score(self, value) -> int:
        try:
            score = int(value)
        except (ValueError, TypeError):
            raise ValidationError("score", value, "must be an integer")

        if not (0 <= score <= 100):
            raise ValidationError("score", value, "must be between 0 and 100")
        return score

    def validate_date(self, value) -> str:
        try:
            parsed = datetime.strptime(str(value).strip(), "%Y-%m-%d")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            raise ValidationError(
                "inspection_date", value, "must be in YYYY-MM-DD format"
            )

    def validate_inspector_id(self, value) -> str:
        cleaned = str(value).strip()
        if not self.INSPECTOR_ID_PATTERN.match(cleaned):
            raise ValidationError(
                "inspector_id", value, "must match format INS-XXX (4 digits)"
            )
        return cleaned

    def validate_record(self, record_num: int, record: dict) -> dict | None:
        """Validate all fields in a record, collecting all errors."""
        errors = []
        cleaned = {}

        # wrap each field in try/except to collect ALL errors
        try:
            cleaned["restaurant_name"] = self.validate_required_field(
                "restaurant_name", record.get("restaurant_name")
            )
        except ValidationError as e:
            errors.append(e)

        try:
            cleaned["inspection_date"] = self.validate_date(
                record.get("inspection_date")
            )
        except ValidationError as e:
            errors.append(e)

        try:
            cleaned["score"] = self.validate_score(record.get("score"))
        except ValidationError as e:
            errors.append(e)

        cleaned["violations"] = str(record.get("violations", "")).strip()

        try:
            cleaned["inspector_id"] = self.validate_inspector_id(
                record.get("inspector_id")
            )
        except ValidationError as e:
            errors.append(e)

        if errors:
            error = RecordValidationError(record_num, errors)
            self.invalid_records.append(error)
            logger.warning("Recrd %d failed validation: %s", record_num, error)
            return None

        self.valid_records.append(cleaned)
        logger.info("Record %d passed validation", record_num)
        return cleaned

    def validate_batch(self, records: list[dict]) -> list[dict]:
        logger.info("Starting validation of %d records", len(records))
        valid = []
        for i, record in enumerate(records, start=1):
            result = self.validate_record(i, record)
            if result is not None:
                valid.append(result)

        logger.info(
            "Validation complete: %d valid, %d invalid out of %d total",
            len(valid),
            len(self.invalid_records),
            len(records),
        )
        return valid

    def get_summary(self) -> dict:
        total = len(self.valid_records) + len(self.invalid_records)
        return {
            "total_records": total,
            "valid_count": len(self.valid_records),
            "invalid_count": len(self.invalid_records),
            "pass_rate": f"{len(self.valid_records) / total * 100:.1f}%"
            if total > 0
            else "N/A",
        }
