# Week 1, Session 5: SoundStream Cumulative Project

**Branch:** `cumulative`
**Concepts Applied:** Docker, PostgreSQL, uv, Python project structure, CREATE TABLE, INSERT, SELECT, foreign keys, classes, CSV/data loading, validation, error handling
**Duration:** 45-60 minutes

---

## BRIEF (5 min)

This session brings together everything from Week 1. You're building the **foundation** of SoundStream -- a music data platform that will grow over the next 15 weeks.

This week you will:
- Set up the SoundStream database in Docker
- Create a Python project in the `soundstream/` directory
- Design and implement the core schema: artists, albums, and tracks
- Write a seed script that generates realistic fake data using Faker
- Write 5 analytical queries that prove the schema works

By the end, you'll have a running PostgreSQL database with 50 artists, 150 albums, and 500 tracks -- and queries that answer real music industry questions.

**This is a no-code session.** You'll receive requirements and acceptance criteria only. Use what you learned in Sessions 1-4 to build everything yourself.

---

## REQUIREMENTS

### 1. Database Setup

- Run a PostgreSQL 16 container named `soundstream_db` (or reuse the existing container and create a new database inside it)
- Create a database called `soundstream_dev`
- The database should be accessible on `localhost:5432`

### 2. Python Project

- Create a Python project in the `soundstream/` directory at the repository root
- Use `uv` for project management
- Add these dependencies: `psycopg2-binary`, `faker`
- Create a `db.py` module with a `get_connection()` function

### 3. Schema Design

Create three tables with the following structure:

**`artists` table:**
- Auto-incrementing primary key
- Artist/band name (required, up to 150 characters)
- Genre (up to 50 characters)
- Country of origin (up to 100 characters)
- Year the artist/band was formed (integer)

**`albums` table:**
- Auto-incrementing primary key
- Album title (required, up to 200 characters)
- Foreign key referencing the artists table
- Release date
- Record label name (up to 100 characters)

**`tracks` table:**
- Auto-incrementing primary key
- Track title (required, up to 200 characters)
- Foreign key referencing the albums table
- Duration in seconds (integer, must be positive)
- Track number on the album (integer, must be positive)

**Schema rules:**
- All foreign keys must be properly declared with REFERENCES
- Use appropriate data types (review Session 1's discussion of NUMERIC vs INTEGER vs VARCHAR)
- Add sensible NOT NULL and CHECK constraints where they make sense
- Tables should be created idempotently (use IF NOT EXISTS)

### 4. Seed Data Script

Create a `seed_data.py` script that:
- Uses the Faker library to generate realistic-looking data
- Creates exactly **50 artists** with varied genres and countries
- Creates exactly **150 albums** distributed across the 50 artists (average 3 per artist, but some variety is fine)
- Creates exactly **500 tracks** distributed across the 150 albums
- Track durations should be realistic (somewhere between 30 seconds and 10 minutes)
- Track numbers should be sequential within each album (track 1, 2, 3... not random)
- The script should be idempotent: if the tables already have data, either clear them first or skip insertion
- All inserts should use parameterized queries
- The entire seed operation should be wrapped in a transaction (commit at the end, rollback on error)
- Print a summary of what was inserted

### 5. Analytical Queries

Create a `queries.py` script that runs these 5 queries and prints formatted results:

**Query 1: Tracks Per Artist**
Show each artist and how many tracks they have across all their albums. Sort by track count, highest first. Limit to top 10.

**Query 2: Longest Album by Total Duration**
Find the album with the highest total duration (sum of all its track durations). Show the album title, artist name, total duration in minutes, and number of tracks.

**Query 3: Artists by Country**
Count how many artists are from each country. Sort by count, highest first.

**Query 4: Albums Released in the Last Year**
Find all albums with a release date within the past 365 days from the current date. Show album title, artist name, and release date. (Hint: use `CURRENT_DATE - INTERVAL '1 year'`.)

**Query 5: Tracks Longer Than 5 Minutes**
Find all tracks longer than 300 seconds. Show track title, album title, artist name, and duration formatted as "M:SS". Sort by duration, longest first. Limit to 20.

---

## ACCEPTANCE CRITERIA

All of the following must pass for the session to be complete:

### AC-1: Docker Container Running

```bash
docker ps
```
Must show a PostgreSQL container running with the `soundstream_dev` database accessible.

### AC-2: Seed Script Completes Without Errors

```bash
cd soundstream && uv run python seed_data.py
```
Must complete successfully and print a summary showing 50 artists, 150 albums, and 500 tracks inserted.

### AC-3: Row Counts Match

Run these from within Python or via `docker exec`:
```sql
SELECT 'artists' as table_name, COUNT(*) as row_count FROM artists
UNION ALL
SELECT 'albums', COUNT(*) FROM albums
UNION ALL
SELECT 'tracks', COUNT(*) FROM tracks;
```
Expected result: artists=50, albums=150, tracks=500.

### AC-4: All 5 Queries Return Non-Empty Results

```bash
cd soundstream && uv run python queries.py
```
Each of the 5 queries must print at least one row of results. None should return empty.

### AC-5: Foreign Key Enforcement

Run this from Python or psql -- it should FAIL with a foreign key violation error:
```sql
INSERT INTO tracks (title, album_id, duration_seconds, track_number)
VALUES ('Ghost Track', 99999, 180, 1);
```
The error should mention a foreign key constraint violation on `album_id`. This proves the foreign key relationship is enforced.

### AC-6: Project Structure

The `soundstream/` directory should contain at minimum:
- `pyproject.toml` (with psycopg2-binary and faker as dependencies)
- `db.py` (connection module)
- `create_tables.py` or equivalent schema creation script
- `seed_data.py`
- `queries.py`
