# exceptions.py


class ValidationError(Exception):
    """Raised when a single field fails validation

    Custom exceptions let you be SPECIFIC about what went wrong.
    'except ValidationError' catches only our validation errors,
    while 'except Exception' catches everything (including bugs).
    """

    def __init__(self, field: str, value, message: str):
        # store structured data about the error, not just a string.
        self.field = field
        self.value = value
        self.message = message
        # call the parent class's __init__ to set the standard message
        super().__init__(f"{field}: {message} (got: {value!r})")


class RecordValidationError(Exception):
    """Raised when a record has one or more validation errors.

    We collect ALL field errors per record rather than failing on the first.
    This is the "error accumulation" pattern.
    """

    def __init__(self, record_num: int, errors: list[ValidationError]):
        self.record_num = record_num
        self.errors = errors
        error_msgs = "; ".join(str(e) for e in errors)
        super().__init__(f"Record {record_num}: {error_msgs}")
