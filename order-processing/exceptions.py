# exceptions.py

class OrderError(Exception):
    """Base class for all order-related errors."""

    pass

class FieldValidationError(OrderError):
    """Raised when a specific field fails validation
    We store the field name and the bad value so the called can decide how to handle it (e.g., log it or show it to a user).
    """

    def __init__(self, field: str, value, message: str):
        self.field = field
        self.value = value
        self.message = message

        # super().__init__ ensures the error message is available to Python
        super().__init__(f"Invalid {field}: {message} (got: {value!r})")


class BatchValidationError(OrderError):
    """Raised when one or more records in a batch fail validation.

    This is our 'Error Accumulator'. It holds a dictionary of record indices and their associated errors.
    """

    def __init__(self, errors: dict[int, list[FieldValidationError]]):
        self.errors = errors

        count = sum(len(e) for e in errors.values())
        super().__init__(
            f"Batch failed with {count} errors across {len(errors)} records"
        )
