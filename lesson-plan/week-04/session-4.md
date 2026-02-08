# Week 4, Session 4: Database Migrations & Schema Versioning
**Domain:** Hotel reservation system
**Concepts:** Schema evolution, migration scripts, forward/rollback migrations, version tracking, alembic concepts (manual approach)
**Prerequisites:** PostgreSQL running in Docker, Python with psycopg2

---

## FOLLOW-ALONG

### Step 1: Create the initial hotel database schema

We start simple on purpose. Real schemas always start simple and evolve. The migration system we'll build handles that evolution safely.

```sql
-- File: hotel_reservations/migrations/000_initial_schema.up.sql

-- This is the starting point: a minimal hotel reservation system.
-- We'll evolve this through migrations, just like you would in a real project.

CREATE TABLE IF NOT EXISTS guests (
    id SERIAL PRIMARY KEY,
    guest_name VARCHAR(200) NOT NULL,
    email VARCHAR(200) NOT NULL UNIQUE,
    phone VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    room_number VARCHAR(10) NOT NULL UNIQUE,
    floor INTEGER NOT NULL,
    capacity INTEGER NOT NULL DEFAULT 2,
    -- Price is stored directly on the room. Later we'll refactor this
    -- into a room_types table (that's what migration 001 will do).
    price_per_night NUMERIC(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS reservations (
    id SERIAL PRIMARY KEY,
    guest_id INTEGER NOT NULL REFERENCES guests(id),
    room_id INTEGER NOT NULL REFERENCES rooms(id),
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'confirmed',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    -- Business rule: check_out must be after check_in
    CHECK (check_out > check_in)
);
```

```sql
-- File: hotel_reservations/migrations/000_initial_schema.down.sql

-- The down migration reverses the up migration.
-- Order matters: drop tables with FKs first to avoid dependency errors.
DROP TABLE IF EXISTS reservations;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS guests;
```

Now seed some data so we have something to verify against after migrations:

```sql
-- File: hotel_reservations/seed.sql

INSERT INTO guests (guest_name, email, phone) VALUES
    ('John Smith', 'john@example.com', '555-0101'),
    ('Jane Doe', 'jane@example.com', '555-0102'),
    ('Bob Wilson', 'bob@example.com', '555-0103'),
    ('Alice Brown', 'alice@example.com', '555-0104');

INSERT INTO rooms (room_number, floor, capacity, price_per_night) VALUES
    ('101', 1, 2, 99.99),
    ('102', 1, 2, 99.99),
    ('201', 2, 4, 149.99),
    ('202', 2, 2, 119.99),
    ('301', 3, 4, 199.99),
    ('PH1', 4, 6, 499.99);

INSERT INTO reservations (guest_id, room_id, check_in, check_out, status) VALUES
    (1, 1, '2025-03-01', '2025-03-05', 'confirmed'),
    (2, 3, '2025-03-10', '2025-03-14', 'confirmed'),
    (3, 5, '2025-04-01', '2025-04-03', 'checked_in'),
    (4, 6, '2025-05-15', '2025-05-20', 'confirmed'),
    (1, 2, '2025-06-01', '2025-06-03', 'confirmed');
```

Run the initial schema, then the seed data. Verify with `SELECT * FROM reservations;`.

### Step 2: Build the migration tracking table

Every migration system needs a way to know which migrations have already been applied. We use a simple table for this.

```sql
-- File: hotel_reservations/migrations/create_migration_tracker.sql

-- This table records which migrations have been applied.
-- The migration runner checks this before running each migration.
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    applied_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Record that the initial schema (version 0) has been applied.
INSERT INTO schema_migrations (version, name) VALUES (0, 'initial_schema')
ON CONFLICT (version) DO NOTHING;
```

Run this now.

### Step 3: Migration 001 — Add room_types table and FK

The first real migration: extract room types into their own table. This is a common refactoring — moving from a column on the entity to a normalized lookup table.

```sql
-- File: hotel_reservations/migrations/001_add_room_types.up.sql

-- WHY: Storing price on each room means if we change the price for "Standard Double",
-- we have to update every room individually. A room_types table gives us
-- one source of truth for pricing and avoids update anomalies.

CREATE TABLE IF NOT EXISTS room_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    base_price_per_night NUMERIC(10, 2) NOT NULL
);

-- Seed room types from existing data. We infer types from price ranges.
INSERT INTO room_types (name, base_price_per_night) VALUES
    ('Standard', 99.99),
    ('Deluxe', 119.99),
    ('Suite', 149.99),
    ('Premium Suite', 199.99),
    ('Penthouse', 499.99);

-- Add the FK column. We use a default initially so existing rows don't violate NOT NULL.
ALTER TABLE rooms ADD COLUMN room_type_id INTEGER;

-- Map existing rooms to room types based on their current price.
-- This is a DATA migration: we're not just changing schema, we're moving data.
UPDATE rooms SET room_type_id = (
    SELECT rt.id FROM room_types rt
    WHERE rt.base_price_per_night = rooms.price_per_night
    LIMIT 1
);

-- Now that all rooms have a type, make the column NOT NULL and add the FK.
ALTER TABLE rooms ALTER COLUMN room_type_id SET NOT NULL;
ALTER TABLE rooms ADD CONSTRAINT fk_rooms_room_type
    FOREIGN KEY (room_type_id) REFERENCES room_types(id);

-- We keep price_per_night on rooms for now (it might differ from the base
-- price for specific rooms). In a future migration we could remove it.
```

```sql
-- File: hotel_reservations/migrations/001_add_room_types.down.sql

-- Reverse migration 001: remove the room_types table and FK.
-- Order: drop FK first, then column, then table.
ALTER TABLE rooms DROP CONSTRAINT IF EXISTS fk_rooms_room_type;
ALTER TABLE rooms DROP COLUMN IF EXISTS room_type_id;
DROP TABLE IF EXISTS room_types;
```

### Step 4: Migration 002 — Split guest_name into first/last

Names stored as a single string are hard to sort, search, and display. This migration splits them.

```sql
-- File: hotel_reservations/migrations/002_split_guest_name.up.sql

-- WHY: "John Smith" as a single field means you can't sort by last name,
-- can't greet the guest by first name in emails, and can't handle
-- names with multiple spaces correctly. Separate fields are better.

-- Add the new columns (nullable at first so existing rows don't break).
ALTER TABLE guests ADD COLUMN first_name VARCHAR(100);
ALTER TABLE guests ADD COLUMN last_name VARCHAR(100);

-- Migrate existing data: split on the first space.
-- This is a simplistic approach -- real names are complex (prefixes, suffixes,
-- multiple last names). For a learning exercise, first-space split works.
UPDATE guests SET
    first_name = SPLIT_PART(guest_name, ' ', 1),
    last_name = CASE
        -- If there's no space, put the whole name in last_name
        WHEN POSITION(' ' IN guest_name) = 0 THEN guest_name
        ELSE SUBSTRING(guest_name FROM POSITION(' ' IN guest_name) + 1)
    END;

-- Now make them NOT NULL since all rows have values.
ALTER TABLE guests ALTER COLUMN first_name SET NOT NULL;
ALTER TABLE guests ALTER COLUMN last_name SET NOT NULL;

-- Don't drop guest_name yet! Keep it for backward compatibility.
-- A future migration can remove it once all code uses first_name/last_name.
-- This is called "expand and contract" -- expand the schema first,
-- migrate consumers, then contract (remove the old column).
```

```sql
-- File: hotel_reservations/migrations/002_split_guest_name.down.sql

-- Reverse: drop the new columns. guest_name is still intact.
ALTER TABLE guests DROP COLUMN IF EXISTS first_name;
ALTER TABLE guests DROP COLUMN IF EXISTS last_name;
```

### Step 5: Migration 003 — Add amenities JSONB column

JSONB is PostgreSQL's way to store semi-structured data. It's perfect for attributes that vary between rooms.

```sql
-- File: hotel_reservations/migrations/003_add_amenities.up.sql

-- WHY: Different rooms have different amenities (wifi, minibar, balcony, etc.).
-- A normalized approach would be an amenities table + a junction table.
-- But amenities are display-only -- we don't JOIN on them or use them in
-- complex queries. JSONB is simpler and faster for this use case.
-- Rule of thumb: use JSONB for data you read but rarely query against.

ALTER TABLE rooms ADD COLUMN amenities JSONB NOT NULL DEFAULT '[]'::jsonb;

-- Set amenities for existing rooms based on their type.
UPDATE rooms SET amenities = '["wifi", "tv", "air_conditioning"]'::jsonb
WHERE room_type_id IN (SELECT id FROM room_types WHERE name = 'Standard');

UPDATE rooms SET amenities = '["wifi", "tv", "air_conditioning", "minibar"]'::jsonb
WHERE room_type_id IN (SELECT id FROM room_types WHERE name = 'Deluxe');

UPDATE rooms SET amenities = '["wifi", "tv", "air_conditioning", "minibar", "living_room"]'::jsonb
WHERE room_type_id IN (SELECT id FROM room_types WHERE name IN ('Suite', 'Premium Suite'));

UPDATE rooms SET amenities = '["wifi", "tv", "air_conditioning", "minibar", "living_room", "balcony", "jacuzzi", "butler_service"]'::jsonb
WHERE room_type_id IN (SELECT id FROM room_types WHERE name = 'Penthouse');

-- You can query JSONB with the @> (contains) operator:
-- SELECT * FROM rooms WHERE amenities @> '["jacuzzi"]';
```

```sql
-- File: hotel_reservations/migrations/003_add_amenities.down.sql

ALTER TABLE rooms DROP COLUMN IF EXISTS amenities;
```

### Step 6: Build the migration runner in Python

This is the core of a migration system: a script that reads migration files, checks which ones have been applied, and runs the pending ones in order.

```python
# File: hotel_reservations/migrate.py

"""
Simple database migration runner.

How it works:
1. Reads the schema_migrations table to see what's been applied.
2. Scans the migrations/ directory for .up.sql and .down.sql files.
3. Applies pending migrations in order (up), or rolls back (down).

File naming convention: NNN_description.up.sql / NNN_description.down.sql
where NNN is a zero-padded version number.

This is a simplified version of what tools like Alembic, Flyway, or
golang-migrate do. The concepts are identical.
"""

import os
import sys
import glob
import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "postgres",
}

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


def get_applied_versions(conn):
    """Query the schema_migrations table to find which versions are applied."""
    with conn.cursor() as cur:
        cur.execute("SELECT version, name FROM schema_migrations ORDER BY version")
        return {row[0]: row[1] for row in cur.fetchall()}


def discover_migrations(direction="up"):
    """Scan the migrations directory for SQL files.
    Returns a sorted list of (version, name, filepath) tuples."""
    pattern = os.path.join(MIGRATIONS_DIR, f"*{direction}.sql")
    migrations = []
    for filepath in sorted(glob.glob(pattern)):
        filename = os.path.basename(filepath)
        # Parse "001_add_room_types.up.sql" -> version=1, name="add_room_types"
        parts = filename.split("_", 1)
        try:
            version = int(parts[0])
        except ValueError:
            continue  # Skip files that don't start with a number
        name = parts[1].replace(f".{direction}.sql", "")
        migrations.append((version, name, filepath))
    return sorted(migrations, key=lambda x: x[0])


def run_migration(conn, filepath):
    """Execute a SQL file against the database."""
    with open(filepath) as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def migrate_up(conn, target_version=None):
    """Apply all pending migrations up to target_version (or all if None)."""
    applied = get_applied_versions(conn)
    available = discover_migrations("up")

    # Filter to only pending (not yet applied) migrations
    pending = [(v, n, f) for v, n, f in available if v not in applied]

    if target_version is not None:
        pending = [(v, n, f) for v, n, f in pending if v <= target_version]

    if not pending:
        print("No pending migrations.")
        return

    for version, name, filepath in pending:
        print(f"Applying migration {version:03d}_{name}...")
        try:
            run_migration(conn, filepath)
            # Record that this migration was applied
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
                    (version, name),
                )
            conn.commit()
            print(f"  ✓ Applied successfully")
        except Exception as e:
            conn.rollback()
            print(f"  ✗ FAILED: {e}")
            print("Stopping migration. Fix the error and retry.")
            sys.exit(1)

    print(f"\nAll migrations applied. Current version: {pending[-1][0]}")


def migrate_down(conn, target_version):
    """Rollback migrations down to (but not including) target_version."""
    applied = get_applied_versions(conn)
    available = discover_migrations("down")

    # We need to rollback in REVERSE order (newest first)
    to_rollback = [
        (v, n, f) for v, n, f in available
        if v in applied and v > target_version
    ]
    to_rollback.sort(key=lambda x: x[0], reverse=True)

    if not to_rollback:
        print(f"Nothing to rollback. Already at or below version {target_version}.")
        return

    for version, name, filepath in to_rollback:
        print(f"Rolling back migration {version:03d}_{name}...")
        try:
            run_migration(conn, filepath)
            # Remove the record from schema_migrations
            with conn.cursor() as cur:
                cur.execute("DELETE FROM schema_migrations WHERE version = %s", (version,))
            conn.commit()
            print(f"  ✓ Rolled back successfully")
        except Exception as e:
            conn.rollback()
            print(f"  ✗ FAILED: {e}")
            print("Stopping rollback. Manual intervention required.")
            sys.exit(1)

    print(f"\nRollback complete. Current version: {target_version}")


def show_status(conn):
    """Show current migration status."""
    applied = get_applied_versions(conn)
    available_up = discover_migrations("up")

    print("Migration Status")
    print("=" * 50)
    for version, name, _ in available_up:
        status = "APPLIED" if version in applied else "PENDING"
        print(f"  {version:03d}_{name}: {status}")

    if applied:
        print(f"\nCurrent version: {max(applied.keys())}")
    else:
        print("\nNo migrations applied.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python migrate.py up              -- Apply all pending migrations")
        print("  python migrate.py up 2            -- Apply up to version 2")
        print("  python migrate.py down 0          -- Rollback to version 0")
        print("  python migrate.py status          -- Show migration status")
        sys.exit(1)

    command = sys.argv[1]
    conn = psycopg2.connect(**DB_CONFIG)

    try:
        if command == "up":
            target = int(sys.argv[2]) if len(sys.argv) > 2 else None
            migrate_up(conn, target)
        elif command == "down":
            if len(sys.argv) < 3:
                print("Error: 'down' requires a target version (e.g., 'down 0')")
                sys.exit(1)
            target = int(sys.argv[2])
            migrate_down(conn, target)
        elif command == "status":
            show_status(conn)
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    finally:
        conn.close()
```

### Step 7: Run the migration system

Test the full cycle:

```bash
# See current status (only version 0 should be applied)
python hotel_reservations/migrate.py status

# Apply all migrations
python hotel_reservations/migrate.py up

# Check status again (all should be APPLIED)
python hotel_reservations/migrate.py status

# Verify the schema changes
psql -c "SELECT * FROM room_types;"
psql -c "SELECT first_name, last_name, guest_name FROM guests;"
psql -c "SELECT room_number, amenities FROM rooms;"

# Now rollback to version 1 (keeps room_types, removes name split and amenities)
python hotel_reservations/migrate.py down 1

# Verify: first_name and last_name should be gone, amenities should be gone
psql -c "\d guests"
psql -c "\d rooms"

# Re-apply everything
python hotel_reservations/migrate.py up
```

Run each command and verify the output matches expectations.

---

## INDEPENDENT

You have 15-20 minutes. Create two new migration files and a verification step. Save all files in the `hotel_reservations/migrations/` directory.

### Task 1: Migration 004 — Add a reviews table

Create `004_add_reviews.up.sql` and `004_add_reviews.down.sql`.

The reviews table should have:
- `id` (serial primary key)
- `guest_id` (foreign key to guests)
- `reservation_id` (foreign key to reservations)
- `rating` (integer, constrained between 1 and 5)
- `comment` (text, nullable)
- `created_at` (timestamp, defaults to now)

The up migration should also add a unique constraint so a guest can only review a reservation once. The down migration should drop the table.

### Task 2: Migration 005 — Add composite index on reservations

Create `005_add_reservation_date_index.up.sql` and `005_add_reservation_date_index.down.sql`.

The up migration should create a composite index on `reservations(check_in, check_out)` to speed up date range searches (e.g., "find all reservations overlapping with March 2025"). The down migration should drop the index.

### Task 3: Migration verification function

Add a function to `migrate.py` called `verify_schema` that, after migrations are applied, checks that the database schema matches expected state. Specifically, it should verify:
- That all expected tables exist (guests, rooms, reservations, room_types, reviews, schema_migrations)
- That the `reviews` table has the correct columns (check by querying `information_schema.columns`)
- That the composite index on reservations exists (check by querying `pg_indexes`)

The function should print a pass/fail for each check. Wire it into the CLI so `python migrate.py verify` runs it.

---

## REVIEW CHECKLIST

When reviewing the student's independent work, check for:

- [ ] **Task 1:** Reviews table has all required columns with correct types. FK constraints reference guests and reservations. CHECK constraint on rating (1-5). UNIQUE constraint on (guest_id, reservation_id). Down migration drops the table cleanly.
- [ ] **Task 2:** Composite index on (check_in, check_out). Down migration drops the index with `DROP INDEX`.
- [ ] **Task 3:** Verify function checks for table existence, column correctness, and index existence. Uses `information_schema` or `pg_catalog` queries. Prints clear pass/fail output.
- [ ] Student ran `python migrate.py up` and `python migrate.py status` showing all 5 migrations applied.
- [ ] Student ran `python migrate.py down 3` and `python migrate.py up` to verify rollback/reapply works.
- [ ] Student ran `python migrate.py verify` and all checks pass.

---

## QUIZ

Answer all 15 questions. The session quiz will use 10 of these; extras are reserved for retries.

---

**Q1 (Multiple Choice).** What is a database migration?

A) Moving data from one database server to another
B) A versioned, incremental change to a database schema
C) A backup of the database
D) Converting data from one format to another

---

**Q2 (Short Answer).** Why should every "up" migration have a corresponding "down" migration?

---

**Q3 (Multiple Choice).** In what order should rollback (down) migrations be applied?

A) The same order they were originally applied (oldest first)
B) Reverse order (newest first)
C) Any order, since they're independent
D) Alphabetical order by filename

---

**Q4 (Spot the Bug).** A developer writes this migration:

```sql
-- up migration
ALTER TABLE users ADD COLUMN age INTEGER NOT NULL;
```

This migration will fail on a table that already has rows. Why, and how would you fix it?

---

**Q5 (Short Answer).** What is the "expand and contract" pattern in database migrations? Give an example.

---

**Q6 (Multiple Choice).** Which of these is a DATA migration (as opposed to a schema migration)?

A) Adding a new column to a table
B) Creating a new index
C) Splitting a `full_name` column into `first_name` and `last_name` and populating them
D) Dropping an unused table

---

**Q7 (What does this code output?).** You run these commands in sequence:

```bash
python migrate.py up       # Applies versions 1, 2, 3
python migrate.py down 1   # Rolls back to version 1
python migrate.py status
```

What does the status output show for versions 1, 2, and 3?

---

**Q8 (Short Answer).** Why is it dangerous to run `ALTER TABLE ... DROP COLUMN` in a production migration without a multi-step approach?

---

**Q9 (Multiple Choice).** What table does a typical migration runner use to track applied migrations?

A) pg_catalog.pg_tables
B) information_schema.tables
C) A custom table (e.g., schema_migrations or alembic_version)
D) The migration files themselves (no table needed)

---

**Q10 (Spot the Bug).** A developer writes two migrations:

```
-- Migration 004 (up)
ALTER TABLE orders ADD COLUMN discount NUMERIC(5,2) DEFAULT 0;

-- Migration 005 (up)
ALTER TABLE orders ADD COLUMN total NUMERIC(10,2);
UPDATE orders SET total = subtotal - discount;
```

Migration 005 is rolled back, then migration 004 is rolled back. Then both are re-applied. What problem occurs?

---

**Q11 (Short Answer).** What is a "zero-downtime migration," and name one technique to achieve it?

---

**Q12 (Multiple Choice).** When adding a foreign key constraint to an existing table with data, what must you ensure?

A) The table must be empty
B) All existing values in the FK column must reference valid rows in the parent table
C) The parent table must have fewer rows than the child table
D) The FK column must be the primary key

---

**Q13 (Short Answer).** What is the difference between using `ALTER TABLE ... ADD COLUMN ... DEFAULT value` and adding the column as nullable first, then updating, then setting NOT NULL?

---

**Q14 (What does this code output?).** A schema_migrations table contains versions [0, 1, 2, 3]. You run `migrate_down(conn, 1)`. Which version numbers are removed from schema_migrations?

---

**Q15 (Multiple Choice).** Which ALTER TABLE operation can cause significant table locking on large tables?

A) Adding a nullable column with no default
B) Adding a column with a DEFAULT value (PostgreSQL 11+)
C) Renaming a column
D) Adding a NOT NULL constraint with a CHECK on existing data

---

### ANSWER KEY

**Q1:** B -- A database migration is a versioned, incremental change to the schema (and sometimes data). Migrations are applied in order and tracked so you know which version the database is at.

**Q2:** The down migration enables rollback if something goes wrong. Without it, if a migration introduces a bug, you can't easily revert the schema to its previous state. It also enables development workflows where you switch between branches that have different schema versions.

**Q3:** B -- Rollbacks are applied in reverse order (newest first). If migration 3 depends on structures created by migration 2, you must undo 3 before undoing 2.

**Q4:** Adding a NOT NULL column without a DEFAULT fails because existing rows would have NULL in that column, violating the constraint. Fix: either add a DEFAULT (`ALTER TABLE users ADD COLUMN age INTEGER NOT NULL DEFAULT 0`) or add it as nullable, UPDATE existing rows, then alter to NOT NULL.

**Q5:** "Expand and contract" is a two-phase migration strategy. First, expand: add the new structure alongside the old one (e.g., add `first_name` and `last_name` columns while keeping `full_name`). Migrate application code to use the new columns. Then contract: remove the old column in a later migration once nothing reads it. This avoids breaking running application code during the transition.

**Q6:** C -- Splitting `full_name` into `first_name`/`last_name` and populating them involves modifying actual data, not just the schema structure. A/B/D only change the schema definition without transforming data values.

**Q7:** Version 1: APPLIED, Version 2: PENDING, Version 3: PENDING. The `down 1` command rolled back versions 3 and 2 (in that order) but left version 1 in place.

**Q8:** If application code still references that column, queries will fail immediately. Even if you deploy new code simultaneously, there's a window where the old code is running against the new schema. Also, dropping a column permanently destroys data -- if the migration has a bug, you can't recover the data without a backup. The safe approach is expand-and-contract: stop writing to the column, stop reading it, then drop it in a later migration.

**Q9:** C -- Migration tools use their own tracking table. The table name varies by tool: `schema_migrations` (Rails), `alembic_version` (Alembic), `flyway_schema_history` (Flyway), etc. System catalogs (A/B) track actual schema state but not migration history.

**Q10:** When migration 005 is first applied, `discount` exists (from 004), so `UPDATE orders SET total = subtotal - discount` works. After rolling back both and re-applying, the same thing happens -- this actually works fine. The real issue is if migration 005's down migration doesn't drop the `total` column -- then re-applying 005 would fail with "column already exists." Always make sure down migrations completely undo the up migration.

**Q11:** A zero-downtime migration changes the database schema without any period of unavailability or errors for users. Techniques include: expand-and-contract (add new column, migrate code, remove old column); creating a new table and backfilling rather than using ALTER on a hot table; using `CREATE INDEX CONCURRENTLY` to avoid locking; adding NOT NULL constraints via a separate CHECK constraint.

**Q12:** B -- All existing values in the FK column must reference valid rows in the parent table. If any orphaned values exist, the `ADD CONSTRAINT` will fail. You must clean up orphaned data first (delete rows or set the FK column to a valid value).

**Q13:** In PostgreSQL 11+, `ADD COLUMN ... DEFAULT value` for a non-volatile default doesn't rewrite the table -- it stores the default in the catalog and applies it lazily. This is fast even on huge tables. The three-step approach (add nullable, update, set NOT NULL) requires an actual UPDATE of every row, which acquires row locks and can be very slow on large tables. For Postgres 11+, use the single-statement approach. For older versions, the three-step approach avoids a full table rewrite for the ALTER.

**Q14:** Versions 2 and 3 are removed. `migrate_down(conn, 1)` rolls back everything above version 1, which means versions 3 and 2 (in that order). Version 1 and version 0 remain.

**Q15:** D -- Adding a NOT NULL constraint requires PostgreSQL to scan every row to verify no NULLs exist, which acquires a lock. Options A and B (in PG 11+) are metadata-only operations. Option C (rename) is also a metadata-only catalog update. The safe alternative is `ALTER TABLE ADD CONSTRAINT check_not_null CHECK (column IS NOT NULL) NOT VALID;` followed by `VALIDATE CONSTRAINT` which holds only a weaker lock.
