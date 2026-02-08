# Week 1, Session 1: Environment Setup

**Domain:** Weather Station Data
**Concepts:** Docker, PostgreSQL, uv, Python project structure, psycopg2
**Duration:** 45-60 minutes

---

## FOLLOW-ALONG (15-20 min)

### Step 1: Run PostgreSQL in Docker

First, pull and run a PostgreSQL container. We use Docker so every student has an identical database environment regardless of their OS -- no "works on my machine" problems.

```bash
# Pull the official PostgreSQL 16 image
# We pin a major version (16) so our SQL behavior is predictable across environments
docker pull postgres:16

# Run the container:
#   -d             = detached mode (runs in background so we keep our terminal)
#   --name         = human-readable name (easier than remembering container IDs)
#   -e POSTGRES_*  = environment variables that configure the DB on first run
#   -p 5432:5432   = map host port 5432 to container port 5432 (so psycopg2 can connect via localhost)
#   -v pgdata:/var/lib/postgresql/data = persist data in a named volume (survives container restarts)
docker run -d \
  --name weather_db \
  -e POSTGRES_USER=student \
  -e POSTGRES_PASSWORD=learningpass \
  -e POSTGRES_DB=weather \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16
```

Verify it's running:

```bash
# docker ps lists only RUNNING containers
# You should see "weather_db" with status "Up X seconds"
docker ps
```

Test that PostgreSQL is accepting connections:

```bash
# docker exec runs a command INSIDE a running container
# psql is PostgreSQL's built-in CLI client
# -U specifies the user, -c executes a single SQL command
docker exec weather_db psql -U student -d weather -c "SELECT version();"
```

### Step 2: Create a Python Project with uv

```bash
# uv is a fast Python package manager (replacement for pip + venv)
# 'uv init' creates a new project with pyproject.toml -- the modern standard
# for Python project metadata (replaces setup.py and requirements.txt)
uv init weather-station
cd weather-station

# Add psycopg2-binary: the PostgreSQL adapter for Python
# We use the -binary variant because it ships pre-compiled -- no need for
# system-level PostgreSQL dev headers. Fine for learning; production uses psycopg2.
uv add psycopg2-binary
```

Your project structure now looks like:

```
weather-station/
├── pyproject.toml       # Project metadata + dependencies (the modern standard)
├── .python-version      # Pins the Python version for reproducibility
└── .venv/               # Virtual environment (uv manages this automatically)
```

### Step 3: Connect to PostgreSQL from Python

Create `db_connection.py`:

```python
# db_connection.py
import psycopg2

def get_connection():
    """Create and return a database connection.

    We wrap this in a function (rather than a bare global connection) because:
    1. It's reusable -- any script can call get_connection()
    2. Each caller gets a FRESH connection (avoids stale connection bugs)
    3. Connection params are in one place (easy to change later)
    """
    return psycopg2.connect(
        host="localhost",      # Docker mapped the container's 5432 to our localhost
        port=5432,
        dbname="weather",
        user="student",
        password="learningpass"
    )


# Quick test: connect, run a query, close
if __name__ == "__main__":
    # __name__ == "__main__" means this block only runs when you execute
    # this file directly (python db_connection.py), NOT when you import it.
    # This is the standard Python pattern for "test this module."
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT current_database(), current_user;")
    db_name, db_user = cursor.fetchone()
    print(f"Connected to '{db_name}' as '{db_user}'")

    # Always close what you open. Unclosed connections leak memory
    # and can hit PostgreSQL's max_connections limit.
    cursor.close()
    conn.close()
```

Run it:

```bash
uv run python db_connection.py
# Expected output: Connected to 'weather' as 'student'
```

### Step 4: Create the weather_stations Table

Create `create_tables.py`:

```python
# create_tables.py
from db_connection import get_connection

def create_weather_stations_table():
    """Create the weather_stations table if it doesn't exist.

    We use IF NOT EXISTS so this script is idempotent -- you can run it
    multiple times without errors. This is a critical habit in data engineering
    because pipelines often re-run on failure.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weather_stations (
            -- SERIAL = auto-incrementing integer. PostgreSQL creates a sequence
            -- behind the scenes. PRIMARY KEY = unique + not null.
            station_id SERIAL PRIMARY KEY,

            -- VARCHAR(100) limits length to 100 chars. Use VARCHAR when you
            -- know the max length; use TEXT when you don't.
            station_name VARCHAR(100) NOT NULL,

            -- NUMERIC(9,6) stores up to 9 total digits with 6 after the decimal.
            -- Perfect for lat/long coordinates (e.g., 42.361145).
            -- We use NUMERIC instead of FLOAT because FLOAT has rounding errors
            -- (try 0.1 + 0.2 in Python -- you get 0.30000000000000004).
            latitude NUMERIC(9, 6) NOT NULL,
            longitude NUMERIC(9, 6) NOT NULL,

            -- TIMESTAMP WITH TIME ZONE stores the moment in time unambiguously.
            -- Without time zone, "2024-01-01 12:00" is meaningless -- noon WHERE?
            -- DEFAULT NOW() means if you don't provide a value, PostgreSQL fills
            -- it in with the current time.
            installed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

            -- BOOLEAN defaults to true. A station might be decommissioned later.
            is_active BOOLEAN DEFAULT TRUE
        );
    """)

    # conn.commit() is REQUIRED. PostgreSQL uses transactions by default --
    # nothing is saved until you commit. Forget this and your table vanishes
    # when the connection closes.
    conn.commit()
    print("Table 'weather_stations' created successfully.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    create_weather_stations_table()
```

Run it:

```bash
uv run python create_tables.py
```

### Step 5: Insert and Query Data

Create `seed_and_query.py`:

```python
# seed_and_query.py
from db_connection import get_connection

def seed_stations():
    """Insert sample weather stations.

    We use parameterized queries (%s placeholders) instead of f-strings
    because f-strings are vulnerable to SQL injection. If station_name
    contained "'; DROP TABLE weather_stations; --", an f-string would
    execute that destructive SQL. Parameterized queries escape it safely.
    """
    conn = get_connection()
    cursor = conn.cursor()

    stations = [
        ("Boston Harbor", 42.3611, -71.0489),
        ("Mount Washington", 44.2706, -71.3033),
        ("Logan Airport", 42.3656, -71.0096),
        ("Blue Hill Observatory", 42.2131, -71.1136),
    ]

    # executemany runs the same INSERT for each tuple in the list.
    # More efficient than looping with execute() because psycopg2 can
    # batch them into fewer network round-trips.
    cursor.executemany(
        """
        INSERT INTO weather_stations (station_name, latitude, longitude)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING;
        """,
        stations
    )

    conn.commit()
    print(f"Inserted {cursor.rowcount} stations.")

    cursor.close()
    conn.close()


def query_stations():
    """Query and display all weather stations."""
    conn = get_connection()
    cursor = conn.cursor()

    # ORDER BY station_name gives predictable output.
    # In SQL, rows have no inherent order -- without ORDER BY,
    # the database returns them in whatever order is fastest.
    cursor.execute("""
        SELECT station_id, station_name, latitude, longitude, is_active
        FROM weather_stations
        ORDER BY station_name;
    """)

    # fetchall() loads ALL rows into memory at once. Fine for small datasets.
    # For millions of rows, use fetchmany(batch_size) or iterate the cursor
    # to avoid running out of RAM.
    rows = cursor.fetchall()

    print(f"\n{'ID':<4} {'Station':<25} {'Lat':<12} {'Long':<12} {'Active'}")
    print("-" * 65)
    for row in rows:
        station_id, name, lat, lon, active = row
        print(f"{station_id:<4} {name:<25} {lat:<12} {lon:<12} {active}")

    print(f"\nTotal stations: {len(rows)}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    seed_stations()
    query_stations()
```

Run it:

```bash
uv run python seed_and_query.py
```

Expected output:

```
Inserted 4 stations.

ID   Station                   Lat          Long         Active
-----------------------------------------------------------------
1    Blue Hill Observatory     42.213100    -71.113600   True
2    Boston Harbor             42.361100    -71.048900   True
3    Logan Airport             42.365600    -71.009600   True
4    Mount Washington          44.270600    -71.303300   True

Total stations: 4
```

---

## INDEPENDENT (15-20 min)

### Task: Add a Readings Table and Query Average Temperature

Your goal is to extend the weather station system with temperature/humidity readings and compute basic statistics.

**Requirements:**

1. **Create a `readings` table** with the following columns:
   - A unique auto-incrementing ID as the primary key
   - A `station_id` column that references the `weather_stations` table as a foreign key
   - A `temperature` column that stores decimal values (e.g., 72.5)
   - A `humidity` column that stores decimal values representing percentage (e.g., 65.2)
   - A `recorded_at` column that stores the timestamp of the reading, defaulting to the current time

2. **Write a script called `insert_readings.py`** that:
   - Inserts at least 5 sample readings spread across at least 2 different stations
   - Uses parameterized queries (not f-strings)
   - Commits the transaction
   - Prints confirmation of how many rows were inserted

3. **In the same script (or a separate one), write a query** that calculates and prints:
   - The average temperature across ALL readings
   - The average temperature PER STATION (showing the station name, not just the ID)

**Expected behavior:**
- If you insert readings with temperatures like 72.5, 68.3, 75.1, 69.8, 71.2, the overall average should be around 71.4.
- The per-station averages should group correctly -- a station with one reading of 72.5 should show exactly 72.5 as its average.

**Hints:**
- Look at how we defined the `weather_stations` table for the syntax of SERIAL, NUMERIC, and TIMESTAMP WITH TIME ZONE.
- A foreign key is declared with `REFERENCES table_name(column_name)`.
- To get per-station averages with station names, you'll need to join the two tables and use GROUP BY.

---

## REVIEW CHECKLIST

When the student shares their code, verify:

- [ ] `readings` table has a proper SERIAL PRIMARY KEY
- [ ] `station_id` column has a FOREIGN KEY constraint referencing `weather_stations(station_id)`
- [ ] `temperature` and `humidity` use NUMERIC or FLOAT (not INTEGER)
- [ ] `recorded_at` has a sensible default (NOW() or CURRENT_TIMESTAMP)
- [ ] Parameterized queries are used (no f-strings or string concatenation in SQL)
- [ ] Transaction is committed after inserts
- [ ] Average temperature query uses AVG() aggregate function
- [ ] Per-station query uses JOIN and GROUP BY correctly
- [ ] Connections and cursors are properly closed
- [ ] Script runs without errors and produces correct output

---

## QUIZ (10 min)

Answer all 15 questions. Grading: 8/10 required to pass (only first 10 count toward pass/fail; questions 11-15 are extras for retries).

### Questions

**1. (Multiple Choice)** What does the `-d` flag do in `docker run -d`?

A) Deletes the container after it stops
B) Runs the container in debug mode
C) Runs the container in detached (background) mode
D) Downloads the image before running

**2. (Multiple Choice)** What happens if you run `docker run` with `--name weather_db` and a container with that name already exists?

A) It creates a second container with the same name
B) It throws an error
C) It restarts the existing container
D) It silently replaces the old container

**3. (Short Answer)** Why do we use `-p 5432:5432` in the `docker run` command? What would happen if we omitted it?

**4. (What Does This Code Output?)**

```python
import psycopg2
conn = psycopg2.connect(host="localhost", port=5432, dbname="weather", user="student", password="learningpass")
cursor = conn.cursor()
cursor.execute("SELECT 1 + 1;")
print(cursor.fetchone())
```

A) `2`
B) `(2,)`
C) `[2]`
D) `{'result': 2}`

**5. (Multiple Choice)** Which SQL data type is BEST for storing latitude/longitude coordinates?

A) INTEGER
B) FLOAT
C) NUMERIC(9,6)
D) VARCHAR(20)

**6. (Spot the Bug)**

```python
conn = get_connection()
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE test_table (
        id SERIAL PRIMARY KEY,
        name VARCHAR(50) NOT NULL
    );
""")
cursor.close()
conn.close()
print("Table created!")
```

What is wrong with this code?

**7. (Multiple Choice)** What does `ON CONFLICT DO NOTHING` do in an INSERT statement?

A) Raises an error if there's a conflict
B) Silently skips the insert if it would violate a constraint
C) Deletes the conflicting row and inserts the new one
D) Updates the conflicting row with the new values

**8. (Short Answer)** Why should you use parameterized queries (`%s` placeholders) instead of Python f-strings when building SQL queries?

**9. (What Does This Code Output?)**

```python
cursor.execute("SELECT * FROM weather_stations ORDER BY station_name LIMIT 2;")
rows = cursor.fetchall()
print(len(rows))
```

Assume the table has 4 rows.

A) 4
B) 2
C) 1
D) 0

**10. (Multiple Choice)** What does `IF NOT EXISTS` do in `CREATE TABLE IF NOT EXISTS weather_stations (...)`?

A) Checks if any rows exist in the table
B) Creates the table only if no table with that name exists
C) Drops the table first, then creates it
D) Creates the table and ignores any duplicate column names

**11. (Short Answer)** What is the purpose of a `pyproject.toml` file in a Python project? Name two things it stores.

**12. (What Does This Code Output?)**

```python
cursor.execute("SELECT station_name FROM weather_stations WHERE is_active = FALSE;")
rows = cursor.fetchall()
print(rows)
```

Assume all 4 stations have `is_active = TRUE`.

A) `None`
B) `[]`
C) `[()]`
D) An error

**13. (Multiple Choice)** What does `cursor.fetchone()` return when the query result has no rows?

A) An empty tuple `()`
B) An empty list `[]`
C) `None`
D) Raises a `StopIteration` exception

**14. (Spot the Bug)**

```python
station_name = "O'Hare Airport"
cursor.execute(f"INSERT INTO weather_stations (station_name, latitude, longitude) VALUES ('{station_name}', 41.97, -87.90);")
```

What is wrong with this code? (There are two problems.)

**15. (Short Answer)** What is the difference between `docker run` and `docker exec`? When would you use each?

---

### Answer Key

**1.** C) Runs the container in detached (background) mode.

**2.** B) It throws an error. Docker requires unique container names. You'd need to `docker rm weather_db` first (or use `docker start weather_db` to restart a stopped container).

**3.** The `-p 5432:5432` maps port 5432 on the host machine to port 5432 inside the container. Without it, PostgreSQL would be running inside the container but nothing outside (like our Python script) could connect to it -- the port would be unreachable from localhost.

**4.** B) `(2,)`. `fetchone()` returns a tuple representing one row. Even a single-column result is a tuple.

**5.** C) NUMERIC(9,6). NUMERIC provides exact decimal storage (no floating-point rounding errors). FLOAT would introduce subtle precision issues. INTEGER can't store decimals. VARCHAR stores text, not numbers.

**6.** Missing `conn.commit()` before closing. PostgreSQL uses transactions by default -- without a commit, the CREATE TABLE is rolled back when the connection closes, and the table won't exist.

**7.** B) Silently skips the insert if it would violate a constraint (like a unique or primary key constraint).

**8.** Parameterized queries prevent SQL injection attacks. If a value contains SQL metacharacters (like single quotes or semicolons), the database driver escapes them safely. With f-strings, malicious input like `'; DROP TABLE weather_stations; --` would be executed as SQL.

**9.** B) 2. `LIMIT 2` restricts the result to at most 2 rows, regardless of how many rows match the query.

**10.** B) Creates the table only if no table with that name exists. If the table already exists, the statement does nothing (no error). This makes the script idempotent.

**11.** `pyproject.toml` is the modern standard for Python project configuration. It stores: (1) project metadata (name, version, description), and (2) dependencies (packages your project needs). It can also store tool configurations for things like linters, formatters, and test runners.

**12.** B) `[]`. `fetchall()` returns an empty list when no rows match the WHERE condition. It does not return `None`.

**13.** C) `None`. When there are no more rows, `fetchone()` returns `None` (not an empty tuple or an exception).

**14.** Two problems: (1) **SQL injection vulnerability** -- using an f-string to build the query means special characters in `station_name` break the SQL (the apostrophe in "O'Hare" would cause a syntax error or worse). (2) **The apostrophe in "O'Hare" will break the SQL** specifically because the `'` in O'Hare terminates the string literal prematurely, causing a syntax error. Fix: use parameterized queries with `%s` placeholders.

**15.** `docker run` creates and starts a NEW container from an image. `docker exec` runs a command inside an ALREADY RUNNING container. Use `docker run` when you need a fresh container; use `docker exec` when you need to interact with a container that's already up (e.g., to run `psql` inside the PostgreSQL container).
