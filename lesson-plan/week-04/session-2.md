# Week 4, Session 2: Indexes and Query Optimization
**Domain:** E-commerce product search
**Concepts:** B-tree indexes, EXPLAIN ANALYZE, sequential vs index scan, composite indexes, partial indexes, index-only scans, when NOT to index
**Prerequisites:** PostgreSQL running in Docker, Python with `pip install faker psycopg2-binary`

---

## FOLLOW-ALONG

### Step 1: Create the products table and generate 100K rows

We need a large enough dataset that the query planner actually considers indexes. On tiny tables, PostgreSQL always does a sequential scan because it's cheaper to just read the whole thing than to consult an index.

```sql
-- File: product_search/schema.sql

CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    price NUMERIC(10, 2) NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    description TEXT
);
```

```python
# File: product_search/generate_data.py

"""
Generate 100K realistic product rows using Faker.
We need volume to make indexes matter -- on <1000 rows, PostgreSQL
will always prefer a sequential scan because reading the whole table
from memory is faster than doing index lookups.
"""

import psycopg2
from faker import Faker
import random
import time

fake = Faker()

# --- Configuration: adjust these to match your Docker setup ---
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "postgres",
}

CATEGORIES = [
    "Electronics", "Books", "Clothing", "Home & Garden", "Sports",
    "Toys", "Automotive", "Health", "Food", "Music",
    "Office", "Pet Supplies", "Beauty", "Tools", "Software",
]

NUM_PRODUCTS = 100_000
BATCH_SIZE = 5000  # Insert in batches to avoid OOM on large inserts


def create_tables(conn):
    with conn.cursor() as cur:
        # Read and execute the schema file, or just run it inline
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                price NUMERIC(10, 2) NOT NULL,
                stock_quantity INTEGER NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                description TEXT
            );
        """)
        conn.commit()


def seed_categories(conn):
    with conn.cursor() as cur:
        for cat in CATEGORIES:
            cur.execute(
                "INSERT INTO categories (name) VALUES (%s) ON CONFLICT DO NOTHING",
                (cat,),
            )
        conn.commit()


def generate_products(conn):
    """Insert 100K products in batches. Batching matters for performance --
    doing 100K individual INSERT statements would take minutes instead of seconds."""
    start = time.time()
    with conn.cursor() as cur:
        for batch_start in range(0, NUM_PRODUCTS, BATCH_SIZE):
            rows = []
            for _ in range(BATCH_SIZE):
                rows.append((
                    fake.catch_phrase(),                        # name
                    random.randint(1, len(CATEGORIES)),         # category_id
                    round(random.uniform(0.99, 999.99), 2),    # price
                    random.randint(0, 500),                     # stock_quantity
                    random.random() > 0.1,                     # is_active (90% active)
                    fake.date_time_between(start_date="-3y"),   # created_at
                ))

            # executemany is simpler but slower than execute_values.
            # For 100K rows this is fine; for millions you'd use COPY.
            args_str = ",".join(
                cur.mogrify("(%s,%s,%s,%s,%s,%s)", row).decode()
                for row in rows
            )
            cur.execute(
                f"INSERT INTO products (name, category_id, price, stock_quantity, is_active, created_at) "
                f"VALUES {args_str}"
            )
            conn.commit()
            print(f"  Inserted {min(batch_start + BATCH_SIZE, NUM_PRODUCTS):,} / {NUM_PRODUCTS:,}")

    elapsed = time.time() - start
    print(f"Done. {NUM_PRODUCTS:,} products in {elapsed:.1f}s")


if __name__ == "__main__":
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        create_tables(conn)
        seed_categories(conn)
        generate_products(conn)
    finally:
        conn.close()
```

Run the script. It should take 20-60 seconds depending on your machine. Verify with `SELECT COUNT(*) FROM products;` → 100,000.

### Step 2: Baseline queries WITHOUT indexes (slow)

Let's establish how slow things are before we optimize.

```sql
-- File: product_search/slow_queries.sql

-- Query 1: Find active products in a price range
-- EXPLAIN ANALYZE tells us the ACTUAL execution plan and time, not just the estimate.
EXPLAIN ANALYZE
SELECT id, name, price
FROM products
WHERE is_active = true AND price BETWEEN 50 AND 100;

-- Query 2: Find products in a specific category ordered by price
EXPLAIN ANALYZE
SELECT p.id, p.name, p.price
FROM products p
JOIN categories c ON p.category_id = c.id
WHERE c.name = 'Electronics'
ORDER BY p.price ASC;

-- Query 3: Count products per category (only active ones)
EXPLAIN ANALYZE
SELECT c.name, COUNT(*) AS product_count
FROM products p
JOIN categories c ON p.category_id = c.id
WHERE p.is_active = true
GROUP BY c.name
ORDER BY product_count DESC;
```

Run each one and note the `Execution Time` at the bottom of the EXPLAIN output. Write these down -- we'll compare after adding indexes.

### Step 3: Reading EXPLAIN ANALYZE output

Let's break down what the output means:

```sql
-- Run this and look at the output carefully:
EXPLAIN ANALYZE
SELECT id, name, price
FROM products
WHERE price < 10.00;
```

Key things to look for in the output:
- **Seq Scan**: The database reads EVERY row in the table. This is O(n).
- **Index Scan**: The database uses an index to jump directly to matching rows. This is O(log n).
- **Bitmap Index Scan**: A hybrid -- the index identifies matching pages, then the database reads those pages. Good for medium selectivity.
- **cost=X..Y**: X is startup cost, Y is total cost. Lower is better.
- **actual time=X..Y**: Real wall-clock time in milliseconds. This is what matters.
- **rows=N**: How many rows the step produced.
- **Filter:** shows conditions applied AFTER reading data (not using an index).

### Step 4: Single-column index

```sql
-- File: product_search/indexes.sql

-- B-tree index on price. The B-tree is a balanced tree structure where
-- each node contains sorted keys. Looking up a value is O(log n) instead
-- of O(n) for a sequential scan. Think of it like a phone book -- you
-- don't read every page to find "Smith", you jump to the S section.
CREATE INDEX idx_products_price ON products (price);

-- Now re-run the price range query:
EXPLAIN ANALYZE
SELECT id, name, price
FROM products
WHERE price < 10.00;
```

Compare the execution time to before. You should see an `Index Scan` or `Bitmap Index Scan` instead of a `Seq Scan`, and the time should be significantly lower.

### Step 5: Composite index for multi-column WHERE

When a query filters on multiple columns, a single-column index only helps with one filter. The database still has to scan the results for the other condition. A composite index covers both.

```sql
-- Column order in a composite index MATTERS. The index is sorted by
-- the first column, then by the second column within each first-column value.
-- Think of it like sorting by last name, then first name.
-- Put the most selective (fewest matching rows) column first.
CREATE INDEX idx_products_active_price ON products (is_active, price);

-- Now the active + price range query can use a single index lookup:
EXPLAIN ANALYZE
SELECT id, name, price
FROM products
WHERE is_active = true AND price BETWEEN 50 AND 100;
```

Look for `Index Scan using idx_products_active_price` in the output. Both conditions are resolved by the index -- no post-filtering needed.

### Step 6: Partial index for active products

90% of our products are active. Most queries only care about active products. Why maintain an index over the 10% inactive ones?

```sql
-- A partial index only indexes rows matching the WHERE condition.
-- This means it's smaller (less storage, fits in memory better)
-- and faster to maintain during inserts/updates.
CREATE INDEX idx_products_active_only_price ON products (price)
    WHERE is_active = true;

-- Compare the size of the full vs partial index:
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
FROM pg_indexes
WHERE tablename = 'products'
ORDER BY indexname;
```

The partial index should be noticeably smaller.

### Step 7: Demonstrating when indexes HURT

Indexes aren't free. They slow down writes and use storage. Let's see this:

```sql
-- First, measure insert speed WITHOUT extra indexes.
-- Drop the indexes we created:
DROP INDEX IF EXISTS idx_products_price;
DROP INDEX IF EXISTS idx_products_active_price;
DROP INDEX IF EXISTS idx_products_active_only_price;

-- Time a batch insert:
EXPLAIN ANALYZE
INSERT INTO products (name, category_id, price, stock_quantity, is_active, created_at)
SELECT
    'Bulk Product ' || g,
    (g % 15) + 1,
    random() * 100,
    (random() * 100)::int,
    random() > 0.1,
    NOW() - (random() * interval '365 days')
FROM generate_series(1, 10000) AS g;

-- Note the execution time. Now recreate indexes:
CREATE INDEX idx_products_price ON products (price);
CREATE INDEX idx_products_active_price ON products (is_active, price);
CREATE INDEX idx_products_active_only_price ON products (price) WHERE is_active = true;
CREATE INDEX idx_products_category ON products (category_id);

-- Time the same batch insert again:
EXPLAIN ANALYZE
INSERT INTO products (name, category_id, price, stock_quantity, is_active, created_at)
SELECT
    'Bulk Product X' || g,
    (g % 15) + 1,
    random() * 100,
    (random() * 100)::int,
    random() > 0.1,
    NOW() - (random() * interval '365 days')
FROM generate_series(1, 10000) AS g;
```

The second insert (with indexes) should be measurably slower because PostgreSQL has to update every index for every new row.

### Step 8: Index-only scan

When an index contains ALL the columns a query needs, PostgreSQL can answer the query entirely from the index without touching the table at all.

```sql
-- This index covers both the WHERE clause (price) and the SELECT (price).
-- PostgreSQL can answer this query using ONLY the index.
EXPLAIN ANALYZE
SELECT price FROM products WHERE price < 10.00;

-- Look for "Index Only Scan" in the output.
-- If you see "Heap Fetches: N" where N > 0, it means the visibility map
-- wasn't up to date and PG had to check the table for some rows.
-- Run VACUUM first to fix this:
VACUUM products;

EXPLAIN ANALYZE
SELECT price FROM products WHERE price < 10.00;
-- Now Heap Fetches should be 0 or very low.
```

Run both and compare -- the VACUUM makes a real difference for index-only scans.

---

## INDEPENDENT

You have 15-20 minutes. Your goal: optimize 5 slow queries by adding appropriate indexes. For **each** query, you must:

1. Run `EXPLAIN ANALYZE` on the query as-is and note the execution time
2. Create one or more indexes to speed it up
3. Run `EXPLAIN ANALYZE` again and confirm execution time is under 50ms
4. Write a SQL comment explaining WHY your index helps (what type of scan does it enable?)

Save all your work in `product_search/optimization.sql`.

### Query A: Exact category lookup

```sql
SELECT p.id, p.name, p.price, p.stock_quantity
FROM products p
WHERE p.category_id = 7 AND p.is_active = true
ORDER BY p.price ASC
LIMIT 20;
```

Goal: Under 50ms. Think about which columns belong in the index and in what order.

### Query B: Text search on product name

```sql
SELECT id, name, price
FROM products
WHERE name ILIKE '%ergonomic%'
LIMIT 50;
```

Goal: Under 50ms. Note: B-tree indexes do NOT help with leading wildcards. Research what PostgreSQL extension and index type can handle this. (Hint: it involves `pg_trgm`.)

### Query C: Date range with aggregation

```sql
SELECT DATE_TRUNC('month', created_at) AS month,
       COUNT(*) AS products_added,
       ROUND(AVG(price), 2) AS avg_price
FROM products
WHERE created_at >= '2024-01-01'
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month;
```

Goal: Under 50ms. Think about what column the index needs and whether a partial index would help.

### Query D: Out-of-stock active products

```sql
SELECT id, name, category_id, price
FROM products
WHERE is_active = true AND stock_quantity = 0
ORDER BY created_at DESC;
```

Goal: Under 50ms. A partial index is particularly effective here -- think about what condition to put in the WHERE clause of the index.

### Query E: Top-priced product per category

```sql
SELECT DISTINCT ON (category_id)
       category_id, id, name, price
FROM products
WHERE is_active = true
ORDER BY category_id, price DESC;
```

Goal: Under 50ms. `DISTINCT ON` requires specific ordering -- think about how your index can match that ordering exactly.

---

## REVIEW CHECKLIST

When reviewing the student's independent work, check for:

- [ ] **Query A:** Composite index on `(category_id, is_active, price)` or `(is_active, category_id, price)` -- column order should match the query's filter and sort.
- [ ] **Query B:** Uses `pg_trgm` extension and a GIN or GiST index with `gin_trgm_ops`. Student enabled the extension with `CREATE EXTENSION IF NOT EXISTS pg_trgm`.
- [ ] **Query C:** Index on `created_at` (simple B-tree). Possibly partial index for the date range.
- [ ] **Query D:** Partial index on `(stock_quantity)` or `(created_at)` with `WHERE is_active = true AND stock_quantity = 0` or similar.
- [ ] **Query E:** Composite index on `(is_active, category_id, price DESC)` to match the DISTINCT ON ordering.
- [ ] Each query shows `EXPLAIN ANALYZE` output before and after.
- [ ] Each query achieves <50ms execution time.
- [ ] SQL comments explain WHY the index helps, not just what it is.

---

## QUIZ

Answer all 15 questions. The session quiz will use 10 of these; extras are reserved for retries.

---

**Q1 (Multiple Choice).** What data structure does a default PostgreSQL index use?

A) Hash table
B) B-tree
C) Skip list
D) Trie

---

**Q2 (Short Answer).** Explain what a "sequential scan" is and when PostgreSQL chooses it over an index scan.

---

**Q3 (Multiple Choice).** In a composite index on `(A, B, C)`, which of these queries can use the index efficiently?

A) `WHERE B = 5`
B) `WHERE A = 1 AND C = 3`
C) `WHERE A = 1 AND B = 2`
D) `WHERE C = 3 AND B = 2`

---

**Q4 (Spot the Bug).** A developer creates this index to speed up `SELECT * FROM orders WHERE status = 'shipped' ORDER BY created_at DESC LIMIT 10`:

```sql
CREATE INDEX idx_orders_status ON orders (status);
```

The query is still slow. What's wrong with this index, and what would be better?

---

**Q5 (Short Answer).** What is a partial index? Give one real-world scenario where it outperforms a full index.

---

**Q6 (What does this code output?).** You run `EXPLAIN ANALYZE` and see this line:

```
Index Scan using idx_price on products  (cost=0.42..8.44 rows=1 width=44) (actual time=0.031..0.033 rows=1 loops=1)
```

What does `rows=1` in the estimated part vs `rows=1` in the actual part tell you?

---

**Q7 (Multiple Choice).** Which statement about indexes is FALSE?

A) Indexes speed up SELECT queries
B) Indexes slow down INSERT/UPDATE/DELETE operations
C) Indexes consume additional disk space
D) Adding more indexes always improves overall database performance

---

**Q8 (Short Answer).** What is the difference between an Index Scan and an Index-Only Scan?

---

**Q9 (Multiple Choice).** You have a table with 100 rows. You add an index on a frequently-queried column. What will PostgreSQL most likely do?

A) Always use the index because it exists
B) Ignore the index and do a sequential scan because the table is small
C) Use the index only for the first query, then cache the results
D) Drop the index automatically if it's not used

---

**Q10 (Spot the Bug).** A developer writes:

```sql
CREATE INDEX idx_search ON products (name);

SELECT * FROM products WHERE name ILIKE '%wireless%';
```

They expect the index to speed up the query, but it doesn't. Why not?

---

**Q11 (Short Answer).** What is "index selectivity" and why does it matter?

---

**Q12 (Multiple Choice).** In which situation would a Bitmap Index Scan be preferred over a plain Index Scan?

A) When selecting a single row by primary key
B) When the query matches a moderate number of rows scattered across many pages
C) When the table has fewer than 100 rows
D) When doing an INSERT operation

---

**Q13 (What does this code output?).** You create these two indexes:

```sql
CREATE INDEX idx_a ON products (category_id, price);
CREATE INDEX idx_b ON products (price, category_id);
```

For the query `SELECT * FROM products WHERE category_id = 5 ORDER BY price ASC`, which index is more useful and why?

---

**Q14 (Short Answer).** Name two scenarios where you should NOT add an index.

---

**Q15 (Multiple Choice).** What does `VACUUM` do in relation to index-only scans?

A) Rebuilds all indexes from scratch
B) Removes dead tuples and updates the visibility map, enabling index-only scans
C) Converts sequential scans into index scans
D) Deletes unused indexes to free disk space

---

### ANSWER KEY

**Q1:** B -- PostgreSQL's default index type is B-tree. Hash indexes exist but must be explicitly requested.

**Q2:** A sequential scan reads every row in the table from start to finish. PostgreSQL chooses it when: the table is small (fitting in a few pages), the query selects a large percentage of rows (low selectivity), or no suitable index exists for the query's conditions.

**Q3:** C -- A composite index on (A, B, C) is usable when the query filters on a **leftmost prefix**: A alone, (A, B), or (A, B, C). `WHERE A = 1 AND B = 2` uses the (A, B) prefix. Query A skips A, so it can't use the index efficiently. Query B skips B, so only the A portion is used. Query D starts with C, skipping A entirely.

**Q4:** The index only covers `status`, so PostgreSQL can find shipped orders but then must sort all of them by `created_at`. With many shipped orders, this sort is expensive. A better index is `CREATE INDEX idx_orders_status_created ON orders (status, created_at DESC)` -- this covers both the filter and the sort, and the LIMIT can stop reading after 10 entries.

**Q5:** A partial index only indexes rows that match a WHERE condition (e.g., `CREATE INDEX idx ON orders (created_at) WHERE status = 'pending'`). It outperforms a full index when most queries only care about a subset of data -- the index is smaller, fits in memory better, and is cheaper to maintain. Real-world example: indexing only active users when 90% of queries filter for `is_active = true`.

**Q6:** The estimated `rows=1` is the planner's prediction of how many rows the step will return. The actual `rows=1` is how many rows it really returned. When these match, the planner's statistics are accurate. When they diverge significantly, you may need to `ANALYZE` the table to update statistics.

**Q7:** D -- Adding more indexes does NOT always improve performance. Each index adds write overhead (INSERT/UPDATE/DELETE must maintain every index), consumes disk space, and can confuse the query planner. Indexes should be added judiciously for specific query patterns.

**Q8:** An Index Scan reads the index to find row locations, then fetches the actual rows from the table (the "heap"). An Index-Only Scan reads only the index because the index contains all columns the query needs -- it never touches the table. Index-Only Scans require the visibility map to be up-to-date (via VACUUM).

**Q9:** B -- For a 100-row table, the entire table fits in one or two disk pages. A sequential scan reads them all in one pass, which is faster than the overhead of looking up each row through the index. The query planner's cost model knows this.

**Q10:** B-tree indexes support prefix matching (`LIKE 'wireless%'`) but NOT infix/suffix matching (`LIKE '%wireless%'`). The leading wildcard means PostgreSQL can't use the B-tree's sorted structure -- it would have to scan every index entry, which is no better than a sequential scan. To support this pattern, use a GIN index with `pg_trgm`: `CREATE INDEX idx_search ON products USING gin (name gin_trgm_ops)`.

**Q11:** Index selectivity measures how unique the indexed values are, expressed as the ratio of distinct values to total rows (closer to 1.0 = more selective). High selectivity means the index can narrow down results quickly. A boolean column (selectivity ≈ 0.5) is rarely worth indexing alone because any query matches ~50% of rows, making a sequential scan cheaper. A unique ID column (selectivity = 1.0) is ideal.

**Q12:** B -- A Bitmap Index Scan is used when the query matches a moderate number of rows spread across many disk pages. It first builds a bitmap of which pages contain matching rows, then reads those pages in sequential order (avoiding random I/O). A plain Index Scan is better for very few rows; a sequential scan is better for many rows.

**Q13:** `idx_a` (category_id, price) is more useful. It can look up `category_id = 5` using the first column, and the matching entries are already sorted by `price` within that category, so the `ORDER BY price ASC` is satisfied without an additional sort step. `idx_b` (price, category_id) sorts by price first, so it can't efficiently jump to category_id = 5 -- it would need to scan the entire index.

**Q14:** (Any two of:) 1) Small tables -- sequential scan is faster. 2) Columns with very low selectivity (like boolean flags) -- the index matches too many rows to be useful alone. 3) Write-heavy tables where inserts/updates vastly outnumber reads -- index maintenance overhead dominates. 4) Columns that are rarely or never used in WHERE, ORDER BY, or JOIN conditions.

**Q15:** B -- VACUUM removes dead tuples (from updates/deletes) and updates the visibility map, which tracks which pages contain only tuples visible to all transactions. When the visibility map is current, PostgreSQL can do index-only scans without checking the heap for tuple visibility.
