# Week 2, Session 5: SoundStream -- Users, Streaming, and Playlists
**Branch:** cumulative
**Builds on:** Week 1 Session 5 (base schema with artists, albums, tracks)
**Concepts applied:** Foreign keys, JOINs, generators, pytest, integration testing

---

## BRIEF

This week you expand SoundStream from a music catalog into a platform with users, streaming events, and playlists. You'll:

1. Add 4 new tables with proper foreign key relationships to the existing schema.
2. Build a generator-based stream loader that batch-inserts streaming events from a CSV file with deduplication.
3. Write 5 JOIN queries that answer real analytical questions about the platform.
4. Write pytest integration tests covering deduplication, foreign key enforcement, and query correctness.

By the end, SoundStream will have a complete relational model connecting artists → albums → tracks → streams → users → playlists.

---

## REQUIREMENTS

### 1. New Tables

Add these tables to the SoundStream database. They must reference the existing `artists`, `albums`, and `tracks` tables from Week 1.

**`users` table:**
- `user_id` -- auto-incrementing primary key
- `username` -- unique, not null, max 50 characters
- `email` -- unique, not null, max 150 characters
- `country` -- not null, max 50 characters (e.g., 'US', 'Japan', 'Brazil')
- `joined_date` -- date, not null, default to current date

**`streams` table:**
- `stream_id` -- auto-incrementing primary key
- `user_id` -- foreign key to `users`, not null
- `track_id` -- foreign key to `tracks`, not null
- `streamed_at` -- timestamp, not null
- `duration_listened` -- integer (seconds), not null, must be > 0
- Unique constraint on (`user_id`, `track_id`, `streamed_at`) to prevent duplicate stream events

**`playlists` table:**
- `playlist_id` -- auto-incrementing primary key
- `name` -- not null, max 100 characters
- `user_id` -- foreign key to `users`, not null
- `created_at` -- timestamp, not null, default to current timestamp

**`playlist_tracks` table:**
- `playlist_track_id` -- auto-incrementing primary key
- `playlist_id` -- foreign key to `playlists`, not null, with ON DELETE CASCADE (deleting a playlist removes all its track entries)
- `track_id` -- foreign key to `tracks`, not null
- `position` -- integer, not null (ordering of tracks in the playlist)
- Unique constraint on (`playlist_id`, `position`) so no two tracks share a position

Insert seed data: at least 5 users, 3 playlists (each with at least 3 tracks), and at least 10 manual stream records.

### 2. Stream Loader (`stream_loader.py`)

Build a script that loads streaming events from a CSV file into the `streams` table.

**CSV format:**
```
user_id,track_id,streamed_at,duration_listened
1,3,2024-06-15 14:30:00,187
2,1,2024-06-15 14:31:00,240
1,3,2024-06-15 14:30:00,187
```

The third row above is a duplicate of the first (same user + track + timestamp).

**Requirements:**
- Create a generator function that reads the CSV file and yields one parsed row at a time (do NOT load the entire file into memory).
- Use a chunked batch insert pattern (chunks of 500 rows, using `execute_values` from `psycopg2.extras`).
- Handle duplicates gracefully using `ON CONFLICT (user_id, track_id, streamed_at) DO NOTHING` so duplicates are silently skipped rather than causing errors.
- Print a summary at the end: total rows in file, rows inserted, duplicates skipped.
- The script should also generate a test CSV with at least 1000 rows (including some deliberate duplicates) if no file argument is given.

**Running:**
- `python stream_loader.py` -- generates a test CSV and loads it
- `python stream_loader.py my_streams.csv` -- loads a provided CSV

### 3. JOIN Queries

Create a file called `queries.py` (or add to an existing queries module) that contains 5 functions, each executing and returning results for one analytical query:

1. **`user_top_tracks(user_id, limit=5)`** -- A user's top N most-played tracks, ordered by play count descending. Returns: track name, artist name, play count.

2. **`most_streamed_artist()`** -- The single most-streamed artist across all users (by total stream count). Returns: artist name, total streams.

3. **`playlist_contents(playlist_id)`** -- Full contents of a playlist with track and artist details, ordered by position. Returns: position, track name, artist name, album name.

4. **`users_never_streamed()`** -- Users who have a SoundStream account but have never streamed a single track. Returns: username, email, joined_date.

5. **`tracks_in_most_playlists(limit=10)`** -- Tracks that appear in the most playlists, ordered by playlist count descending. Returns: track name, artist name, playlist count.

Each function takes a database connection as its first argument.

### 4. Tests (`test_soundstream.py`)

Write at least 5 pytest integration tests in a file called `test_soundstream.py`. Use a conftest.py with appropriate fixtures (session-scoped for the database connection, function-scoped for cleanup).

**Required tests:**

1. **Stream deduplication:** Insert the same stream event twice via `stream_loader.py`'s insert logic. Verify only one row exists in the database.

2. **Foreign key enforcement on streams:** Attempt to insert a stream with a nonexistent `user_id`. Verify it raises an IntegrityError.

3. **Foreign key enforcement on playlist_tracks:** Attempt to add a track to a nonexistent playlist. Verify it raises an IntegrityError.

4. **Query correctness -- user_top_tracks:** Insert known stream data for a user (e.g., 5 streams of track A, 3 streams of track B, 1 stream of track C). Verify `user_top_tracks` returns them in the correct order with correct counts.

5. **Query correctness -- users_never_streamed:** Insert 2 users, add streams for only one. Verify `users_never_streamed` returns only the user with no streams.

---

## ACCEPTANCE CRITERIA

Run each of these commands and verify the expected output:

### 1. Tables exist with proper foreign keys
```sql
-- Run in psql or your SQL client
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```
**Expected:** At least these tables: `albums`, `artists`, `playlist_tracks`, `playlists`, `streams`, `tracks`, `users`

```sql
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name;
```
**Expected:** Foreign keys from `streams.user_id → users.user_id`, `streams.track_id → tracks.track_id`, `playlists.user_id → users.user_id`, `playlist_tracks.playlist_id → playlists.playlist_id`, `playlist_tracks.track_id → tracks.track_id`

### 2. Stream loader works
```bash
python stream_loader.py
```
**Expected:** Output like:
```
Generated test CSV: test_streams.csv (1000+ rows with duplicates)
Processing test_streams.csv...
  Inserted 800 rows (batch 1)...
  ...
Done: 950 rows inserted, 50 duplicates skipped (1000 total in file)
```
The exact numbers depend on your generated data, but duplicates must be > 0 and total must match the CSV line count.

### 3. Queries return correct results
```bash
python queries.py
```
**Expected:** Each of the 5 queries prints formatted results. Verify:
- `user_top_tracks` returns tracks ordered by play count descending
- `most_streamed_artist` returns exactly one artist
- `playlist_contents` shows tracks in position order with artist/album names
- `users_never_streamed` returns only users with zero streams (or empty if all users have streamed)
- `tracks_in_most_playlists` returns tracks ordered by playlist count descending

### 4. Tests pass
```bash
pytest test_soundstream.py -v
```
**Expected:** At least 5 tests, all passing:
```
test_soundstream.py::test_stream_deduplication PASSED
test_soundstream.py::test_stream_fk_enforcement PASSED
test_soundstream.py::test_playlist_track_fk_enforcement PASSED
test_soundstream.py::test_user_top_tracks_order PASSED
test_soundstream.py::test_users_never_streamed PASSED
```
