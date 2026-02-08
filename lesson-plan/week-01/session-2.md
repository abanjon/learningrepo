# Week 1, Session 2: Tables, Inserts, Basic Queries

**Domain:** Bookstore Inventory
**Concepts:** CREATE TABLE, INSERT, SELECT, WHERE, ORDER BY, LIMIT, data types, CSV loading
**Duration:** 45-60 minutes

---

## FOLLOW-ALONG (15-20 min)

### Step 1: Set Up the Database

We'll reuse the same PostgreSQL Docker container from Session 1, but create a new database for this project.

```bash
# Create a new database inside the existing container.
# -U student = connect as the 'student' user
# We use a separate database per project so data doesn't collide.
docker exec weather_db psql -U student -d postgres -c "CREATE DATABASE bookstore;"
```

Create a new project:

```bash
uv init bookstore-inventory
cd bookstore-inventory
uv add psycopg2-binary
```

### Step 2: Create the Books Table

Create `db.py`:

```python
# db.py
import psycopg2

def get_connection():
    """Return a connection to the bookstore database."""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="bookstore",
        user="student",
        password="learningpass"
    )
```

Create `create_tables.py`:

```python
# create_tables.py
from db import get_connection

def create_books_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            -- SERIAL gives us an auto-incrementing ID. We almost always want
            -- a synthetic primary key rather than using a natural key like ISBN,
            -- because natural keys can change (ISBNs get reassigned, formats change).
            book_id SERIAL PRIMARY KEY,

            -- NOT NULL means this column MUST have a value. A book without a
            -- title is nonsensical. Think of NOT NULL as a data quality guard
            -- at the database level -- it catches bugs your Python code misses.
            title VARCHAR(200) NOT NULL,
            author VARCHAR(100) NOT NULL,

            -- NUMERIC(8,2) stores up to 999,999.99. We use NUMERIC for money
            -- instead of FLOAT because FLOAT can't represent $19.99 exactly
            -- (try float(19.99) in Python -- it's 19.990000000000002).
            price NUMERIC(8, 2) NOT NULL,

            -- VARCHAR(50) for genre. We could normalize this into a separate
            -- genres table, but for a bookstore with a small set of genres,
            -- a simple string column is pragmatic.
            genre VARCHAR(50),

            -- DEFAULT 0 means "if no stock quantity is given, assume zero."
            -- CHECK constraints enforce business rules at the DB level.
            -- Stock can't be negative -- that's a physical impossibility.
            stock_quantity INTEGER DEFAULT 0 CHECK (stock_quantity >= 0),

            -- DATE stores just the date (no time). Perfect for "when was this
            -- book published?" since we don't care about the exact hour.
            published_date DATE
        );
    """)

    conn.commit()
    print("Table 'books' created.")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    create_books_table()
```

```bash
uv run python create_tables.py
```

### Step 3: Prepare a CSV of Books

Create `books.csv`:

```csv
title,author,price,genre,stock_quantity,published_date
The Great Gatsby,F. Scott Fitzgerald,12.99,Fiction,15,1925-04-10
To Kill a Mockingbird,Harper Lee,14.99,Fiction,22,1960-07-11
1984,George Orwell,11.99,Dystopian,18,1949-06-08
Dune,Frank Herbert,16.99,Science Fiction,10,1965-08-01
The Hobbit,J.R.R. Tolkien,13.99,Fantasy,25,1937-09-21
Neuromancer,William Gibson,14.99,Science Fiction,8,1984-07-01
Pride and Prejudice,Jane Austen,9.99,Fiction,30,1813-01-28
The Catcher in the Rye,J.D. Salinger,11.99,Fiction,12,1951-07-16
Brave New World,Aldous Huxley,12.99,Dystopian,14,1932-01-01
Foundation,Isaac Asimov,15.99,Science Fiction,9,1951-06-01
The Road,Cormac McCarthy,13.99,Fiction,7,2006-09-26
Sapiens,Yuval Noah Harari,18.99,Non-Fiction,20,2011-01-01
Thinking Fast and Slow,Daniel Kahneman,17.99,Non-Fiction,11,2011-10-25
Clean Code,Robert C. Martin,39.99,Technical,6,2008-08-01
Designing Data-Intensive Applications,Martin Kleppmann,45.99,Technical,4,2017-03-16
The Pragmatic Programmer,David Thomas,44.99,Technical,5,1999-10-20
Fahrenheit 451,Ray Bradbury,10.99,Dystopian,16,1953-10-19
The Left Hand of Darkness,Ursula K. Le Guin,14.99,Science Fiction,7,1969-03-01
Atomic Habits,James Clear,16.99,Non-Fiction,35,2018-10-16
The Name of the Wind,Patrick Rothfuss,15.99,Fantasy,13,2007-03-27
```

### Step 4: Load the CSV into PostgreSQL

Create `load_books.py`:

```python
# load_books.py
import csv
from db import get_connection

def load_books_from_csv(filepath: str):
    """Read a CSV file and insert each row into the books table.

    We use csv.DictReader because it maps each row to a dictionary using the
    header as keys. This means we write column names (row['title']) instead of
    index numbers (row[0]), which makes the code self-documenting and resilient
    to column reordering in the CSV.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Track how many rows we insert for feedback
    inserted = 0

    with open(filepath, "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            cursor.execute(
                """
                INSERT INTO books (title, author, price, genre, stock_quantity, published_date)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (
                    row["title"],
                    row["author"],
                    row["price"],        # psycopg2 handles str -> NUMERIC conversion
                    row["genre"],
                    row["stock_quantity"],  # psycopg2 handles str -> INTEGER conversion
                    row["published_date"],
                ),
            )
            inserted += 1

    # One commit at the end, not inside the loop. This makes the entire load
    # atomic: either ALL rows are inserted, or NONE are (if an error occurs).
    # This is crucial for data integrity -- you never want a half-loaded table.
    conn.commit()
    print(f"Loaded {inserted} books from {filepath}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    load_books_from_csv("books.csv")
```

```bash
uv run python load_books.py
# Expected: Loaded 20 books from books.csv
```

### Step 5: Write Queries

Create `queries.py`:

```python
# queries.py
from db import get_connection

def run_query(description: str, sql: str):
    """Helper to run a query and print results with a header.

    Extracting this into a function avoids repeating the connect/execute/print
    pattern for every query. DRY = Don't Repeat Yourself.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()

    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print(f"{'=' * 60}")
    for row in rows:
        print(row)
    print(f"({len(rows)} rows)")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    # Query 1: Filter by genre
    # WHERE clause filters rows BEFORE they reach the result set.
    # Think of it as a bouncer at the door -- only matching rows get in.
    run_query(
        "Science Fiction Books",
        """
        SELECT title, author, price
        FROM books
        WHERE genre = 'Science Fiction'
        ORDER BY title;
        """
    )

    # Query 2: Sort by price, most expensive first
    # DESC = descending (highest first). Default is ASC (ascending).
    # Without ORDER BY, SQL returns rows in an undefined order --
    # it might change between runs depending on the query plan.
    run_query(
        "Books by Price (Most Expensive First)",
        """
        SELECT title, price, genre
        FROM books
        ORDER BY price DESC;
        """
    )

    # Query 3: Find books over $15
    # Comparison operators in WHERE: =, !=, <, >, <=, >=
    # For NUMERIC columns, comparisons work exactly (no floating-point surprises).
    run_query(
        "Books Over $15",
        """
        SELECT title, author, price
        FROM books
        WHERE price > 15.00
        ORDER BY price DESC;
        """
    )

    # Query 4: Combine conditions with AND/OR
    # AND = both must be true. OR = either can be true.
    # Parentheses control precedence (just like in math).
    run_query(
        "Cheap Fiction (Fiction or Dystopian, under $13)",
        """
        SELECT title, genre, price
        FROM books
        WHERE (genre = 'Fiction' OR genre = 'Dystopian')
          AND price < 13.00
        ORDER BY price;
        """
    )

    # Query 5: LIMIT restricts the number of rows returned
    # Useful for "top N" queries or when you just want a sample.
    # ALWAYS pair LIMIT with ORDER BY -- without ORDER BY, which rows
    # you get is random/nondeterministic.
    run_query(
        "Top 5 Most Expensive Books",
        """
        SELECT title, author, price
        FROM books
        ORDER BY price DESC
        LIMIT 5;
        """
    )

    # Query 6: COUNT and basic aggregation
    # COUNT(*) counts all rows. COUNT(column) counts non-NULL values.
    # These are called aggregate functions -- they collapse many rows into one.
    run_query(
        "Book Count by Genre",
        """
        SELECT genre, COUNT(*) as book_count
        FROM books
        GROUP BY genre
        ORDER BY book_count DESC;
        """
    )
```

```bash
uv run python queries.py
```

---

## INDEPENDENT (15-20 min)

### Task: Add a Sales Table and Write Analytics Queries

You're the new data analyst at this bookstore. The owner wants to understand sales patterns. Your job: create a sales table, add some data, and answer business questions.

**Requirements:**

1. **Create a `sales` table** with:
   - A unique auto-incrementing primary key
   - A reference to the `books` table (foreign key on `book_id`)
   - A quantity sold (integer, must be at least 1)
   - A sale date
   - A total price column (the price at time of sale times quantity -- store this explicitly because book prices can change over time)

2. **Insert at least 12 sales records** spanning at least 5 different books. Make some books sell multiple times and vary the quantities. Make sure at least 3 books have ZERO sales (don't insert any sales for them).

3. **Write the following queries:**

   **Query A: Total Revenue by Genre**
   Show each genre and its total revenue from sales. Sort by revenue, highest first. (Hint: you'll need to join sales with books to get the genre.)

   **Query B: Best-Selling Book**
   Find the single book with the highest total quantity sold. Show the title and total quantity.

   **Query C: Books That Have Never Sold**
   List all books that have zero sales records. Show the title and stock quantity. (Hint: think about which type of JOIN shows you rows from one table that have NO match in another table. Alternatively, consider using a subquery with NOT IN.)

**Expected behavior:**
- Revenue by genre should show dollar amounts. If you sold 3 copies of a $12.99 book, that's $38.97 revenue from that sale.
- The "never sold" query should return exactly the books you didn't create sales for.
- If multiple books tie for best-selling, returning any one of them is fine (but think about how LIMIT interacts with ties).

---

## REVIEW CHECKLIST

When the student shares their code, verify:

- [ ] `sales` table has SERIAL PRIMARY KEY
- [ ] `book_id` has a FOREIGN KEY constraint referencing `books(book_id)`
- [ ] `quantity` has a CHECK constraint (>= 1) or at least is NOT NULL
- [ ] `total_price` is stored (not calculated on-the-fly from the books table price)
- [ ] At least 12 sales records inserted across at least 5 books
- [ ] Revenue query uses SUM() and JOIN with GROUP BY genre
- [ ] Best-selling query uses SUM(quantity) with GROUP BY and ORDER BY + LIMIT 1
- [ ] Never-sold query uses LEFT JOIN ... WHERE ... IS NULL or NOT IN subquery
- [ ] All queries produce correct results when run
- [ ] Parameterized queries used for inserts

---

## QUIZ (10 min)

Answer all 15 questions.

### Questions

**1. (Multiple Choice)** What does `CHECK (stock_quantity >= 0)` do?

A) Checks the value when you SELECT from the table
B) Rejects any INSERT or UPDATE that would set stock_quantity below 0
C) Sets stock_quantity to 0 if a negative value is provided
D) Logs a warning but allows the negative value

**2. (What Does This Code Output?)**

```sql
SELECT title, price FROM books WHERE genre = 'Horror' ORDER BY price;
```

Assume no books have genre 'Horror'.

A) An error because 'Horror' doesn't exist
B) NULL
C) An empty result set (0 rows)
D) All books regardless of genre

**3. (Multiple Choice)** What is the difference between `VARCHAR(100)` and `TEXT` in PostgreSQL?

A) VARCHAR is stored on disk, TEXT is stored in memory
B) VARCHAR enforces a maximum length, TEXT has no length limit
C) TEXT is deprecated; always use VARCHAR
D) VARCHAR is faster than TEXT for all queries

**4. (Spot the Bug)**

```sql
SELECT genre, COUNT(*) as book_count
FROM books
WHERE book_count > 3
GROUP BY genre;
```

What is wrong with this query?

**5. (Short Answer)** Why do we commit once at the end of loading all CSV rows, rather than committing after each row?

**6. (Multiple Choice)** What does `ORDER BY price DESC LIMIT 3` return?

A) The 3 cheapest items
B) The 3 most expensive items
C) 3 random items sorted by price
D) All items, but only showing the price column

**7. (What Does This Code Output?)**

```sql
SELECT COUNT(*) FROM books WHERE published_date IS NULL;
```

Assume all 20 books have a published_date value.

A) 20
B) 0
C) NULL
D) An error

**8. (Multiple Choice)** Which of these WHERE clauses correctly finds books priced between $10 and $20 inclusive?

A) `WHERE price BETWEEN 10 AND 20`
B) `WHERE price >= 10 AND price <= 20`
C) Both A and B are correct and equivalent
D) Neither A nor B is correct

**9. (Spot the Bug)**

```python
cursor.execute(
    "INSERT INTO books (title, author, price) VALUES (%s, %s, %s);",
    ("The Hobbit", "Tolkien")
)
```

What is wrong with this code?

**10. (Short Answer)** Explain the difference between `COUNT(*)` and `COUNT(genre)`. When would they return different results?

**11. (Multiple Choice)** What does `SERIAL` do in a column definition?

A) Creates a string column that auto-generates UUIDs
B) Creates an auto-incrementing integer column backed by a sequence
C) Creates a column that must contain unique strings
D) Creates a column that stores serialized Python objects

**12. (What Does This Code Output?)**

```sql
SELECT DISTINCT genre FROM books ORDER BY genre LIMIT 3;
```

Assume genres are: Dystopian, Fantasy, Fiction, Non-Fiction, Science Fiction, Technical.

A) Dystopian, Fantasy, Fiction
B) Fiction, Fiction, Fiction
C) Technical, Science Fiction, Non-Fiction
D) Depends on the database

**13. (Short Answer)** Why do we store `total_price` in the sales table instead of computing it from the books table's price column at query time?

**14. (Multiple Choice)** Which query finds books where the author's name contains "Tolkien"?

A) `SELECT * FROM books WHERE author = 'Tolkien';`
B) `SELECT * FROM books WHERE author LIKE '%Tolkien%';`
C) `SELECT * FROM books WHERE author CONTAINS 'Tolkien';`
D) `SELECT * FROM books WHERE author IN ('Tolkien');`

**15. (Spot the Bug)**

```sql
SELECT title, price
FROM books
ORDER BY price
LIMIT 5
WHERE genre = 'Fiction';
```

What is wrong with this query?

---

### Answer Key

**1.** B) Rejects any INSERT or UPDATE that would set stock_quantity below 0. CHECK constraints enforce data integrity rules at the database level.

**2.** C) An empty result set (0 rows). SQL doesn't error when a WHERE condition matches nothing -- it simply returns zero rows.

**3.** B) VARCHAR enforces a maximum length, TEXT has no length limit. In PostgreSQL specifically, they have identical performance -- the only difference is the length check. (This is PostgreSQL-specific; other databases may differ.)

**4.** You cannot use a column alias (`book_count`) in the WHERE clause. WHERE is evaluated BEFORE the GROUP BY and aggregation. To filter on aggregated results, use HAVING: `HAVING COUNT(*) > 3`.

**5.** Two reasons: (1) **Atomicity** -- committing once makes the entire load all-or-nothing. If row 15 fails, rows 1-14 are also rolled back, so you never have a partially-loaded table. (2) **Performance** -- each commit forces PostgreSQL to flush data to disk. Committing once is dramatically faster than committing 20 times.

**6.** B) The 3 most expensive items. DESC sorts highest-first, and LIMIT 3 takes the first 3 from that sorted result.

**7.** B) 0. `COUNT(*)` counts rows matching the WHERE condition. Since no rows have NULL published_date, the count is 0.

**8.** C) Both A and B are correct and equivalent. `BETWEEN` is inclusive on both ends and is syntactic sugar for `>= AND <=`.

**9.** The VALUES clause has 3 placeholders (`%s, %s, %s`) but the tuple only has 2 values (`"The Hobbit", "Tolkien"`). The number of `%s` placeholders must match the number of values in the tuple. This will raise a psycopg2 error at runtime.

**10.** `COUNT(*)` counts all rows, including those where some columns are NULL. `COUNT(genre)` counts only rows where the `genre` column is NOT NULL. They return different results when some rows have `genre = NULL`. For example, if 3 books have no genre set, `COUNT(*)` returns 20 but `COUNT(genre)` returns 17.

**11.** B) Creates an auto-incrementing integer column backed by a sequence. PostgreSQL creates a sequence object and sets the column's default to `nextval('sequence_name')`.

**12.** A) Dystopian, Fantasy, Fiction. DISTINCT removes duplicate genre values, ORDER BY genre sorts alphabetically (ascending by default), and LIMIT 3 takes the first three.

**13.** The price of a book can change over time (sales, markdowns, price increases). If we computed total_price from the current book price, historical sales records would show incorrect revenue. Storing total_price at the time of sale captures the actual amount paid -- this is a fundamental principle in data modeling called "preserving historical context."

**14.** B) `SELECT * FROM books WHERE author LIKE '%Tolkien%';`. LIKE with `%` wildcards performs pattern matching. `%` matches any sequence of characters. Option A requires an exact match. Option C uses a non-existent CONTAINS keyword. Option D checks for exact membership in a list.

**15.** The clauses are in the wrong order. SQL requires a specific clause order: `SELECT ... FROM ... WHERE ... GROUP BY ... HAVING ... ORDER BY ... LIMIT ...`. WHERE must come before ORDER BY and LIMIT. The corrected query is: `SELECT title, price FROM books WHERE genre = 'Fiction' ORDER BY price LIMIT 5;`.
