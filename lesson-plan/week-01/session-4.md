# Week 1, Session 4: Data Validation & Error Handling

**Domain:** Restaurant Health Inspections
**Concepts:** try/except, custom exceptions, validation patterns, logging, error collection
**Duration:** 45-60 minutes

---

## FOLLOW-ALONG (15-20 min)

### Step 1: Set Up the Project

```bash
docker exec weather_db psql -U student -d postgres -c "CREATE DATABASE inspections;"

uv init health-inspections
cd health-inspections
uv add psycopg2-binary
```

Create `db.py`:

```python
# db.py
import psycopg2

def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="inspections",
        user="student",
        password="learningpass"
    )
```

Create `create_tables.py`:

```python
# create_tables.py
from db import get_connection

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inspections (
            inspection_id SERIAL PRIMARY KEY,
            restaurant_name VARCHAR(200) NOT NULL,
            inspection_date DATE NOT NULL,
            score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
            violations TEXT,
            inspector_id VARCHAR(20) NOT NULL
        );
    """)

    conn.commit()
    print("Table 'inspections' created.")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    create_tables()
```

```bash
uv run python create_tables.py
```

### Step 2: Define Custom Exceptions

Create `exceptions.py`:

```python
# exceptions.py

class ValidationError(Exception):
    """Raised when a single field fails validation.

    Custom exceptions let you be SPECIFIC about what went wrong.
    'except ValidationError' catches only our validation errors,
    while 'except Exception' catches everything (including bugs).
    Being specific means your error handling doesn't accidentally
    swallow real bugs like TypeError or KeyError.
    """

    def __init__(self, field: str, value, message: str):
        # Store structured data about the error, not just a string.
        # This lets code that catches the exception inspect the details
        # programmatically (e.g., "which field failed?") instead of
        # parsing a human-readable string.
        self.field = field
        self.value = value
        self.message = message
        # Call the parent class's __init__ to set the standard
        # exception message (what you see in tracebacks).
        super().__init__(f"{field}: {message} (got: {value!r})")


class RecordValidationError(Exception):
    """Raised when a record has one or more validation errors.

    We collect ALL field errors per record rather than failing on the first.
    This is the "error accumulation" pattern -- essential in data pipelines
    because you want to report every problem in one pass, not make the user
    fix errors one at a time.
    """

    def __init__(self, record_num: int, errors: list[ValidationError]):
        self.record_num = record_num
        self.errors = errors
        error_msgs = "; ".join(str(e) for e in errors)
        super().__init__(f"Record {record_num}: {error_msgs}")
```

### Step 3: Build the InspectionValidator Class

Create `validator.py`:

```python
# validator.py
import re
import logging
from datetime import datetime
from exceptions import ValidationError, RecordValidationError

# Configure logging. We use logging instead of print() because:
# 1. Logging has LEVELS (DEBUG, INFO, WARNING, ERROR, CRITICAL) so you can
#    filter by severity. print() has no severity concept.
# 2. Logging can go to files, not just the console. In production, you need
#    persistent logs that survive after the terminal closes.
# 3. Logging includes timestamps and module names automatically.
# 4. You can enable/disable logging per module without changing code.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        # StreamHandler sends to stderr (console). FileHandler sends to a file.
        # Using both means you see output AND have a persistent record.
        logging.StreamHandler(),
        logging.FileHandler("validation.log", mode="w"),
    ],
)

# getLogger(__name__) creates a logger named after this module ("validator").
# This is a convention: each module gets its own named logger, so log output
# tells you WHERE the message came from.
logger = logging.getLogger(__name__)


class InspectionValidator:
    """Validates restaurant health inspection records.

    Design principle: validate ALL fields in a record before reporting errors.
    This is called "collect-then-report" vs "fail-fast". Fail-fast raises on
    the first error; collect-then-report gathers everything. We use
    collect-then-report because:
    - The user fixes all problems in one pass instead of playing whack-a-mole
    - We can produce statistics ("47% of records have date issues")
    - The pipeline can still process valid records alongside invalid ones
    """

    # This regex validates inspector IDs. Format: INS-XXXX where X is a digit.
    # r"..." is a raw string -- backslashes are literal (no escaping needed).
    # ^       = start of string
    # INS-    = literal characters
    # \d{4}   = exactly 4 digits
    # $       = end of string
    INSPECTOR_ID_PATTERN = re.compile(r"^INS-\d{4}$")

    def __init__(self):
        self.valid_records = []
        self.invalid_records = []  # list of RecordValidationError

    def validate_required_field(self, field: str, value) -> str:
        """Check that a field is present and non-empty after stripping whitespace.

        We strip whitespace because CSV files often have trailing spaces, and
        a field containing only spaces should be treated as empty.
        """
        if value is None:
            raise ValidationError(field, value, "field is required")
        cleaned = str(value).strip()
        if not cleaned:
            raise ValidationError(field, value, "field cannot be empty")
        return cleaned

    def validate_score(self, value) -> int:
        """Validate that score is an integer between 0 and 100."""
        try:
            score = int(value)
        except (ValueError, TypeError):
            raise ValidationError("score", value, "must be an integer")

        if not (0 <= score <= 100):
            raise ValidationError("score", value, f"must be between 0 and 100")

        return score

    def validate_date(self, value) -> str:
        """Validate and normalize the inspection date.

        We accept the date as a string, validate its format, and return
        a normalized ISO format string. This handles cases where the input
        might be '1/15/2024' or '2024-01-15' inconsistently.
        """
        try:
            parsed = datetime.strptime(str(value).strip(), "%Y-%m-%d")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            raise ValidationError(
                "inspection_date", value,
                "must be in YYYY-MM-DD format"
            )

    def validate_inspector_id(self, value) -> str:
        """Validate inspector ID matches the format INS-XXXX."""
        cleaned = str(value).strip()
        if not self.INSPECTOR_ID_PATTERN.match(cleaned):
            raise ValidationError(
                "inspector_id", value,
                "must match format INS-XXXX (4 digits)"
            )
        return cleaned

    def validate_record(self, record_num: int, record: dict) -> dict | None:
        """Validate all fields in a record, collecting all errors.

        This is the core of the collect-then-report pattern. We don't
        short-circuit on the first error -- we validate every field and
        gather all failures into a list.
        """
        errors = []
        cleaned = {}

        # Each validation is wrapped in its own try/except so one field's
        # failure doesn't prevent other fields from being validated.
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

        # Violations can be empty (a clean inspection), so we just strip it
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
            logger.warning("Record %d failed validation: %s", record_num, error)
            return None

        self.valid_records.append(cleaned)
        logger.info("Record %d passed validation", record_num)
        return cleaned

    def validate_batch(self, records: list[dict]) -> list[dict]:
        """Validate a batch of records and return only the valid ones.

        This is the entry point for external callers. It processes all
        records and returns the cleaned valid ones, while storing invalid
        records internally for reporting.
        """
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
        """Return a summary of validation results."""
        total = len(self.valid_records) + len(self.invalid_records)
        return {
            "total_records": total,
            "valid_count": len(self.valid_records),
            "invalid_count": len(self.invalid_records),
            "pass_rate": (
                f"{len(self.valid_records) / total * 100:.1f}%"
                if total > 0
                else "N/A"
            ),
        }
```

### Step 4: Run the Validator

Create `main.py`:

```python
# main.py
import json
from validator import InspectionValidator

# Sample data -- some records are intentionally invalid to demonstrate
# error collection. In a real pipeline, this data would come from a CSV
# file, an API response, or another database.
SAMPLE_RECORDS = [
    {
        "restaurant_name": "Joe's Diner",
        "inspection_date": "2024-03-15",
        "score": 92,
        "violations": "Minor: food storage temperature",
        "inspector_id": "INS-1234",
    },
    {
        "restaurant_name": "Pizza Palace",
        "inspection_date": "2024-03-16",
        "score": 78,
        "violations": "Major: pest evidence; Minor: handwashing",
        "inspector_id": "INS-5678",
    },
    {
        # Empty name, invalid date, score out of range, bad inspector ID
        # This record has FOUR errors -- all will be reported
        "restaurant_name": "",
        "inspection_date": "not-a-date",
        "score": 150,
        "violations": "",
        "inspector_id": "BADGE-99",
    },
    {
        "restaurant_name": "Taco Town",
        "inspection_date": "2024-03-17",
        "score": 85,
        "violations": "",
        "inspector_id": "INS-9012",
    },
    {
        "restaurant_name": "Burger Barn",
        "inspection_date": "03/18/2024",  # Wrong date format
        "score": 65,
        "violations": "Critical: cross-contamination",
        "inspector_id": "INS-3456",
    },
    {
        "restaurant_name": "Sushi Spot",
        "inspection_date": "2024-03-19",
        "score": "ninety",  # Not a number
        "violations": "Minor: labeling",
        "inspector_id": "INS-7890",
    },
    {
        "restaurant_name": "Green Leaf Cafe",
        "inspection_date": "2024-03-20",
        "score": 95,
        "violations": "",
        "inspector_id": "INS-2345",
    },
    {
        "restaurant_name": "  ",  # Whitespace-only (should fail "required" check)
        "inspection_date": "2024-03-20",
        "score": 88,
        "violations": "",
        "inspector_id": "INS-6789",
    },
]


def main():
    validator = InspectionValidator()
    valid_records = validator.validate_batch(SAMPLE_RECORDS)

    print(f"\n{'=' * 50}")
    print("  Validation Results")
    print(f"{'=' * 50}")

    summary = validator.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")

    if validator.invalid_records:
        print(f"\n  Failed Records:")
        for error in validator.invalid_records:
            print(f"    Record {error.record_num}:")
            for field_error in error.errors:
                print(f"      - {field_error}")

    print(f"\n  Valid records ready for insertion:")
    for record in valid_records:
        print(f"    {record['restaurant_name']} (score: {record['score']})")


if __name__ == "__main__":
    main()
```

```bash
uv run python main.py
```

Expected output (approximately):

```
2024-03-20 10:15:00,000 [INFO] validator: Starting validation of 8 records
2024-03-20 10:15:00,001 [INFO] validator: Record 1 passed validation
2024-03-20 10:15:00,001 [INFO] validator: Record 2 passed validation
2024-03-20 10:15:00,001 [WARNING] validator: Record 3 failed validation: ...
2024-03-20 10:15:00,001 [INFO] validator: Record 4 passed validation
2024-03-20 10:15:00,001 [WARNING] validator: Record 5 failed validation: ...
2024-03-20 10:15:00,001 [WARNING] validator: Record 6 failed validation: ...
2024-03-20 10:15:00,002 [INFO] validator: Record 7 passed validation
2024-03-20 10:15:00,002 [WARNING] validator: Record 8 failed validation: ...
2024-03-20 10:15:00,002 [INFO] validator: Validation complete: 4 valid, 4 invalid out of 8 total

==================================================
  Validation Results
==================================================
  total_records: 8
  valid_count: 4
  invalid_count: 4
  pass_rate: 50.0%

  Failed Records:
    Record 3:
      - restaurant_name: field cannot be empty (got: '')
      - inspection_date: must be in YYYY-MM-DD format (got: 'not-a-date')
      - score: must be between 0 and 100 (got: 150)
      - inspector_id: must match format INS-XXXX (4 digits) (got: 'BADGE-99')
    Record 5:
      - inspection_date: must be in YYYY-MM-DD format (got: '03/18/2024')
    Record 6:
      - score: must be an integer (got: 'ninety')
    Record 8:
      - restaurant_name: field cannot be empty (got: '  ')

  Valid records ready for insertion:
    Joe's Diner (score: 92)
    Pizza Palace (score: 78)
    Taco Town (score: 85)
    Green Leaf Cafe (score: 95)
```

Also check the log file:

```bash
cat validation.log
```

---

## INDEPENDENT (15-20 min)

### Task: Build a ValidationReport Class

The health department needs analytics on validation failures to identify systemic data quality issues. Build a class that analyzes the validation results and produces a summary report.

**Requirements:**

1. **Create a file called `validation_report.py`** containing a `ValidationReport` class.

2. **The class should accept the validator instance** (the `InspectionValidator` object after it has processed records) in its constructor. This gives the report access to both valid and invalid record data.

3. **Implement a `generate()` method** that computes and prints the following:

   **Section A: Overview**
   - Total records processed
   - Number that passed validation
   - Number that failed validation
   - Pass rate as a percentage

   **Section B: Error Analysis**
   - Count of errors per field (e.g., "restaurant_name: 2 errors, inspection_date: 2 errors, score: 2 errors, inspector_id: 1 error")
   - The most common error field (which field fails most often?)
   - Total number of individual field errors across all records

   **Section C: Score Analysis** (from valid records only)
   - The restaurant with the lowest inspection score
   - The restaurant with the highest inspection score
   - The average score across all valid records

4. **Implement a `save_to_file(filepath)` method** that writes the same report content to a text file.

5. **Add a `__main__` block** that creates the validator, runs validation on the sample data, creates a ValidationReport, calls generate(), and saves to "report.txt".

**Expected behavior:**
- The overview numbers should match the validator's summary exactly.
- Error analysis should correctly count that Record 3 contributed 4 field errors (one per field), while Records 5, 6, and 8 contributed 1 each -- totaling 7 field errors across 4 invalid records.
- The "most common error field" could be determined by iterating through the invalid records and counting which field names appear in the errors.
- Score analysis should only consider the 4 valid records, not the invalid ones.

**Hints:**
- The validator's `invalid_records` list contains `RecordValidationError` objects. Each has an `errors` attribute that is a list of `ValidationError` objects. Each `ValidationError` has a `.field` attribute telling you which field failed.
- To count occurrences of each field name, consider using a dictionary where keys are field names and values are counts.
- For finding min/max scores from valid records, remember that `validator.valid_records` is a list of dictionaries with a "score" key.

---

## REVIEW CHECKLIST

When the student shares their code, verify:

- [ ] ValidationReport class accepts the validator instance in `__init__`
- [ ] `generate()` method prints all three sections (Overview, Error Analysis, Score Analysis)
- [ ] Error-per-field counting correctly iterates through `invalid_records` → `errors` → `field`
- [ ] Most common error field is correctly identified
- [ ] Total field error count is correct (7 for the sample data)
- [ ] Score analysis uses only valid records
- [ ] Min/max/average scores are computed correctly
- [ ] `save_to_file()` method writes to a text file
- [ ] File writing uses a context manager
- [ ] Script runs end-to-end without errors

---

## QUIZ (10 min)

Answer all 15 questions.

### Questions

**1. (Multiple Choice)** What is the output of this code?

```python
try:
    x = int("abc")
except ValueError:
    print("A")
except Exception:
    print("B")
```

A) `A`
B) `B`
C) `A` then `B`
D) An unhandled exception

**2. (Short Answer)** Why should you catch specific exceptions (like `ValueError`) instead of bare `except:` or `except Exception:`?

**3. (Multiple Choice)** What logging level should you use for "a record failed validation but the pipeline continues"?

A) DEBUG
B) INFO
C) WARNING
D) ERROR

**4. (Spot the Bug)**

```python
try:
    value = int(user_input)
    if value < 0:
        raise ValueError("Negative numbers not allowed")
except ValueError as e:
    print(f"Error: {e}")
    value = 0
print(f"Using value: {value}")
```

The developer wants negative numbers to be rejected entirely. What's wrong?

**5. (What Does This Code Output?)**

```python
import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("test")

logger.debug("msg1")
logger.info("msg2")
logger.warning("msg3")
logger.error("msg4")
```

A) All four messages are printed
B) Only msg3 and msg4 are printed
C) Only msg4 is printed
D) Nothing is printed

**6. (Multiple Choice)** What is the difference between `try/except` and `if/else` for validation?

A) They are interchangeable; use whichever you prefer
B) `try/except` is for unexpected runtime errors; `if/else` is for expected conditions you can check proactively
C) `if/else` is faster so you should always use it instead of `try/except`
D) `try/except` only works with built-in exceptions

**7. (Short Answer)** What does `super().__init__(message)` do in a custom exception class? What happens if you omit it?

**8. (What Does This Code Output?)**

```python
errors = []
for item in ["10", "abc", "20", "", "30"]:
    try:
        errors.append(int(item))
    except ValueError:
        errors.append(None)
print(errors)
```

A) `[10, 20, 30]`
B) `[10, None, 20, None, 30]`
C) `[10, "abc", 20, "", 30]`
D) An error on "abc"

**9. (Multiple Choice)** In the "collect-then-report" pattern, when is an exception raised to the caller?

A) On the first validation error
B) After all fields in a record are validated
C) After all records are validated
D) It depends on the implementation -- the pattern is about WHEN you report, not whether you raise

**10. (Spot the Bug)**

```python
import logging

logger = logging.getLogger(__name__)

def process_record(record):
    try:
        validate(record)
        insert_to_db(record)
    except Exception:
        logger.error("Something went wrong")
```

Name two problems with this error handling.

**11. (Multiple Choice)** What does `re.compile(r"^INS-\d{4}$")` match?

A) Any string containing "INS-" followed by digits
B) Only strings that are exactly "INS-" followed by exactly 4 digits
C) Strings starting with "INS-" followed by 4 or more digits
D) The literal string `^INS-\d{4}$`

**12. (What Does This Code Output?)**

```python
class CustomError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

try:
    raise CustomError(404, "Not found")
except CustomError as e:
    print(e.code, e.message)
```

A) `404 Not found`
B) `[404] Not found`
C) `CustomError: [404] Not found`
D) An error because custom exceptions can't have extra attributes

**13. (Short Answer)** Explain the difference between `logging.WARNING` and `logging.ERROR`. Give an example of when you'd use each in a data pipeline.

**14. (Multiple Choice)** What does `finally` do in a `try/except/finally` block?

A) Runs only if no exception occurred
B) Runs only if an exception occurred
C) Runs regardless of whether an exception occurred
D) Catches any exceptions not caught by `except`

**15. (Spot the Bug)**

```python
def validate_and_insert(records):
    conn = get_connection()
    cursor = conn.cursor()

    for record in records:
        try:
            cleaned = validate(record)
            cursor.execute("INSERT INTO inspections VALUES (%s, %s)", cleaned)
        except ValidationError:
            continue

    conn.commit()
    cursor.close()
    conn.close()
```

There are two problems with this code. What are they?

---

### Answer Key

**1.** A) `A`. Python matches exceptions top-to-bottom. `ValueError` is caught by the first `except ValueError` block. The `except Exception` block is never reached because `ValueError` is a subclass of `Exception`, and the more specific handler comes first.

**2.** Bare `except:` catches ALL exceptions, including `KeyboardInterrupt` (Ctrl+C), `SystemExit`, and programming bugs like `TypeError` or `NameError`. This masks real bugs -- your code silently swallows errors that indicate broken logic. Catching specific exceptions means only expected, recoverable errors are handled; genuine bugs propagate naturally so you can find and fix them.

**3.** C) WARNING. The record failed, but the pipeline continues processing. WARNING means "something unexpected happened but the system can continue." ERROR would mean "the system cannot perform its function." A single bad record in a batch of thousands is a warning, not an error.

**4.** When the input is negative, `raise ValueError(...)` is caught by the `except ValueError` block immediately below, which sets `value = 0` and continues. The developer intended to reject negatives, but the code silently replaces them with 0. Fix: either handle the negative case in a separate `if` block before the `try`, or use a different exception class (like a custom `NegativeValueError`) that isn't caught by the `except ValueError`.

**5.** B) Only msg3 and msg4 are printed. The logging level is set to WARNING, which means only messages at WARNING level or above (WARNING, ERROR, CRITICAL) are output. DEBUG and INFO are suppressed.

**6.** B) `try/except` is for unexpected runtime errors; `if/else` is for expected conditions you can check proactively. Use `if/else` when you can test the condition beforehand (`if value >= 0`). Use `try/except` when the only way to know if something works is to try it (`int("abc")` -- you can't easily pre-check if an arbitrary string is a valid integer without essentially reimplementing `int()`). This is called "LBYL" (Look Before You Leap) vs "EAFP" (Easier to Ask Forgiveness than Permission).

**7.** `super().__init__(message)` calls the parent `Exception` class's constructor, which stores the message as the standard exception string. This is what Python displays in tracebacks and what `str(e)` returns. If you omit it, `str(e)` returns an empty string (or the default `Exception()` representation), so error messages in tracebacks won't show your custom message.

**8.** B) `[10, None, 20, None, 30]`. `int("abc")` and `int("")` both raise `ValueError`, which is caught and replaced with `None`. `int("10")`, `int("20")`, and `int("30")` succeed. The result is `[10, None, 20, None, 30]`.

**9.** D) It depends on the implementation. The "collect-then-report" pattern is about accumulating errors rather than stopping on the first one. Some implementations raise a batch exception after processing all records; others return the errors as data. The key principle is: validate everything first, report all failures together.

**10.** Two problems: (1) **The exception is silenced** -- `except Exception` catches everything (including bugs like `AttributeError` or `TypeError` in `validate()` or `insert_to_db()`), and the code just logs a generic message and continues. Bugs are hidden. (2) **The error message is useless** -- `"Something went wrong"` contains no information about WHAT went wrong, WHICH record caused it, or what the exception was. It should at least log `logger.error("Failed to process record %s: %s", record, e)` and include the exception.

**11.** B) Only strings that are exactly "INS-" followed by exactly 4 digits. `^` anchors to the start, `$` anchors to the end, and `\d{4}` matches exactly 4 digits. Without the anchors, it would match substrings within longer strings.

**12.** A) `404 Not found`. The `except CustomError as e` catches the exception and binds it to `e`. We then access `e.code` (404) and `e.message` ("Not found") directly. The `super().__init__()` formatted string is what `str(e)` would return, but we're printing the individual attributes.

**13.** `WARNING` means something unexpected happened but the system can continue operating. Example: "5 out of 1000 records had invalid dates and were skipped." `ERROR` means the system could not complete an operation. Example: "Database connection failed -- cannot insert any records." The difference is about impact: WARNINGs are degraded results, ERRORs are failures.

**14.** C) Runs regardless of whether an exception occurred. `finally` executes whether the `try` block succeeded, whether an exception was caught by `except`, or even if an unhandled exception is propagating. It's used for guaranteed cleanup (closing files, database connections, releasing locks).

**15.** Two problems: (1) **If `cursor.execute()` fails, the `except ValidationError` won't catch it** -- database errors raise `psycopg2.Error`, not `ValidationError`. A failed INSERT will crash the entire function, and `conn.close()` will never be called (connection leak). (2) **If any INSERT fails, the `conn.commit()` at the end commits a partial batch** -- some records inserted, some skipped due to validation, some potentially failed due to DB errors. The valid inserts that succeeded before the crash will be committed in an inconsistent state. Fix: wrap the entire batch in a transaction with rollback on DB errors, and use `try/finally` for connection cleanup.
