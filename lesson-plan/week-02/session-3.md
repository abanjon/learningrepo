# Week 2, Session 3: pytest Fundamentals
**Domain:** E-commerce order processing
**Concepts:** pytest basics, test functions, assertions, fixtures, parametrize, tmp_path
**Prerequisites:** Python classes from Week 1, pip install pytest

---

## FOLLOW-ALONG

### Step 1: Project Setup

```bash
mkdir -p week-02/session-3
cd week-02/session-3
pip install pytest
```

### Step 2: Build the Code We'll Test

First, let's create the `OrderProcessor` class. This is NOT the testing part yet -- we need something to test.

```python
# order_processor.py
# E-commerce order processing logic.
# We'll write tests for every public method in this class.

from dataclasses import dataclass
from datetime import datetime


@dataclass
class OrderItem:
    """One line item in an order."""
    product_name: str
    unit_price: float
    quantity: int


class InsufficientStockError(Exception):
    """Raised when an order requests more stock than available."""
    pass


class InvalidOrderError(Exception):
    """Raised when an order fails validation."""
    pass


class OrderProcessor:
    """Processes e-commerce orders: validation, pricing, discounts."""

    # In a real system these would come from a database.
    # We use a class-level dict so tests can easily override it.
    STOCK = {
        'Widget': 100,
        'Gadget': 50,
        'Doohickey': 25,
        'Thingamajig': 0,  # out of stock
    }

    TAX_RATE = 0.08  # 8% sales tax

    def calculate_subtotal(self, items: list[OrderItem]) -> float:
        """Sum of (price * quantity) for all items, before tax/discounts."""
        return sum(item.unit_price * item.quantity for item in items)

    def apply_discount(self, subtotal: float, discount_percent: float) -> float:
        """
        Apply a percentage discount to the subtotal.
        discount_percent is 0-100 (not 0-1).
        Returns the discounted amount (always >= 0).
        Raises ValueError if discount is negative or > 100.
        """
        if discount_percent < 0:
            raise ValueError('Discount cannot be negative')
        if discount_percent > 100:
            raise ValueError('Discount cannot exceed 100%')
        discount_amount = subtotal * (discount_percent / 100)
        return round(subtotal - discount_amount, 2)

    def calculate_tax(self, amount: float) -> float:
        """Calculate tax on the given amount."""
        return round(amount * self.TAX_RATE, 2)

    def calculate_total(self, items: list[OrderItem], discount_percent: float = 0) -> dict:
        """
        Full price calculation: subtotal -> discount -> tax -> total.
        Returns a dict with all components for transparency.
        """
        subtotal = self.calculate_subtotal(items)
        after_discount = self.apply_discount(subtotal, discount_percent)
        tax = self.calculate_tax(after_discount)
        return {
            'subtotal': subtotal,
            'discount_percent': discount_percent,
            'after_discount': after_discount,
            'tax': tax,
            'total': round(after_discount + tax, 2),
        }

    def validate_order(self, items: list[OrderItem]) -> bool:
        """
        Check that an order is valid:
        - Must have at least one item
        - All quantities must be positive
        - All prices must be positive
        - All products must have sufficient stock
        Raises InvalidOrderError or InsufficientStockError on failure.
        Returns True if valid.
        """
        if not items:
            raise InvalidOrderError('Order must contain at least one item')

        for item in items:
            if item.quantity <= 0:
                raise InvalidOrderError(
                    f'Quantity must be positive, got {item.quantity} for {item.product_name}'
                )
            if item.unit_price <= 0:
                raise InvalidOrderError(
                    f'Price must be positive, got {item.unit_price} for {item.product_name}'
                )
            stock = self.STOCK.get(item.product_name, 0)
            if item.quantity > stock:
                raise InsufficientStockError(
                    f'Requested {item.quantity} of {item.product_name}, only {stock} in stock'
                )
        return True

    def generate_receipt(self, items: list[OrderItem], discount_percent: float = 0) -> str:
        """Generate a plain-text receipt string."""
        result = self.calculate_total(items, discount_percent)
        lines = ['=== ORDER RECEIPT ===']
        for item in items:
            line_total = item.unit_price * item.quantity
            lines.append(f'{item.product_name:20s} {item.quantity}x ${item.unit_price:.2f} = ${line_total:.2f}')
        lines.append(f'{"Subtotal":20s} ${result["subtotal"]:.2f}')
        if discount_percent > 0:
            lines.append(f'{"Discount":20s} -{discount_percent}%')
            lines.append(f'{"After discount":20s} ${result["after_discount"]:.2f}')
        lines.append(f'{"Tax (8%)":20s} ${result["tax"]:.2f}')
        lines.append(f'{"TOTAL":20s} ${result["total"]:.2f}')
        lines.append('=====================')
        return '\n'.join(lines)
```

Run `python -c "from order_processor import OrderProcessor; print('Import OK')"` to verify it loads.

### Step 3: Your First Test

```python
# test_order_processor.py
# pytest discovers files named test_*.py and functions named test_*.
# No classes needed, no boilerplate -- just functions with assert statements.

from order_processor import OrderProcessor, OrderItem


def test_calculate_subtotal_single_item():
    """Test subtotal with one item: 3 widgets at $10 each = $30."""
    # ARRANGE: set up the objects you need
    processor = OrderProcessor()
    items = [OrderItem('Widget', 10.00, 3)]

    # ACT: call the method under test
    result = processor.calculate_subtotal(items)

    # ASSERT: verify the result
    assert result == 30.00
    # pytest uses plain `assert` -- if the expression is False, the test fails.
    # No assertEqual, assertGreater, etc. needed. Just `assert`.


def test_calculate_subtotal_multiple_items():
    """Test subtotal with multiple items."""
    processor = OrderProcessor()
    items = [
        OrderItem('Widget', 10.00, 2),   # 20.00
        OrderItem('Gadget', 25.50, 1),   # 25.50
    ]

    result = processor.calculate_subtotal(items)

    assert result == 45.50
```

Run the tests:

```bash
pytest test_order_processor.py -v
```

The `-v` flag shows each test name and its result. You should see two green PASSED lines.

### Step 4: Testing Exceptions

```python
# Add these to test_order_processor.py

import pytest  # needed for pytest.raises


def test_apply_discount_negative_raises():
    """Negative discounts should be rejected."""
    processor = OrderProcessor()

    # pytest.raises is a context manager that EXPECTS the given exception.
    # If the exception is NOT raised, the test FAILS.
    with pytest.raises(ValueError, match='cannot be negative'):
        # The `match` parameter checks the exception message with a regex.
        # This ensures we're getting the RIGHT ValueError, not some unrelated one.
        processor.apply_discount(100.00, -10)


def test_apply_discount_over_100_raises():
    """Discounts over 100% should be rejected."""
    processor = OrderProcessor()

    with pytest.raises(ValueError, match='cannot exceed 100'):
        processor.apply_discount(100.00, 150)


def test_validate_empty_order_raises():
    """Empty orders should be rejected."""
    processor = OrderProcessor()

    with pytest.raises(Exception) as exc_info:
        # exc_info captures the exception so you can inspect it further
        processor.validate_order([])

    # Check the exception type and message
    assert 'at least one item' in str(exc_info.value)
```

Run again: `pytest test_order_processor.py -v`. Three new tests should pass.

### Step 5: Fixtures -- Reusable Setup

```python
# Add these to test_order_processor.py, near the top (after imports)

@pytest.fixture
def processor():
    """
    Fixture: creates an OrderProcessor instance.
    Any test that has `processor` as a parameter automatically gets this.
    Pytest sees the parameter name, finds a matching fixture, calls it,
    and injects the return value.
    """
    return OrderProcessor()


@pytest.fixture
def sample_items():
    """Fixture: a standard set of order items for reuse across tests."""
    return [
        OrderItem('Widget', 10.00, 2),
        OrderItem('Gadget', 25.50, 1),
    ]


# Now we can rewrite our tests to use fixtures (shorter, less repetition)
def test_subtotal_with_fixtures(processor, sample_items):
    """Same test as before, but processor and items come from fixtures."""
    # pytest injects `processor` and `sample_items` automatically
    result = processor.calculate_subtotal(sample_items)
    assert result == 45.50


def test_total_with_no_discount(processor, sample_items):
    """Full calculation: subtotal $45.50, no discount, 8% tax."""
    result = processor.calculate_total(sample_items)

    assert result['subtotal'] == 45.50
    assert result['after_discount'] == 45.50  # no discount applied
    assert result['tax'] == 3.64              # 45.50 * 0.08 = 3.64
    assert result['total'] == 49.14           # 45.50 + 3.64


def test_total_with_discount(processor, sample_items):
    """10% off $45.50 = $40.95, then 8% tax."""
    result = processor.calculate_total(sample_items, discount_percent=10)

    assert result['after_discount'] == 40.95
    assert result['tax'] == 3.28              # 40.95 * 0.08 = 3.276, rounds to 3.28
    assert result['total'] == 44.23
```

Run: `pytest test_order_processor.py -v`. The fixture tests should pass alongside the originals.

### Step 6: Parametrize -- Test Many Inputs Without Repeating Code

```python
# Add to test_order_processor.py

@pytest.mark.parametrize('discount_percent, expected_after_discount', [
    (0, 100.00),     # no discount
    (10, 90.00),     # 10% off
    (25, 75.00),     # 25% off
    (50, 50.00),     # half off
    (100, 0.00),     # free (edge case)
])
def test_apply_discount_various(processor, discount_percent, expected_after_discount):
    """
    Parametrize runs the same test function multiple times with different inputs.
    Each tuple in the list becomes one test case.
    This replaces writing 5 nearly identical test functions.
    """
    result = processor.apply_discount(100.00, discount_percent)
    assert result == expected_after_discount


@pytest.mark.parametrize('quantity, price, expected', [
    (1, 10.00, 10.00),
    (5, 3.99, 19.95),
    (100, 0.01, 1.00),     # penny items in bulk
])
def test_subtotal_parametrized(processor, quantity, price, expected):
    """Multiple quantity/price combinations."""
    items = [OrderItem('TestProduct', price, quantity)]
    result = processor.calculate_subtotal(items)
    assert result == expected
```

Run: `pytest test_order_processor.py -v`. You'll see each parametrized case listed as a separate test (e.g., `test_apply_discount_various[0-100.0]`).

### Step 7: tmp_path -- Testing File Output

```python
# Add to test_order_processor.py

def test_receipt_written_to_file(processor, sample_items, tmp_path):
    """
    tmp_path is a built-in pytest fixture that provides a temporary directory.
    The directory is unique per test and automatically cleaned up.
    Use it whenever your code reads/writes files.
    """
    # Generate a receipt
    receipt_text = processor.generate_receipt(sample_items, discount_percent=10)

    # Write it to a file in the temp directory
    receipt_file = tmp_path / 'receipt.txt'
    receipt_file.write_text(receipt_text)

    # Read it back and verify
    content = receipt_file.read_text()
    assert 'ORDER RECEIPT' in content
    assert 'Widget' in content
    assert 'Gadget' in content
    assert 'Discount' in content  # discount section should appear since we used 10%
    assert '$44.23' in content    # the total

    # Verify the file actually exists on disk
    assert receipt_file.exists()
    assert receipt_file.stat().st_size > 0


def test_receipt_no_discount_omits_discount_line(processor, sample_items, tmp_path):
    """When discount is 0%, the receipt should NOT show a discount line."""
    receipt_text = processor.generate_receipt(sample_items, discount_percent=0)

    receipt_file = tmp_path / 'receipt.txt'
    receipt_file.write_text(receipt_text)

    content = receipt_file.read_text()
    assert 'Discount' not in content  # no discount line when 0%
```

Run: `pytest test_order_processor.py -v`. Notice you never had to create or clean up temp directories -- `tmp_path` handles it.

### Step 8: See It All Together

Run the full suite with verbose output and a summary:

```bash
pytest test_order_processor.py -v --tb=short
```

`--tb=short` gives concise tracebacks for any failures. You should see ~15+ tests all passing. The key patterns to remember:

1. **Arrange-Act-Assert**: Set up, call, check.
2. **Fixtures** (`@pytest.fixture`): Shared setup, injected by name.
3. **Parametrize** (`@pytest.mark.parametrize`): Many inputs, one test function.
4. **Exception testing** (`pytest.raises`): Verify errors are raised correctly.
5. **Temp files** (`tmp_path`): Safe file I/O in tests.

---

## INDEPENDENT

### Your Task

Add 8 more test functions to `test_order_processor.py` that cover edge cases and error conditions. You have 15-20 minutes. All tests must pass.

### Required Tests

1. **Empty order validation:** Write a test that verifies `validate_order` raises `InvalidOrderError` when given an empty list. Use `pytest.raises` with a `match` parameter to check the error message.

2. **Negative quantity rejection:** Write a test that verifies `validate_order` raises `InvalidOrderError` when an item has a negative quantity (e.g., -1). Check that the error message mentions the product name.

3. **Discount over 100%:** Write a test that verifies `apply_discount` raises `ValueError` when the discount percentage is exactly 101. (Note: 100% is valid, 101% is not.)

4. **Out-of-stock item:** Write a test that verifies `validate_order` raises `InsufficientStockError` when ordering a product with zero stock (`Thingamajig` has 0 stock in the class). The error message should mention the stock quantity.

5. **Bulk order pricing:** Write a parametrized test that checks `calculate_subtotal` for at least 3 different large-quantity scenarios (e.g., 1000 items at $0.01, 1 item at $9999.99, 50 items at $49.99). Each should calculate the correct total.

6. **Zero-percent discount is a no-op:** Write a test that verifies applying a 0% discount returns the original subtotal unchanged. Use a specific subtotal value like $123.45.

7. **Tax calculation precision:** Write a test that checks `calculate_tax` on an amount that would produce a repeating decimal (e.g., $33.33 * 0.08 = $2.6664, which should round to $2.67). Verify the rounding is correct.

8. **Receipt contains all items:** Write a test using `tmp_path` that generates a receipt for an order with 3 different products. Write the receipt to a file, read it back, and assert that all 3 product names appear in the file content.

### Guidelines

- Use fixtures (`processor`, `sample_items`) where appropriate -- don't recreate the OrderProcessor in every test.
- Use `pytest.raises` with `match` for all exception tests.
- Use `@pytest.mark.parametrize` for the bulk order test.
- Every test must follow the Arrange-Act-Assert pattern.
- Run `pytest -v` after each test you write to catch failures immediately.

---

## REVIEW CHECKLIST

When the student shares their code, check for:

- [ ] All 8 required tests are present and have descriptive names
- [ ] Empty order test uses `pytest.raises(InvalidOrderError)` with `match`
- [ ] Negative quantity test uses a specific product and checks the error message mentions it
- [ ] Discount 101% test uses `pytest.raises(ValueError)` (not just any exception)
- [ ] Out-of-stock test uses `Thingamajig` (or another 0-stock product) and checks `InsufficientStockError`
- [ ] Bulk order test uses `@pytest.mark.parametrize` with at least 3 cases
- [ ] Zero-discount test asserts the result equals the original subtotal exactly
- [ ] Tax rounding test uses a value that produces more than 2 decimal places and verifies correct rounding
- [ ] Receipt test uses `tmp_path`, writes to a file, reads it back, and checks for all 3 product names
- [ ] All tests pass: `pytest test_order_processor.py -v` shows green across the board
- [ ] Tests follow Arrange-Act-Assert pattern (not jumbled)

---

## QUIZ

Answer all 15 questions. You must score at least 8/10 on the 10 selected for grading.

**Q1 (Multiple Choice):** How does pytest discover test functions?
a) You must register each test in a configuration file
b) It finds files matching `test_*.py` and functions matching `test_*`
c) It looks for classes that inherit from `unittest.TestCase`
d) It scans all `.py` files for functions with `assert` statements

**Q2 (What Does This Output?):**
```python
def test_math():
    assert 0.1 + 0.2 == 0.3
```
Does this test pass or fail? Why?

**Q3 (Short Answer):** What is the Arrange-Act-Assert pattern? Give a one-sentence description of each phase.

**Q4 (Spot the Bug):**
```python
@pytest.fixture
def processor():
    return OrderProcessor()

def test_something():
    p = processor()
    result = p.calculate_subtotal([])
    assert result == 0
```
What's wrong with how the fixture is used?

**Q5 (Multiple Choice):** What does `@pytest.mark.parametrize` do?
a) Runs the test function once with all parameters combined
b) Runs the test function multiple times, once for each set of parameters
c) Creates a new test file for each parameter set
d) Marks the test as optional

**Q6 (What Does This Output?):**
```python
@pytest.mark.parametrize('x, expected', [(2, 4), (3, 9), (4, 15)])
def test_square(x, expected):
    assert x ** 2 == expected
```
How many tests run, and which ones pass?

**Q7 (Short Answer):** What is the difference between a fixture with `scope="function"` (the default) and `scope="session"`?

**Q8 (Multiple Choice):** What does `pytest.raises(ValueError)` do?
a) Raises a ValueError
b) Catches any exception and checks if it's a ValueError
c) Asserts that the code block raises a ValueError; fails if it doesn't
d) Silently ignores ValueErrors

**Q9 (Spot the Bug):**
```python
def test_discount():
    processor = OrderProcessor()
    processor.apply_discount(100, 10)
    assert result == 90
```
Why does this test fail?

**Q10 (What Does This Output?):**
```python
@pytest.fixture
def data():
    print("SETUP")
    yield [1, 2, 3]
    print("TEARDOWN")

def test_first(data):
    data.append(4)
    assert len(data) == 4

def test_second(data):
    assert len(data) == 3
```
Do both tests pass? Why or why not?

**Q11 (Multiple Choice):** What does the `tmp_path` fixture provide?
a) A string containing a temporary file name
b) A `pathlib.Path` object pointing to a unique temporary directory
c) A file-like object for writing temporary data
d) A database connection for temporary storage

**Q12 (Short Answer):** You have a function that should raise `FileNotFoundError` when given a nonexistent path. Write the pytest assertion pattern you would use (describe in prose, not code).

**Q13 (Multiple Choice):** If you run `pytest -v --tb=short`, what does `--tb=short` control?
a) The test timeout duration
b) The amount of traceback detail shown for failing tests
c) The number of tests to run in parallel
d) The verbosity of passing test output

**Q14 (What Does This Output?):**
```python
@pytest.fixture
def counter():
    return {'count': 0}

def test_increment(counter):
    counter['count'] += 1
    assert counter['count'] == 1

def test_check(counter):
    assert counter['count'] == 0
```
Do both tests pass? Explain.

**Q15 (Short Answer):** Why should you use `match` parameter in `pytest.raises(SomeError, match='expected message')` instead of just `pytest.raises(SomeError)`?

---

### ANSWER KEY

**Q1:** b) It finds files matching `test_*.py` and functions matching `test_*`

**Q2:** The test FAILS. Due to floating-point imprecision, `0.1 + 0.2` equals `0.30000000000000004` in Python, not exactly `0.3`. Fix: use `pytest.approx(0.3)` or compare with a tolerance.

**Q3:** Arrange: Set up the test data and objects you need. Act: Call the method or function under test. Assert: Verify the result matches your expectation.

**Q4:** The fixture is called as `processor()` with parentheses, but fixtures are injected by pytest -- you use them by adding the fixture name as a function parameter, not by calling the fixture function directly. Fix: `def test_something(processor):` then use `processor` directly (no parentheses).

**Q5:** b) Runs the test function multiple times, once for each set of parameters

**Q6:** 3 tests run. The first two pass (2²=4, 3²=9) but the third fails (4²=16, not 15).

**Q7:** `scope="function"` (default) creates a new fixture instance for EVERY test function -- each test gets its own fresh object. `scope="session"` creates the fixture ONCE for the entire test session and reuses it across all tests. Session scope is useful for expensive setup like database connections.

**Q8:** c) Asserts that the code block raises a ValueError; fails if it doesn't

**Q9:** The return value of `apply_discount` is never captured. `result` is undefined -- it will raise `NameError`. Fix: `result = processor.apply_discount(100, 10)`.

**Q10:** Both tests pass. The `yield` fixture with default function scope creates a fresh `[1, 2, 3]` list for each test. `test_first` appends to its own copy; `test_second` gets a brand new list. SETUP and TEARDOWN print for each test.

**Q11:** b) A `pathlib.Path` object pointing to a unique temporary directory

**Q12:** Use `pytest.raises(FileNotFoundError)` as a context manager wrapping the function call. Inside the `with` block, call the function with a path that doesn't exist. If the function does NOT raise `FileNotFoundError`, pytest will fail the test.

**Q13:** b) The amount of traceback detail shown for failing tests

**Q14:** Both tests pass. Fixtures with default scope (`function`) run fresh for each test. `test_increment` gets its own `{'count': 0}` dict, increments it to 1. `test_check` gets a separate `{'count': 0}` dict, asserts it equals 0. The fixture is not shared between tests.

**Q15:** Without `match`, `pytest.raises(SomeError)` passes if ANY `SomeError` is raised, even if it's from a completely different code path or reason than what you intended to test. The `match` parameter checks the error message with a regex, confirming the RIGHT error was raised for the RIGHT reason. This prevents false-positive tests.
