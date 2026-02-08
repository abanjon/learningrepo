# Week 2, Session 2: Python Generators and Chunked Processing
**Domain:** Server access logs
**Concepts:** Generators, yield, memory efficiency, chunked reading, batch inserts
**Prerequisites:** Python classes from Week 1, PostgreSQL running, basic INSERT/SELECT

---

## FOLLOW-ALONG

### Step 1: Project Setup

```bash
mkdir -p week-02/session-2
cd week-02/session-2
```

### Step 2: Create a Simulated Log File

First, let's generate a large fake Apache access log. This script creates 100,000 lines -- enough to make memory differences visible.

```python
# generate_logs.py
# Creates a fake Apache access log file for processing.
# We generate a LOT of lines so we can see the memory difference
# between loading everything into a list vs streaming with a generator.

import random
from datetime import datetime, timedelta

PATHS = [
    '/api/users', '/api/products', '/api/orders',
    '/login', '/logout', '/dashboard',
    '/static/style.css', '/static/app.js',
    '/health', '/api/search',
]

STATUS_CODES = [200, 200, 200, 200, 200, 301, 304, 400, 403, 404, 404, 500]
# 200 appears 5 times to make it the most common -- realistic distribution

METHODS = ['GET', 'GET', 'GET', 'POST', 'PUT', 'DELETE']
# GET weighted heavily because most web traffic is reads

def generate_ip():
    """Random IP address. Reuses some IPs to simulate repeat visitors."""
    # 20 "known" IPs that appear frequently, plus random ones
    known_ips = [f'192.168.1.{i}' for i in range(1, 21)]
    if random.random() < 0.6:  # 60% of requests from known IPs
        return random.choice(known_ips)
    return f'{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}'

def generate_log_line(timestamp):
    """Produces one Apache Combined Log Format line."""
    ip = generate_ip()
    method = random.choice(METHODS)
    path = random.choice(PATHS)
    status = random.choice(STATUS_CODES)
    size = random.randint(200, 50000)
    # Apache log format: IP - - [timestamp] "METHOD /path HTTP/1.1" status size
    time_str = timestamp.strftime('%d/%b/%Y:%H:%M:%S +0000')
    return f'{ip} - - [{time_str}] "{method} {path} HTTP/1.1" {status} {size}'

def main():
    num_lines = 100_000
    start_time = datetime(2024, 1, 1, 0, 0, 0)

    with open('access.log', 'w') as f:
        for i in range(num_lines):
            # Each log entry is ~1-3 seconds after the previous one
            timestamp = start_time + timedelta(seconds=i * random.uniform(1, 3))
            f.write(generate_log_line(timestamp) + '\n')

    print(f'Generated {num_lines} log lines -> access.log')

if __name__ == '__main__':
    main()
```

Run it:

```bash
python generate_logs.py
```

Check the file size: `ls -lh access.log` -- should be ~8-10 MB. Now let's process it.

### Step 3: The WRONG Way -- Load Everything Into Memory

```python
# bad_approach.py
# This loads the entire file into a list in memory.
# Works fine for 100K lines, but imagine 100M lines -- your machine would run out of RAM.

import sys

def parse_log_line(line):
    """Parse one Apache log line into a dictionary."""
    parts = line.split()
    return {
        'ip': parts[0],
        'timestamp': parts[3].strip('['),   # remove leading [
        'method': parts[5].strip('"'),       # remove leading "
        'path': parts[6],
        'status': int(parts[8]),
        'size': int(parts[9]),
    }

def load_all_logs(filepath):
    """Read every line, parse it, store in a list. Returns the whole list."""
    results = []
    with open(filepath, 'r') as f:
        for line in f:
            results.append(parse_log_line(line.strip()))
    return results  # <-- entire dataset sits in memory at once

# Load everything
all_logs = load_all_logs('access.log')

# Show memory impact: sys.getsizeof only shows the list container size,
# not the dictionaries inside it. For a rough estimate we multiply.
list_size = sys.getsizeof(all_logs)
approx_total = list_size + len(all_logs) * sys.getsizeof(all_logs[0])
print(f'Loaded {len(all_logs)} entries')
print(f'List container: {list_size:,} bytes')
print(f'Approximate total: {approx_total:,} bytes ({approx_total / 1_048_576:.1f} MB)')
print(f'First entry: {all_logs[0]}')
```

Run it: `python bad_approach.py`. Note the memory usage.

### Step 4: The RIGHT Way -- Generators

```python
# generator_approach.py
# A generator yields one item at a time instead of building the whole list.
# The key insight: at any point, only ONE parsed log entry is in memory.

import sys

def parse_log_line(line):
    """Parse one Apache log line into a dictionary."""
    parts = line.split()
    return {
        'ip': parts[0],
        'timestamp': parts[3].strip('['),
        'method': parts[5].strip('"'),
        'path': parts[6],
        'status': int(parts[8]),
        'size': int(parts[9]),
    }

def stream_logs(filepath):
    """
    Generator function: uses 'yield' instead of building a list.
    Each call to next() reads and parses exactly one line, then pauses.
    The function remembers where it left off between calls.
    """
    with open(filepath, 'r') as f:
        for line in f:
            stripped = line.strip()
            if stripped:  # skip empty lines
                yield parse_log_line(stripped)
    # When the file is exhausted, the generator automatically raises StopIteration.
    # The for-loop in the caller handles this gracefully.

# stream_logs() returns a generator OBJECT -- it does NOT run the function body yet.
# The function body only executes when you iterate over the generator.
log_stream = stream_logs('access.log')

# Proof: the generator object is tiny regardless of file size
print(f'Generator object size: {sys.getsizeof(log_stream)} bytes')

# Process entries one at a time
count = 0
error_count = 0
for entry in log_stream:
    count += 1
    if entry['status'] >= 400:
        error_count += 1

print(f'Processed {count} entries')
print(f'Errors (4xx/5xx): {error_count}')
print(f'Error rate: {error_count / count * 100:.1f}%')
# Memory used: roughly the size of ONE dictionary at any time, not 100,000
```

Run it: `python generator_approach.py`. Compare the generator object size (~200 bytes) to the list approach (~dozens of MB). Same results, fraction of the memory.

### Step 5: Understanding yield Step-by-Step

```python
# yield_demo.py
# Let's slow things down and see exactly how yield works.

def count_up_to(n):
    """Generator that yields numbers 1 through n."""
    print(f'  [generator] Starting up')
    i = 1
    while i <= n:
        print(f'  [generator] About to yield {i}')
        yield i  # <-- execution PAUSES here and returns i to the caller
        # When next() is called again, execution RESUMES right here
        print(f'  [generator] Resumed after yielding {i}')
        i += 1
    print(f'  [generator] Done, no more values')

# Create the generator -- nothing inside the function runs yet
gen = count_up_to(3)
print(f'Generator created: {gen}')
print()

# Each call to next() runs the function until the next yield
print('Calling next() #1:')
val = next(gen)
print(f'Got: {val}\n')

print('Calling next() #2:')
val = next(gen)
print(f'Got: {val}\n')

print('Calling next() #3:')
val = next(gen)
print(f'Got: {val}\n')

print('Calling next() #4:')
try:
    val = next(gen)
except StopIteration:
    print('StopIteration raised -- generator is exhausted')
```

Run it and read the output carefully. Notice the interleaving: the generator runs, pauses at `yield`, hands control back to you, then resumes exactly where it left off. This is called "lazy evaluation."

### Step 6: Set Up the Database Table

```python
# setup_db.py
# Create a table to hold parsed log entries.

import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='postgres',  # adjust to your database name
    user='postgres',     # adjust to your credentials
    password='postgres'
)
conn.autocommit = True
cur = conn.cursor()

cur.execute('DROP TABLE IF EXISTS access_logs;')
cur.execute('''
    CREATE TABLE access_logs (
        log_id SERIAL PRIMARY KEY,
        ip_address VARCHAR(45) NOT NULL,
        timestamp VARCHAR(30) NOT NULL,
        method VARCHAR(10) NOT NULL,
        path VARCHAR(255) NOT NULL,
        status_code INTEGER NOT NULL,
        response_size INTEGER NOT NULL
    );
''')
print('Table access_logs created.')
cur.close()
conn.close()
```

Run it: `python setup_db.py`

### Step 7: Batch Inserts With a Generator and Chunking

```python
# batch_loader.py
# This is the real pattern: generator + chunked batch inserts.
# Instead of inserting 100,000 rows one-at-a-time (slow) or loading them all
# into memory at once (wasteful), we insert in chunks of 500.

import psycopg2
from psycopg2.extras import execute_values  # bulk insert helper
import time

def parse_log_line(line):
    """Parse one Apache log line into a tuple (matching our INSERT column order)."""
    parts = line.split()
    return (
        parts[0],                    # ip_address
        parts[3].strip('['),         # timestamp
        parts[5].strip('"'),         # method
        parts[6],                    # path
        int(parts[8]),               # status_code
        int(parts[9]),               # response_size
    )

def stream_logs(filepath):
    """Generator: yields parsed log tuples one at a time."""
    with open(filepath, 'r') as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                yield parse_log_line(stripped)

def chunked(iterable, size):
    """
    Generator that groups items from any iterable into chunks of `size`.
    This is the glue between single-item generators and batch operations.
    Works with ANY iterable, including other generators.
    """
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk    # yield the full chunk
            chunk = []     # start a new chunk
    if chunk:              # don't forget the last partial chunk
        yield chunk

def load_logs(filepath, chunk_size=500):
    """Load logs from file into database using generator + batch inserts."""
    conn = psycopg2.connect(
        host='localhost', port=5432,
        dbname='postgres', user='postgres', password='postgres'
    )
    cur = conn.cursor()

    insert_sql = '''
        INSERT INTO access_logs (ip_address, timestamp, method, path, status_code, response_size)
        VALUES %s
    '''

    total_inserted = 0
    start_time = time.time()

    # Chain: file -> stream_logs (yields tuples) -> chunked (yields lists of 500)
    for batch in chunked(stream_logs(filepath), chunk_size):
        # execute_values does a single INSERT with multiple value rows
        # Way faster than 500 individual INSERT statements
        execute_values(cur, insert_sql, batch)
        conn.commit()  # commit after each batch so we don't hold a huge transaction
        total_inserted += len(batch)

        # Progress indicator every 10,000 rows
        if total_inserted % 10_000 == 0:
            elapsed = time.time() - start_time
            rate = total_inserted / elapsed
            print(f'  Inserted {total_inserted:>7,} rows  ({rate:,.0f} rows/sec)')

    elapsed = time.time() - start_time
    print(f'\nDone: {total_inserted:,} rows in {elapsed:.1f}s ({total_inserted/elapsed:,.0f} rows/sec)')

    cur.close()
    conn.close()

if __name__ == '__main__':
    load_logs('access.log', chunk_size=500)
```

Run it: `python batch_loader.py`

The key architecture: `stream_logs` yields one tuple at a time → `chunked` collects them into batches of 500 → `execute_values` inserts 500 rows in one SQL statement → commit. At no point does the full 100K-row dataset exist in memory.

### Step 8: Verify the Load

```python
# verify.py
# Quick sanity check that the data loaded correctly.

import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='postgres', user='postgres', password='postgres'
)
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM access_logs;')
print(f'Total rows: {cur.fetchone()[0]:,}')

cur.execute('''
    SELECT status_code, COUNT(*) as cnt
    FROM access_logs
    GROUP BY status_code
    ORDER BY cnt DESC;
''')
print('\nStatus code distribution:')
for code, count in cur.fetchall():
    print(f'  {code}: {count:,}')

cur.execute('''
    SELECT ip_address, COUNT(*) as cnt
    FROM access_logs
    GROUP BY ip_address
    ORDER BY cnt DESC
    LIMIT 5;
''')
print('\nTop 5 IPs:')
for ip, count in cur.fetchall():
    print(f'  {ip}: {count:,}')

cur.close()
conn.close()
```

Run it: `python verify.py`. You should see 100,000 rows with a distribution skewed toward 200 status codes and the 192.168.1.x IPs.

### Step 9: Generator Expressions (One-Liner Generators)

```python
# generator_expressions.py
# Just like list comprehensions but with () instead of [].
# They produce generators, not lists -- so they're lazy and memory-efficient.

import sys

# List comprehension: builds the entire list in memory NOW
squares_list = [x ** 2 for x in range(1_000_000)]
print(f'List size: {sys.getsizeof(squares_list):,} bytes')

# Generator expression: builds nothing yet -- values computed on demand
squares_gen = (x ** 2 for x in range(1_000_000))
print(f'Generator size: {sys.getsizeof(squares_gen)} bytes')  # ~200 bytes regardless of range

# You can pass generator expressions directly to functions that accept iterables
total = sum(x ** 2 for x in range(1_000_000))  # no extra [] needed inside sum()
print(f'Sum of squares: {total:,}')

# GOTCHA: generators are single-use. Once exhausted, they're done.
gen = (x for x in range(5))
print(list(gen))  # [0, 1, 2, 3, 4]
print(list(gen))  # [] -- already exhausted!
```

Run it. Note the memory difference. The generator expression is useful for quick one-off transformations; `def` + `yield` generators are better when you need complex logic or reusability.

---

## INDEPENDENT

### Your Task

Build a `LogAnalyzer` class that uses generators to stream through the database results and compute analytics WITHOUT loading all rows into memory at once. You have 15-20 minutes.

### Requirements

Create a file called `log_analyzer.py` with a class `LogAnalyzer` that:

1. **Connects to the database** in its `__init__` method and stores the connection.

2. **Has a `stream_rows` method** that executes a SELECT query and yields rows one at a time using a server-side cursor. (Hint: psycopg2 supports named cursors -- when you give a cursor a name, PostgreSQL streams results instead of loading them all into client memory. Look up how to create a named cursor and set its `itersize` attribute.)

3. **Has a `requests_per_hour` method** that uses `stream_rows` to iterate through all log entries and returns a dictionary mapping each hour (as a string like `"2024-01-01 00"`) to the count of requests in that hour. You'll need to parse the timestamp field to extract the date and hour.

4. **Has a `top_ips` method** that takes a parameter `n` (default 10) and uses `stream_rows` to iterate through all log entries, counting occurrences of each IP address, then returns the top `n` as a list of (ip, count) tuples sorted by count descending.

5. **Has an `error_rate` method** that uses `stream_rows` to iterate through all log entries and returns a dictionary with keys `"total"`, `"errors"`, and `"rate"`. Errors are any status code >= 400. Rate is a float between 0 and 1.

6. **Has a `close` method** that closes the database connection.

### Expected Behavior

When run as a script, `log_analyzer.py` should:
- Create a LogAnalyzer instance
- Print the top 5 hours by request count
- Print the top 10 IPs by request count
- Print the error rate as a percentage
- Close the connection

The key constraint: `stream_rows` must use a generator (yield), not `fetchall()`. Your methods that call `stream_rows` should process rows one at a time, accumulating only the summary data (counters/dictionaries), never the raw rows.

### Validation

- Run `python log_analyzer.py` and verify the output makes sense (top IPs should be in the 192.168.1.x range, error rate should roughly match the distribution from verify.py).
- The `stream_rows` method should use `yield`, not return a list.
- Each analytics method should iterate through `self.stream_rows(...)`, not call `fetchall()`.

---

## REVIEW CHECKLIST

When the student shares their code, check for:

- [ ] `LogAnalyzer.__init__` establishes a database connection
- [ ] `stream_rows` uses a named cursor (psycopg2 server-side cursor) or at minimum uses `yield` to emit rows one at a time
- [ ] `stream_rows` is a generator function (uses `yield`, not `return list`)
- [ ] `requests_per_hour` correctly parses the timestamp string to extract date+hour
- [ ] `requests_per_hour` uses `stream_rows` and accumulates into a dict, not loading all rows into a list
- [ ] `top_ips` counts IPs in a dict, then sorts and slices to top N
- [ ] `top_ips` returns a list of tuples sorted by count descending
- [ ] `error_rate` correctly identifies 4xx and 5xx status codes as errors
- [ ] `error_rate` returns a dict with total, errors, and rate keys
- [ ] `close` method properly closes the database connection
- [ ] No use of `fetchall()` in the analytics methods (the whole point is streaming)

---

## QUIZ

Answer all 15 questions. You must score at least 8/10 on the 10 selected for grading.

**Q1 (Multiple Choice):** What does the `yield` keyword do in a Python function?
a) Returns a value and terminates the function permanently
b) Pauses the function, returns a value, and resumes on the next iteration
c) Creates a list of all yielded values at once
d) Raises a StopIteration exception

**Q2 (What Does This Output?):**
```python
def gen():
    yield 1
    yield 2
    yield 3

g = gen()
print(next(g))
print(next(g))
```

**Q3 (Short Answer):** Why is a generator more memory-efficient than a list when processing a 10GB file line by line?

**Q4 (Spot the Bug):**
```python
def read_lines(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
    for line in lines:
        yield line.strip()
```
This function claims to be a generator, but it defeats the purpose. What's wrong?

**Q5 (Multiple Choice):** What happens when you call a generator function?
a) It executes the entire function body and returns all yielded values
b) It returns a generator object without executing the function body
c) It executes until the first yield and pauses
d) It raises a TypeError

**Q6 (What Does This Output?):**
```python
gen = (x * 2 for x in range(4))
result = list(gen)
result2 = list(gen)
print(result)
print(result2)
```

**Q7 (Short Answer):** Explain why batch inserts (e.g., 500 rows at a time) are faster than inserting one row at a time, even though the total number of rows is the same.

**Q8 (Multiple Choice):** What is the difference between `[x**2 for x in range(10)]` and `(x**2 for x in range(10))`?
a) They produce identical results -- the syntax difference doesn't matter
b) The first creates a list in memory; the second creates a generator that computes values lazily
c) The first is valid Python; the second is a syntax error
d) The second creates a tuple

**Q9 (Spot the Bug):**
```python
def chunked(items, size):
    chunk = []
    for item in items:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
```
This function mostly works but has a subtle bug. What data can it lose?

**Q10 (What Does This Output?):**
```python
def countdown(n):
    while n > 0:
        yield n
        n -= 1

total = sum(countdown(5))
print(total)
```

**Q11 (Multiple Choice):** In psycopg2, what is the purpose of a named (server-side) cursor?
a) It allows you to execute multiple queries simultaneously
b) It streams results from the server in batches instead of loading all rows into client memory
c) It encrypts the query results for security
d) It caches query results for faster repeated access

**Q12 (Short Answer):** You have a generator that yields 1 million dictionaries. You need to use the data twice: once to count items and once to compute a sum. What problem will you hit, and how do you solve it?

**Q13 (What Does This Output?):**
```python
def letters():
    yield 'a'
    yield 'b'
    return 'c'

gen = letters()
print(list(gen))
```

**Q14 (Multiple Choice):** Which of these is TRUE about generators?
a) You can index into a generator with `gen[3]`
b) Generators can be iterated over multiple times
c) Generators implement the iterator protocol (`__iter__` and `__next__`)
d) Generators are always faster than lists for all operations

**Q15 (Short Answer):** Write ONE sentence explaining what the `chunked()` helper function does and why it's useful for database batch operations.

---

### ANSWER KEY

**Q1:** b) Pauses the function, returns a value, and resumes on the next iteration

**Q2:** Output:
```
1
2
```
`next(g)` advances the generator to the next `yield`, returning its value. The third yield (3) is never reached because we only call `next()` twice.

**Q3:** A list loads all lines into memory simultaneously (the entire 10GB), while a generator yields one line at a time -- only one line is ever in memory. The generator's memory footprint is constant regardless of file size.

**Q4:** `f.readlines()` reads the ENTIRE file into a list in memory before the loop even starts. The `yield` makes it technically a generator, but the memory damage is already done. Fix: iterate with `for line in f:` instead of calling `readlines()`.

**Q5:** b) It returns a generator object without executing the function body. The body only executes when you iterate (e.g., call `next()` or use a `for` loop).

**Q6:** Output:
```
[0, 2, 4, 6]
[]
```
Generator expressions are single-use. After `list(gen)` exhausts it, `list(gen)` on the same generator returns an empty list.

**Q7:** Each individual INSERT requires a round-trip to the database server: send query, wait for acknowledgment, repeat. With 100,000 rows, that's 100,000 round-trips. Batch inserts send 500 rows in a single statement/round-trip, reducing overhead to 200 round-trips. Network latency and transaction overhead dominate at small row counts.

**Q8:** b) The first creates a list in memory; the second creates a generator that computes values lazily

**Q9:** If the total number of items isn't evenly divisible by `size`, the last partial chunk is never yielded. For example, `chunked([1,2,3], 2)` yields `[1,2]` but loses `[3]`. Fix: add `if chunk: yield chunk` after the for loop.

**Q10:** Output: `15`. `sum()` consumes the generator: 5 + 4 + 3 + 2 + 1 = 15.

**Q11:** b) It streams results from the server in batches instead of loading all rows into client memory

**Q12:** Generators are single-use. After the first pass (counting), the generator is exhausted and the second pass (summing) will get no data. Solution: either (1) call the generator function again to create a new generator for the second pass, (2) collect into a list if memory allows, or (3) compute both metrics in a single pass.

**Q13:** Output: `['a', 'b']`. The `return 'c'` terminates the generator (equivalent to `StopIteration`), but the value `'c'` is NOT yielded -- `return` in a generator just stops iteration. The value is attached to the StopIteration exception but `list()` ignores it.

**Q14:** c) Generators implement the iterator protocol (`__iter__` and `__next__`). You cannot index generators (a), they're single-use (b), and lists are faster for random access (d).

**Q15:** `chunked()` collects items from any iterable into fixed-size groups (e.g., batches of 500), which lets you pair a single-item generator with bulk database operations that are most efficient when given many rows at once.
