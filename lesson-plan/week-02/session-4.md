# Week 2, Session 4: Integration Testing with Test Databases
**Domain:** Library book lending
**Concepts:** Test database setup, transaction rollback for test isolation, conftest.py, fixture scopes (session/function), testing database operations
**Prerequisites:** pytest from Session 3, PostgreSQL running, psycopg2

---

## FOLLOW-ALONG

### Step 1: Project Setup

```bash
mkdir -p week-02/session-4
cd week-02/session-4
```

### Step 2: Build the Library Database Class

This is the application code we'll test. It manages books, patrons, and checkouts.

```python
# library_db.py
# A library book lending system backed by PostgreSQL.
# Every method runs real SQL -- this is what makes our tests "integration tests"
# rather than unit tests: they hit an actual database.

import psycopg2
from datetime import datetime, timedelta


class LibraryDB:
    """Manages library operations: books, patrons, checkouts."""

    MAX_CHECKOUTS = 3       # a patron can have at most 3 books checked out
    LOAN_PERIOD_DAYS = 14   # books are due 14 days after checkout
    LATE_FEE_PER_DAY = 0.25 # $0.25 per day overdue

    def __init__(self, conn):
        """
        Takes an existing database connection.
        We don't create the connection here because tests need to control it
        (e.g., wrap everything in a transaction they can roll back).
        """
        self.conn = conn

    def create_tables(self):
        """Create the schema. Idempotent (IF NOT EXISTS)."""
        with self.conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    book_id SERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    author VARCHAR(100) NOT NULL,
                    isbn VARCHAR(13) UNIQUE,
                    available BOOLEAN NOT NULL DEFAULT TRUE
                );
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS patrons (
                    patron_id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(150) UNIQUE NOT NULL
                );
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS checkouts (
                    checkout_id SERIAL PRIMARY KEY,
                    book_id INTEGER NOT NULL REFERENCES books(book_id),
                    patron_id INTEGER NOT NULL REFERENCES patrons(patron_id),
                    checked_out_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    due_date TIMESTAMP NOT NULL,
                    returned_at TIMESTAMP
                );
            ''')
        self.conn.commit()

    def add_book(self, title, author, isbn=None):
        """Add a book to the library. Returns the new book_id."""
        with self.conn.cursor() as cur:
            cur.execute(
                'INSERT INTO books (title, author, isbn) VALUES (%s, %s, %s) RETURNING book_id;',
                (title, author, isbn)
            )
            book_id = cur.fetchone()[0]
        self.conn.commit()
        return book_id

    def add_patron(self, name, email):
        """Register a new patron. Returns the new patron_id."""
        with self.conn.cursor() as cur:
            cur.execute(
                'INSERT INTO patrons (name, email) VALUES (%s, %s) RETURNING patron_id;',
                (name, email)
            )
            patron_id = cur.fetchone()[0]
        self.conn.commit()
        return patron_id

    def checkout_book(self, book_id, patron_id):
        """
        Check out a book to a patron.
        Raises ValueError if:
        - The book doesn't exist or is already checked out
        - The patron has reached the checkout limit
        Returns the checkout_id.
        """
        with self.conn.cursor() as cur:
            # Check book availability
            cur.execute('SELECT available FROM books WHERE book_id = %s;', (book_id,))
            row = cur.fetchone()
            if row is None:
                raise ValueError(f'Book {book_id} does not exist')
            if not row[0]:
                raise ValueError(f'Book {book_id} is already checked out')

            # Check patron's current checkout count
            cur.execute(
                '''SELECT COUNT(*) FROM checkouts
                   WHERE patron_id = %s AND returned_at IS NULL;''',
                (patron_id,)
            )
            current_count = cur.fetchone()[0]
            if current_count >= self.MAX_CHECKOUTS:
                raise ValueError(
                    f'Patron {patron_id} already has {current_count} books checked out (max {self.MAX_CHECKOUTS})'
                )

            # Create checkout record
            due_date = datetime.now() + timedelta(days=self.LOAN_PERIOD_DAYS)
            cur.execute(
                '''INSERT INTO checkouts (book_id, patron_id, due_date)
                   VALUES (%s, %s, %s) RETURNING checkout_id;''',
                (book_id, patron_id, due_date)
            )
            checkout_id = cur.fetchone()[0]

            # Mark book as unavailable
            cur.execute('UPDATE books SET available = FALSE WHERE book_id = %s;', (book_id,))

        self.conn.commit()
        return checkout_id

    def return_book(self, book_id):
        """
        Return a checked-out book.
        Sets returned_at timestamp and marks the book available again.
        Returns the late fee (0.00 if returned on time).
        """
        with self.conn.cursor() as cur:
            # Find the active checkout for this book
            cur.execute(
                '''SELECT checkout_id, due_date FROM checkouts
                   WHERE book_id = %s AND returned_at IS NULL;''',
                (book_id,)
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError(f'Book {book_id} is not checked out')

            checkout_id, due_date = row
            now = datetime.now()

            # Calculate late fee
            late_fee = 0.0
            if now > due_date:
                days_late = (now - due_date).days
                late_fee = round(days_late * self.LATE_FEE_PER_DAY, 2)

            # Mark as returned
            cur.execute(
                'UPDATE checkouts SET returned_at = %s WHERE checkout_id = %s;',
                (now, checkout_id)
            )

            # Mark book as available
            cur.execute('UPDATE books SET available = TRUE WHERE book_id = %s;', (book_id,))

        self.conn.commit()
        return late_fee

    def get_overdue(self):
        """
        Find all currently overdue books (checked out, not returned, past due date).
        Returns list of dicts with book title, patron name, due date, days overdue.
        """
        with self.conn.cursor() as cur:
            cur.execute('''
                SELECT b.title, p.name, c.due_date,
                       EXTRACT(DAY FROM NOW() - c.due_date)::INTEGER as days_overdue
                FROM checkouts c
                JOIN books b ON c.book_id = b.book_id
                JOIN patrons p ON c.patron_id = p.patron_id
                WHERE c.returned_at IS NULL AND c.due_date < NOW();
            ''')
            rows = cur.fetchall()

        return [
            {
                'title': row[0],
                'patron': row[1],
                'due_date': row[2],
                'days_overdue': row[3],
            }
            for row in rows
        ]

    def get_patron_checkouts(self, patron_id):
        """Get all currently checked-out books for a patron."""
        with self.conn.cursor() as cur:
            cur.execute('''
                SELECT b.book_id, b.title, b.author, c.checked_out_at, c.due_date
                FROM checkouts c
                JOIN books b ON c.book_id = b.book_id
                WHERE c.patron_id = %s AND c.returned_at IS NULL
                ORDER BY c.due_date;
            ''', (patron_id,))
            rows = cur.fetchall()

        return [
            {
                'book_id': row[0],
                'title': row[1],
                'author': row[2],
                'checked_out_at': row[3],
                'due_date': row[4],
            }
            for row in rows
        ]
```

Save this file. Don't run it yet -- it needs a database connection to be useful.

### Step 3: Set Up conftest.py With Fixture Scopes

```python
# conftest.py
# This is a special pytest file. Fixtures defined here are automatically
# available to ALL test files in the same directory (and subdirectories).
# You never need to import conftest.py -- pytest finds it by convention.

import pytest
import psycopg2

# ------------------------------------------------------------------
# SESSION-SCOPED FIXTURE: runs ONCE for the entire test session.
# Creates the test database (expensive operation, do it only once).
# ------------------------------------------------------------------
@pytest.fixture(scope='session')
def db_connection():
    """
    Create a connection to a TEST database.
    scope='session' means this fixture runs once and is shared across ALL tests.
    This avoids creating/dropping the database for every single test function.
    """
    # Connect to the default database to create our test database
    admin_conn = psycopg2.connect(
        host='localhost', port=5432,
        dbname='postgres', user='postgres', password='postgres'
    )
    admin_conn.autocommit = True  # CREATE DATABASE can't run inside a transaction
    admin_cur = admin_conn.cursor()

    # Drop and recreate the test database for a clean slate
    admin_cur.execute('DROP DATABASE IF EXISTS library_test;')
    admin_cur.execute('CREATE DATABASE library_test;')
    admin_cur.close()
    admin_conn.close()

    # Now connect to the test database
    conn = psycopg2.connect(
        host='localhost', port=5432,
        dbname='library_test', user='postgres', password='postgres'
    )

    yield conn  # <-- tests use this connection

    # TEARDOWN: after ALL tests are done, drop the test database
    conn.close()
    admin_conn = psycopg2.connect(
        host='localhost', port=5432,
        dbname='postgres', user='postgres', password='postgres'
    )
    admin_conn.autocommit = True
    admin_cur = admin_conn.cursor()
    admin_cur.execute('DROP DATABASE IF EXISTS library_test;')
    admin_cur.close()
    admin_conn.close()


# ------------------------------------------------------------------
# SESSION-SCOPED FIXTURE: create tables once.
# ------------------------------------------------------------------
@pytest.fixture(scope='session')
def tables(db_connection):
    """Create the schema once. Depends on db_connection (also session-scoped)."""
    from library_db import LibraryDB
    lib = LibraryDB(db_connection)
    lib.create_tables()
    return True  # just a signal that tables exist


# ------------------------------------------------------------------
# FUNCTION-SCOPED FIXTURE: runs before EACH test.
# This is the key to test isolation: clean the data between tests.
# ------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_tables(db_connection, tables):
    """
    Truncate all tables before each test.
    autouse=True means EVERY test gets this automatically -- you don't need
    to add it as a parameter.

    TRUNCATE is faster than DELETE because it doesn't scan rows.
    CASCADE handles foreign key dependencies.
    RESTART IDENTITY resets SERIAL counters to 1, making tests predictable.
    """
    with db_connection.cursor() as cur:
        cur.execute('''
            TRUNCATE TABLE checkouts, books, patrons
            RESTART IDENTITY CASCADE;
        ''')
    db_connection.commit()
    yield  # test runs here
    # No teardown needed -- the next test's setup will truncate again


# ------------------------------------------------------------------
# FUNCTION-SCOPED FIXTURE: fresh LibraryDB instance per test.
# ------------------------------------------------------------------
@pytest.fixture
def library(db_connection):
    """Provide a fresh LibraryDB instance for each test."""
    return LibraryDB(db_connection)
```

The key insight: `db_connection` and `tables` are session-scoped (created once, shared), while `clean_tables` and `library` are function-scoped (fresh per test). This gives you speed (don't recreate the database for each test) AND isolation (each test starts with empty tables).

### Step 4: Write the First Integration Tests

```python
# test_library.py

import pytest
from library_db import LibraryDB


class TestAddBook:
    """Group related tests in a class for organization (optional in pytest)."""

    def test_add_book_returns_id(self, library):
        """Adding a book should return a positive integer ID."""
        book_id = library.add_book('Dune', 'Frank Herbert', '9780441013593')
        assert isinstance(book_id, int)
        assert book_id > 0

    def test_add_book_is_available(self, library):
        """Newly added books should be available for checkout."""
        book_id = library.add_book('Dune', 'Frank Herbert')

        # Verify directly in the database
        with library.conn.cursor() as cur:
            cur.execute('SELECT available FROM books WHERE book_id = %s;', (book_id,))
            available = cur.fetchone()[0]

        assert available is True

    def test_add_duplicate_isbn_fails(self, library):
        """Two books with the same ISBN should be rejected (UNIQUE constraint)."""
        library.add_book('Dune', 'Frank Herbert', '9780441013593')

        # psycopg2 raises IntegrityError on UNIQUE violations
        import psycopg2
        with pytest.raises(psycopg2.IntegrityError):
            library.add_book('Different Book', 'Other Author', '9780441013593')

        # IMPORTANT: after a failed transaction, we need to rollback
        # before the connection can be used again
        library.conn.rollback()


class TestCheckout:

    def test_checkout_marks_unavailable(self, library):
        """After checkout, the book should no longer be available."""
        book_id = library.add_book('1984', 'George Orwell')
        patron_id = library.add_patron('Alice', 'alice@library.org')

        library.checkout_book(book_id, patron_id)

        # Check the book's availability directly
        with library.conn.cursor() as cur:
            cur.execute('SELECT available FROM books WHERE book_id = %s;', (book_id,))
            available = cur.fetchone()[0]

        assert available is False

    def test_checkout_unavailable_book_raises(self, library):
        """Checking out a book that's already checked out should fail."""
        book_id = library.add_book('1984', 'George Orwell')
        patron_a = library.add_patron('Alice', 'alice@library.org')
        patron_b = library.add_patron('Bob', 'bob@library.org')

        library.checkout_book(book_id, patron_a)

        with pytest.raises(ValueError, match='already checked out'):
            library.checkout_book(book_id, patron_b)

    def test_checkout_nonexistent_book_raises(self, library):
        """Checking out a book that doesn't exist should fail."""
        patron_id = library.add_patron('Alice', 'alice@library.org')

        with pytest.raises(ValueError, match='does not exist'):
            library.checkout_book(9999, patron_id)


class TestReturn:

    def test_return_makes_book_available(self, library):
        """Returning a book should mark it as available again."""
        book_id = library.add_book('Brave New World', 'Aldous Huxley')
        patron_id = library.add_patron('Carol', 'carol@library.org')
        library.checkout_book(book_id, patron_id)

        library.return_book(book_id)

        with library.conn.cursor() as cur:
            cur.execute('SELECT available FROM books WHERE book_id = %s;', (book_id,))
            available = cur.fetchone()[0]

        assert available is True

    def test_return_on_time_no_fee(self, library):
        """Returning a book before the due date should have zero late fee."""
        book_id = library.add_book('Fahrenheit 451', 'Ray Bradbury')
        patron_id = library.add_patron('Dave', 'dave@library.org')
        library.checkout_book(book_id, patron_id)

        # Return immediately -- definitely not late
        fee = library.return_book(book_id)
        assert fee == 0.0

    def test_return_not_checked_out_raises(self, library):
        """Returning a book that isn't checked out should fail."""
        book_id = library.add_book('The Hobbit', 'J.R.R. Tolkien')

        with pytest.raises(ValueError, match='not checked out'):
            library.return_book(book_id)
```

Run the tests:

```bash
pytest test_library.py -v
```

All 9 should pass. Notice how each test starts with a clean database (thanks to `clean_tables`), so tests can't interfere with each other.

### Step 5: Testing With Backdated Timestamps

Some things are hard to test because they depend on "now" -- like overdue detection. We handle this by inserting data with backdated timestamps directly via SQL.

```python
# Add to test_library.py

from datetime import datetime, timedelta


class TestOverdue:

    def test_overdue_detection(self, library):
        """Books checked out more than 14 days ago should appear as overdue."""
        book_id = library.add_book('Old Book', 'Ancient Author')
        patron_id = library.add_patron('Eve', 'eve@library.org')

        # Manually insert a checkout record with a past due date
        # This is a testing technique: bypass the application layer
        # to set up specific time-dependent scenarios
        past_due = datetime.now() - timedelta(days=20)
        checked_out_at = past_due - timedelta(days=14)  # checked out 34 days ago

        with library.conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO checkouts (book_id, patron_id, checked_out_at, due_date)
                   VALUES (%s, %s, %s, %s);''',
                (book_id, patron_id, checked_out_at, past_due)
            )
            cur.execute(
                'UPDATE books SET available = FALSE WHERE book_id = %s;',
                (book_id,)
            )
        library.conn.commit()

        overdue = library.get_overdue()

        assert len(overdue) == 1
        assert overdue[0]['title'] == 'Old Book'
        assert overdue[0]['patron'] == 'Eve'
        assert overdue[0]['days_overdue'] >= 20  # at least 20 days overdue

    def test_not_overdue_excluded(self, library):
        """Books checked out recently should NOT appear as overdue."""
        book_id = library.add_book('New Book', 'Modern Author')
        patron_id = library.add_patron('Frank', 'frank@library.org')

        # Check out normally -- due date is 14 days from now
        library.checkout_book(book_id, patron_id)

        overdue = library.get_overdue()
        assert len(overdue) == 0
```

Run: `pytest test_library.py -v`. The overdue tests should pass.

### Step 6: Transaction Rollback Pattern (Alternative Isolation Strategy)

The `clean_tables` approach works well but there's another pattern worth knowing: wrapping each test in a transaction and rolling it back after. Let's see both approaches:

```python
# rollback_demo.py
# This file demonstrates the rollback pattern -- NOT part of the main test suite.
# In production test suites, you'd choose ONE strategy, not both.

import pytest
import psycopg2
from library_db import LibraryDB


@pytest.fixture
def rollback_library():
    """
    Alternative isolation: wrap each test in a transaction, rollback after.
    Pro: faster than TRUNCATE (no DDL).
    Con: doesn't work if the code under test calls COMMIT (our LibraryDB does).
    """
    conn = psycopg2.connect(
        host='localhost', port=5432,
        dbname='library_test', user='postgres', password='postgres'
    )
    # Start a savepoint we can roll back to
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute('SAVEPOINT test_savepoint;')

    lib = LibraryDB(conn)
    yield lib

    # After the test, rollback to undo ALL changes
    cur.execute('ROLLBACK TO SAVEPOINT test_savepoint;')
    conn.close()
```

This file is for demonstration only. The key tradeoff: rollback is faster but breaks if the application code calls `conn.commit()` (which ours does). For our `LibraryDB`, the TRUNCATE approach in `conftest.py` is more reliable.

### Step 7: Run the Full Suite

```bash
pytest test_library.py -v --tb=short
```

You should see all 11 tests passing. The output shows the class grouping (TestAddBook, TestCheckout, TestReturn, TestOverdue).

---

## INDEPENDENT

### Your Task

Add 4 groups of tests to `test_library.py` covering checkout limits, overdue calculations, late fees, and a full workflow. You have 15-20 minutes. All tests must pass.

### Test Group 1: Checkout Limit (MAX_CHECKOUTS = 3)

Write tests that verify the 3-book checkout limit:

- A patron can check out exactly 3 books (the maximum).
- Attempting to check out a 4th book raises a `ValueError` with a message about the limit.
- After returning one of the 3 books, the patron can check out a new book (they're back under the limit).

You'll need to add multiple books and check them out sequentially to reach the limit.

### Test Group 2: Overdue Calculation

Write tests that verify overdue detection works correctly for multiple scenarios:

- A patron with 2 overdue books should have both appear in `get_overdue()`.
- A patron with 1 overdue book and 1 on-time book should only have the overdue one appear.
- A returned book should NOT appear in overdue results, even if it was overdue when returned.

Use the backdated timestamp technique from the follow-along to create overdue scenarios.

### Test Group 3: Late Fee Calculation

Write a test that verifies late fees are calculated correctly:

- Check out a book, backdate the due date to 10 days ago using a direct SQL UPDATE, then return it.
- The late fee should be 10 * $0.25 = $2.50.
- Verify the returned fee matches the expected amount.

Hint: After creating the checkout through `library.checkout_book()`, use a direct SQL UPDATE to change the `due_date` to a past date, then call `library.return_book()`.

### Test Group 4: Full Workflow Test

Write one test that exercises the complete lifecycle:

1. Add 2 books and 1 patron.
2. Check out both books to the patron.
3. Verify `get_patron_checkouts` returns 2 books.
4. Return book 1.
5. Verify `get_patron_checkouts` returns only book 2.
6. Verify book 1 is available again (query the database directly).
7. Return book 2.
8. Verify `get_patron_checkouts` returns an empty list.

This tests the integration between all methods: add, checkout, return, and query.

### Expected Results

- All new tests pass alongside the existing ones.
- `pytest test_library.py -v` should show at least 18 total tests (11 original + 7+ new).
- No test should depend on another test's data (each test starts with clean tables).

---

## REVIEW CHECKLIST

When the student shares their code, check for:

- [ ] Checkout limit tests: adds 3+ books, checks out 3 successfully, 4th raises ValueError
- [ ] Checkout limit tests: after returning one book, a new checkout succeeds
- [ ] Overdue tests: uses backdated timestamps (direct SQL or timedelta manipulation)
- [ ] Overdue tests: correctly checks that only overdue (not on-time) books appear
- [ ] Overdue tests: verifies returned books don't appear in overdue results
- [ ] Late fee test: backdates the due date and verifies the fee calculation
- [ ] Late fee test: checks the exact dollar amount ($2.50 for 10 days)
- [ ] Full workflow test: covers add → checkout → verify → return → verify → return → verify
- [ ] Full workflow test: checks both `get_patron_checkouts` results AND direct database queries
- [ ] All tests use the `library` fixture (don't create their own connections)
- [ ] All tests pass: `pytest test_library.py -v` shows green
- [ ] Tests are independent (no test relies on data from another test)

---

## QUIZ

Answer all 15 questions. You must score at least 8/10 on the 10 selected for grading.

**Q1 (Multiple Choice):** What is the main difference between a unit test and an integration test?
a) Unit tests are written by developers, integration tests by QA
b) Unit tests test isolated components; integration tests test components working together (e.g., code + database)
c) Unit tests run faster; integration tests require more CPU
d) Unit tests use `assert`; integration tests use `verify`

**Q2 (Short Answer):** Why do we create a separate test database (`library_test`) instead of running tests against the development database?

**Q3 (Multiple Choice):** What does `scope='session'` mean on a pytest fixture?
a) The fixture runs once per test function
b) The fixture runs once per test class
c) The fixture runs once for the entire test session (all tests)
d) The fixture runs once per test file

**Q4 (Spot the Bug):**
```python
@pytest.fixture
def db_connection():
    conn = psycopg2.connect(dbname='testdb')
    return conn

def test_insert(db_connection):
    cur = db_connection.cursor()
    cur.execute("INSERT INTO items VALUES (1, 'test');")
    db_connection.commit()

def test_count(db_connection):
    cur = db_connection.cursor()
    cur.execute("SELECT COUNT(*) FROM items;")
    assert cur.fetchone()[0] == 0
```
`test_count` fails with a count of 1 instead of 0. Why?

**Q5 (Multiple Choice):** What is `conftest.py` used for?
a) Configuring the Python interpreter
b) Defining fixtures and hooks shared across test files in the same directory
c) Storing test data and expected results
d) Logging test output to a file

**Q6 (What Does This Output?):**
```python
@pytest.fixture(scope='session')
def counter():
    return {'n': 0}

def test_one(counter):
    counter['n'] += 1
    assert counter['n'] == 1

def test_two(counter):
    counter['n'] += 1
    assert counter['n'] == 2
```
Do both tests pass? Why or why not?

**Q7 (Short Answer):** Explain the transaction rollback testing pattern in 2-3 sentences. Why might it not work with application code that calls `COMMIT`?

**Q8 (Multiple Choice):** What does `TRUNCATE TABLE books RESTART IDENTITY CASCADE` do?
a) Deletes all rows from `books`, resets auto-increment, and truncates tables that reference `books`
b) Drops the `books` table and recreates it
c) Removes the primary key constraint from `books`
d) Deletes only rows with no foreign key references

**Q9 (Spot the Bug):**
```python
@pytest.fixture(scope='session')
def library():
    conn = psycopg2.connect(dbname='library_test')
    lib = LibraryDB(conn)
    lib.create_tables()
    return lib

@pytest.fixture(autouse=True)
def clean(library):
    with library.conn.cursor() as cur:
        cur.execute('TRUNCATE TABLE checkouts, books, patrons RESTART IDENTITY CASCADE;')
    library.conn.commit()
```
This fixture setup has a scope mismatch problem. What is it?

**Q10 (Short Answer):** Why do we use `autouse=True` on the `clean_tables` fixture instead of adding it as a parameter to every test?

**Q11 (Multiple Choice):** After a `psycopg2.IntegrityError` is raised (e.g., from a UNIQUE violation), what must you do before using the connection again?
a) Close and reopen the connection
b) Call `conn.rollback()` to abort the failed transaction
c) Call `conn.commit()` to clear the error
d) Nothing -- the connection automatically recovers

**Q12 (What Does This Output?):**
```python
@pytest.fixture
def book(library):
    return library.add_book('Test Book', 'Test Author')

def test_book_exists(library, book):
    with library.conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM books;')
        count = cur.fetchone()[0]
    assert count == 1

def test_book_available(library, book):
    with library.conn.cursor() as cur:
        cur.execute('SELECT available FROM books WHERE book_id = %s;', (book,))
        available = cur.fetchone()[0]
    assert available is True
```
Assuming `clean_tables` runs before each test, do both tests pass?

**Q13 (Short Answer):** What's the advantage of testing `get_overdue()` with backdated timestamps instead of actually waiting 14+ days?

**Q14 (Multiple Choice):** Which fixture scope should you use for a database connection that needs to be shared across all tests?
a) `scope='function'`
b) `scope='class'`
c) `scope='module'`
d) `scope='session'`

**Q15 (Short Answer):** You have a `clean_tables` fixture (function-scoped, autouse) and a `db_connection` fixture (session-scoped). In what order do they run relative to each test, and why can a function-scoped fixture depend on a session-scoped one but not vice versa?

---

### ANSWER KEY

**Q1:** b) Unit tests test isolated components; integration tests test components working together (e.g., code + database)

**Q2:** Tests insert, modify, and delete data. Running against the development database would corrupt your development data (and other developers' data). A separate test database can be freely truncated, dropped, and recreated without risk.

**Q3:** c) The fixture runs once for the entire test session (all tests)

**Q4:** There's no test isolation. `test_insert` commits a row into the database, and `test_count` sees it because the data persists. The `db_connection` fixture is function-scoped (recreated per test) but the DATABASE still has the committed data. Fix: add a cleanup fixture that truncates tables before each test.

**Q5:** b) Defining fixtures and hooks shared across test files in the same directory

**Q6:** Both tests pass. The `counter` fixture is session-scoped, so the same dictionary is shared across both tests. `test_one` increments to 1, `test_two` increments to 2. (Note: this means the tests are order-dependent, which is generally bad practice.)

**Q7:** The rollback pattern wraps each test in a database transaction (or savepoint). After the test completes, you ROLLBACK, undoing all changes and returning the database to its pre-test state. It fails with application code that calls COMMIT because COMMIT ends the transaction -- the rollback can no longer undo the committed changes.

**Q8:** a) Deletes all rows from `books`, resets auto-increment counters, and cascades the truncation to tables with foreign keys referencing `books`

**Q9:** The `clean` fixture is function-scoped (default) but depends on `library` which is session-scoped. While this dependency direction is allowed (function can depend on session), the real problem is that `clean` truncates tables using the session-scoped `library` fixture, but `library` itself is session-scoped -- so `library.create_tables()` only runs once, while `clean` truncates every test. This actually works, but if the `library` fixture were function-scoped instead, it would fail because function-scoped fixtures can't depend on other function-scoped fixtures from `conftest.py` in the same way. The more subtle issue: since `library` is session-scoped, ALL tests share the same `LibraryDB` instance and the same connection, which means tests aren't truly isolated at the connection level.

**Q10:** `autouse=True` makes the fixture run automatically for every test without needing to declare it as a parameter. This prevents the mistake of forgetting to include the cleanup fixture in a test, which would leave stale data and cause tests to interfere with each other.

**Q11:** b) Call `conn.rollback()` to abort the failed transaction. PostgreSQL puts the connection in an error state after a failed statement, and all subsequent queries will fail until the transaction is rolled back.

**Q12:** Both tests pass. The `clean_tables` fixture (autouse) truncates tables before each test. Then the `book` fixture runs (it depends on `library`), creating a fresh book. `test_book_exists` sees count=1 because its own `book` fixture just inserted one. `test_book_available` also gets a fresh `book` fixture (function-scoped) after truncation, so it also sees its own single book.

**Q13:** Tests need to be fast and deterministic. Waiting 14 real days would make tests impossibly slow. Backdating timestamps gives you precise control over the time conditions and lets the test run in milliseconds.

**Q14:** d) `scope='session'` -- creating a database connection is expensive, so you create it once and share it.

**Q15:** Before each test: session-scoped `db_connection` is already running (created once at start). Function-scoped `clean_tables` runs, truncating data. Then the test runs. A function-scoped fixture can depend on session-scoped because the session fixture exists for the duration of every function. But a session-scoped fixture cannot depend on a function-scoped one because the session fixture outlives the function fixture -- the function fixture would be created/destroyed multiple times during the session fixture's single lifetime.
