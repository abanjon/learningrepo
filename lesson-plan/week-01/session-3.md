# Week 1, Session 3: Python Classes, File I/O, CSV Loading

**Domain:** Fitness Tracker Logs
**Concepts:** Python classes, `__init__`, methods, csv module, file reading/writing, context managers
**Duration:** 45-60 minutes

---

## FOLLOW-ALONG (15-20 min)

### Step 1: Set Up the Project

```bash
# Create the database for this project
docker exec weather_db psql -U student -d postgres -c "CREATE DATABASE fitness;"

uv init fitness-tracker
cd fitness-tracker
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
        dbname="fitness",
        user="student",
        password="learningpass"
    )
```

Create the table:

```python
# create_tables.py
from db import get_connection

def create_workouts_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            workout_id SERIAL PRIMARY KEY,
            workout_date DATE NOT NULL,
            exercise VARCHAR(100) NOT NULL,
            duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
            calories_burned INTEGER CHECK (calories_burned >= 0),
            heart_rate_avg INTEGER CHECK (heart_rate_avg BETWEEN 30 AND 250)
        );
    """)
    conn.commit()
    print("Table 'workouts' created.")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    create_workouts_table()
```

```bash
uv run python create_tables.py
```

### Step 2: Create Sample CSV Data

Create `workouts.csv`:

```csv
date,exercise,duration_minutes,calories_burned,heart_rate_avg
2024-01-15,Running,30,350,155
2024-01-15,Push-ups,15,120,130
2024-01-16,Cycling,45,400,140
2024-01-17,Running,25,280,150
2024-01-17,Yoga,60,200,95
2024-01-18,Swimming,40,380,145
2024-01-19,Running,35,390,158
2024-01-19,Push-ups,20,150,135
2024-01-20,Cycling,50,450,142
2024-01-20,Yoga,45,170,90
2024-01-21,Running,30,340,152
2024-01-21,Swimming,35,350,148
invalid_date,Running,30,350,155
2024-01-22,Running,-5,350,155
2024-01-22,,30,350,155
2024-01-23,Running,30,abc,155
```

Note: the last 4 rows have intentional errors. We'll validate them.

### Step 3: Build the WorkoutLoader Class

Create `workout_loader.py`:

```python
# workout_loader.py
import csv
from datetime import datetime
from db import get_connection


class WorkoutLoader:
    """Loads workout CSV data into PostgreSQL with validation.

    Why a class instead of standalone functions?
    1. State: We need to track errors, row counts, and the DB connection
       across multiple method calls. A class bundles this state naturally.
    2. Lifecycle: __init__ sets up, load() does the work, close() tears down.
       This maps cleanly to the open/process/close pattern.
    3. Testability: You can create a WorkoutLoader with a test database
       connection and verify each method independently.
    """

    def __init__(self, filepath: str):
        """Initialize the loader with a CSV file path.

        __init__ is the constructor -- Python calls it automatically when you
        create an instance: loader = WorkoutLoader("workouts.csv").
        'self' is the instance being created. Every method gets it as the
        first argument so it can access instance state (self.filepath, etc.).
        """
        self.filepath = filepath
        self.errors = []       # Collect all validation errors (not just the first)
        self.valid_rows = []   # Rows that passed validation
        self.total_rows = 0    # Total rows attempted

    def validate_row(self, row_num: int, row: dict) -> dict | None:
        """Validate a single CSV row. Return cleaned data or None if invalid.

        We return None (instead of raising an exception) because we want to
        continue processing the rest of the file. Raising would stop on the
        first bad row, and in real data pipelines you often have thousands of
        rows where only a few are bad. Collecting all errors at once lets the
        user fix them in a single pass.
        """
        errors_before = len(self.errors)

        # --- Validate date ---
        workout_date = None
        try:
            # strptime = "string parse time". The format string must match
            # the CSV's date format exactly. %Y = 4-digit year, %m = 2-digit
            # month, %d = 2-digit day.
            workout_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
        except ValueError:
            self.errors.append(f"Row {row_num}: Invalid date '{row['date']}'")

        # --- Validate exercise (required field) ---
        exercise = row.get("exercise", "").strip()
        if not exercise:
            self.errors.append(f"Row {row_num}: Missing exercise name")

        # --- Validate duration ---
        duration = None
        try:
            duration = int(row["duration_minutes"])
            if duration <= 0:
                self.errors.append(f"Row {row_num}: Duration must be positive, got {duration}")
                duration = None
        except ValueError:
            self.errors.append(f"Row {row_num}: Invalid duration '{row['duration_minutes']}'")

        # --- Validate calories ---
        calories = None
        try:
            calories = int(row["calories_burned"])
            if calories < 0:
                self.errors.append(f"Row {row_num}: Calories can't be negative, got {calories}")
                calories = None
        except ValueError:
            self.errors.append(f"Row {row_num}: Invalid calories '{row['calories_burned']}'")

        # --- Validate heart rate ---
        heart_rate = None
        try:
            heart_rate = int(row["heart_rate_avg"])
            if not (30 <= heart_rate <= 250):
                self.errors.append(f"Row {row_num}: Heart rate {heart_rate} outside range 30-250")
                heart_rate = None
        except ValueError:
            self.errors.append(f"Row {row_num}: Invalid heart rate '{row['heart_rate_avg']}'")

        # If any new errors were added, this row is invalid
        if len(self.errors) > errors_before:
            return None

        return {
            "workout_date": workout_date,
            "exercise": exercise,
            "duration_minutes": duration,
            "calories_burned": calories,
            "heart_rate_avg": heart_rate,
        }

    def load(self) -> int:
        """Read the CSV, validate, and insert valid rows into the database.

        Returns the number of rows successfully inserted.

        We use 'with open(...)' (a context manager) to ensure the file is
        closed even if an exception occurs mid-read. Without it, the file
        handle might leak if validate_row() or the DB insert raises.
        """
        # 'with' is a context manager. It guarantees cleanup (file.close())
        # happens even if an exception is thrown inside the block.
        # Under the hood, Python calls file.__enter__() at the start
        # and file.__exit__() at the end (or on exception).
        with open(self.filepath, "r") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=1):
                self.total_rows += 1
                cleaned = self.validate_row(row_num, row)
                if cleaned is not None:
                    self.valid_rows.append(cleaned)

        # Now insert valid rows into the database
        if not self.valid_rows:
            print("No valid rows to insert.")
            return 0

        conn = get_connection()
        cursor = conn.cursor()

        try:
            for row in self.valid_rows:
                cursor.execute(
                    """
                    INSERT INTO workouts (workout_date, exercise, duration_minutes,
                                          calories_burned, heart_rate_avg)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (
                        row["workout_date"],
                        row["exercise"],
                        row["duration_minutes"],
                        row["calories_burned"],
                        row["heart_rate_avg"],
                    ),
                )
            conn.commit()
        except Exception as e:
            # If ANY insert fails, roll back ALL of them.
            # This keeps the database in a consistent state.
            conn.rollback()
            print(f"Database error: {e}")
            return 0
        finally:
            # 'finally' runs no matter what -- even after an exception.
            # This ensures we don't leak database connections.
            cursor.close()
            conn.close()

        return len(self.valid_rows)

    def print_summary(self):
        """Print a human-readable summary of the load operation."""
        print(f"\n{'=' * 50}")
        print(f"  Workout Load Summary")
        print(f"{'=' * 50}")
        print(f"  Total rows:   {self.total_rows}")
        print(f"  Valid rows:   {len(self.valid_rows)}")
        print(f"  Invalid rows: {len(self.errors)}")

        if self.errors:
            print(f"\n  Errors:")
            for error in self.errors:
                print(f"    - {error}")

        print(f"{'=' * 50}")
```

### Step 4: Run the Loader

Create `main.py`:

```python
# main.py
from workout_loader import WorkoutLoader

def main():
    # Create an instance of WorkoutLoader.
    # This calls __init__ with filepath="workouts.csv"
    loader = WorkoutLoader("workouts.csv")

    # load() reads the CSV, validates, and inserts into the DB.
    # It returns the count of successfully inserted rows.
    inserted = loader.load()
    print(f"\nInserted {inserted} rows into the database.")

    # print_summary() shows validation results
    loader.print_summary()


if __name__ == "__main__":
    main()
```

```bash
uv run python main.py
```

Expected output (approximately):

```
Inserted 12 rows into the database.

==================================================
  Workout Load Summary
==================================================
  Total rows:   16
  Valid rows:   12
  Invalid rows: 4

  Errors:
    - Row 13: Invalid date 'invalid_date'
    - Row 14: Duration must be positive, got -5
    - Row 15: Missing exercise name
    - Row 16: Invalid calories 'abc'
==================================================
```

### Step 5: Verify Data in the Database

Create `verify.py`:

```python
# verify.py
from db import get_connection

def verify():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM workouts;")
    count = cursor.fetchone()[0]
    print(f"Total workouts in database: {count}")

    cursor.execute("""
        SELECT exercise, COUNT(*) as sessions, SUM(calories_burned) as total_cal
        FROM workouts
        GROUP BY exercise
        ORDER BY total_cal DESC;
    """)

    print(f"\n{'Exercise':<15} {'Sessions':<10} {'Total Calories'}")
    print("-" * 40)
    for row in cursor.fetchall():
        print(f"{row[0]:<15} {row[1]:<10} {row[2]}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    verify()
```

```bash
uv run python verify.py
```

---

## INDEPENDENT (15-20 min)

### Task: Build an ExportReport Class

The gym owner wants a weekly summary report exported as a CSV file. Build an `ExportReport` class that queries the database and writes a summary.

**Requirements:**

1. **Create a file called `export_report.py`** containing an `ExportReport` class.

2. **The class should:**
   - Accept an output file path in its constructor (e.g., `ExportReport("summary.csv")`)
   - Have a `generate()` method that queries the database and writes the summary CSV
   - Properly close all database connections and file handles (use context managers)

3. **The summary CSV must contain these rows** (one row per metric, not one row per workout):
   - `total_workouts` -- the total number of workout records
   - `total_calories` -- the sum of all calories burned
   - `avg_heart_rate` -- the average heart rate across all workouts (rounded to 1 decimal)
   - `favorite_exercise` -- the exercise that appears most frequently
   - `total_duration_minutes` -- the sum of all workout durations

4. **The CSV format should be:**
   ```
   metric,value
   total_workouts,12
   total_calories,3580
   avg_heart_rate,138.3
   favorite_exercise,Running
   total_duration_minutes,430
   ```

5. **Add a `__main__` block** that creates an ExportReport and calls generate(), then prints confirmation with the output file path.

**Expected behavior:**
- Running the script creates a file called `summary.csv` in the current directory
- The file is valid CSV that can be opened in any spreadsheet application
- The values should match what's actually in the database (verify against your `verify.py` output)
- If the file already exists, it should be overwritten (not appended to)

**Hints:**
- You'll need multiple queries (or one clever query) to compute all the metrics. Think about which SQL aggregate functions give you each metric.
- For "favorite exercise," think about which combination of GROUP BY, COUNT, ORDER BY, and LIMIT finds the most frequent value.
- The `csv.writer` from Python's csv module can write rows to a file. Remember that `writerow()` takes a list or tuple.

---

## REVIEW CHECKLIST

When the student shares their code, verify:

- [ ] ExportReport class has `__init__` that accepts and stores an output file path
- [ ] `generate()` method exists and does the querying + writing
- [ ] Context managers (`with`) used for both file I/O and ideally DB connections
- [ ] All 5 required metrics are computed correctly using SQL aggregate functions
- [ ] Favorite exercise query uses COUNT + GROUP BY + ORDER BY + LIMIT pattern
- [ ] Output CSV has correct `metric,value` format
- [ ] `csv.writer` or `csv.DictWriter` is used (not manual string formatting)
- [ ] Database connections and cursors are properly closed
- [ ] Script runs without errors
- [ ] Output file contains accurate values matching the database

---

## QUIZ (10 min)

Answer all 15 questions.

### Questions

**1. (Multiple Choice)** What is the purpose of `__init__` in a Python class?

A) It's called when the class is deleted from memory
B) It initializes a new instance's attributes when the object is created
C) It defines the class's public interface
D) It's required by Python but has no specific purpose

**2. (What Does This Code Output?)**

```python
class Counter:
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1

c1 = Counter()
c2 = Counter()
c1.increment()
c1.increment()
c2.increment()
print(c1.count, c2.count)
```

A) `2 2`
B) `3 3`
C) `2 1`
D) `0 0`

**3. (Short Answer)** What does `self` refer to in a Python class method? Why is it the first parameter of every instance method?

**4. (Multiple Choice)** What does `csv.DictReader` return for each row?

A) A list of values
B) A tuple of values
C) A dictionary mapping column headers to values
D) A named tuple

**5. (Spot the Bug)**

```python
class DataLoader:
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self.load_data()

    def load_data(self):
        f = open(self.filepath, "r")
        reader = csv.DictReader(f)
        rows = list(reader)
        return rows
```

What is the problem with this code?

**6. (Multiple Choice)** What does the `with` statement guarantee?

A) The code inside runs exactly once
B) The resource's cleanup method (`__exit__`) is called even if an exception occurs
C) No exceptions can occur inside the block
D) The variable is available after the block ends

**7. (What Does This Code Output?)**

```python
with open("test.txt", "w") as f:
    f.write("hello")
    f.write("world")

with open("test.txt", "r") as f:
    print(f.read())
```

A) `hello world`
B) `helloworld`
C) `hello\nworld`
D) An error because the file is closed

**8. (Short Answer)** Explain the difference between `open("file.txt", "w")` and `open("file.txt", "a")`. When would you use each?

**9. (Multiple Choice)** What happens when you call `csv.DictReader(f)` on a file where the first row is `name,age,city`?

A) The first row becomes the first data row
B) The first row is used as dictionary keys for all subsequent rows
C) An error is raised because the header must be passed separately
D) The first row is skipped entirely

**10. (Spot the Bug)**

```python
class WorkoutLoader:
    def __init__(self, filepath):
        self.filepath = filepath
        self.errors = []

    def validate_row(row):
        if not row.get("exercise"):
            self.errors.append("Missing exercise")
            return None
        return row
```

What is wrong with the `validate_row` method? (There are two bugs.)

**11. (What Does This Code Output?)**

```python
data = {"name": "Alice", "age": "30", "city": "Boston"}
values = [data[key] for key in sorted(data.keys())]
print(values)
```

A) `['Alice', '30', 'Boston']`
B) `['30', 'Boston', 'Alice']`
C) `['30', 'Alice', 'Boston']`
D) `{'age': '30', 'city': 'Boston', 'name': 'Alice'}`

**12. (Multiple Choice)** In the WorkoutLoader class, why do we collect errors in a list instead of raising an exception on the first error?

A) Python doesn't support raising exceptions inside classes
B) It's faster than using exceptions
C) It allows processing the entire file and reporting ALL errors at once
D) Lists use less memory than exceptions

**13. (Short Answer)** What is the difference between a class attribute and an instance attribute? Give an example of each.

**14. (What Does This Code Output?)**

```python
import csv
import io

data = "name,score\nAlice,95\nBob,87\n"
reader = csv.DictReader(io.StringIO(data))
rows = list(reader)
print(len(rows), rows[0]["score"])
```

A) `3 95`
B) `2 95`
C) `2 87`
D) An error

**15. (Multiple Choice)** Which of these is a valid way to make a class usable as a context manager (with `with` statements)?

A) Define `__open__` and `__close__` methods
B) Define `__enter__` and `__exit__` methods
C) Define `__with__` and `__done__` methods
D) Inherit from the `Contextual` base class

---

### Answer Key

**1.** B) It initializes a new instance's attributes when the object is created. `__init__` is called automatically by Python right after the instance is created in memory.

**2.** C) `2 1`. `c1` and `c2` are separate instances with their own `count` attribute. `c1.increment()` is called twice (count=2), `c2.increment()` is called once (count=1). Instance attributes are not shared between instances.

**3.** `self` refers to the specific instance of the class that the method is being called on. It's the first parameter because Python needs a way to give each method access to the instance's data (attributes). When you call `loader.load()`, Python translates this to `WorkoutLoader.load(loader)` -- the instance is passed as `self`.

**4.** C) A dictionary mapping column headers to values. If the header row is `date,exercise,duration`, then each row is like `{"date": "2024-01-15", "exercise": "Running", "duration": "30"}`.

**5.** The file `f` is never closed. `open()` is called without a `with` statement, and there's no `f.close()` call. If `load_data()` fails partway through, the file handle leaks. Fix: use `with open(self.filepath, "r") as f:` to ensure the file is closed even on error.

**6.** B) The resource's cleanup method (`__exit__`) is called even if an exception occurs. This is the core guarantee -- `with` ensures cleanup happens no matter what (exception, return, break, etc.).

**7.** B) `helloworld`. Two `write()` calls with no newline between them concatenate directly. `write()` doesn't add newlines automatically (unlike `print()`). To get `hello world`, you'd need `f.write("hello ")` or `f.write("hello\nworld")`.

**8.** `"w"` (write) opens the file and **truncates** it -- any existing content is erased. `"a"` (append) opens the file and positions the cursor at the end -- existing content is preserved and new writes are added after it. Use `"w"` when you want to create a fresh file (like our summary report). Use `"a"` when you want to add to existing content (like a log file that grows over time).

**9.** B) The first row is used as dictionary keys for all subsequent rows. `DictReader` automatically treats the first row as the header unless you pass a `fieldnames` argument.

**10.** Two bugs: (1) `validate_row` is missing `self` as the first parameter -- it should be `def validate_row(self, row):`. Without `self`, Python treats `row` as `self` and the actual row is never received. (2) Because `self` is missing, the reference to `self.errors` will raise a `NameError` (or, more precisely, `row` will be the WorkoutLoader instance and `.get("exercise")` will fail with an `AttributeError`).

**11.** B) `['30', 'Boston', 'Alice']`. `sorted(data.keys())` gives `['age', 'city', 'name']` (alphabetical order), so the list comprehension produces `data['age']`, `data['city']`, `data['name']` = `'30'`, `'Boston'`, `'Alice'`.

**12.** C) It allows processing the entire file and reporting ALL errors at once. In data engineering, you often have files with thousands of rows. Stopping at the first error means the user fixes one error, re-runs, hits another, fixes it, re-runs... Collecting all errors lets them fix everything in one pass.

**13.** A **class attribute** is shared by all instances of the class -- it's defined directly in the class body (e.g., `class Dog: species = "canine"`). An **instance attribute** is unique to each instance -- it's defined in `__init__` using `self` (e.g., `self.name = name`). If you change a class attribute, all instances see the change. If you change an instance attribute, only that instance is affected.

**14.** B) `2 95`. The header row (`name,score`) is consumed by DictReader as column names, leaving 2 data rows. `rows[0]` is `{"name": "Alice", "score": "95"}`, so `rows[0]["score"]` is the string `"95"`. Note: it's a string, not an integer -- csv module doesn't auto-convert types.

**15.** B) Define `__enter__` and `__exit__` methods. These are the Python data model methods that the `with` statement uses. `__enter__` sets up the resource and returns it; `__exit__` cleans up (close file, release connection, etc.).
