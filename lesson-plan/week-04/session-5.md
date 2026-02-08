# Week 4, Session 5: SoundStream -- Analytics & Performance

**Branch:** cumulative
**Builds on:** Week 3 Session 5 (API layer + Docker Compose)
**Concepts applied:** Window functions, CTEs, indexes, materialized views, migrations

---

## BRIEF

This week you learned advanced SQL: window functions, CTEs, query optimization with indexes, materialized views, and database migrations. Now you'll apply all of these to SoundStream.

You will:
1. Write 5 analytics queries using window functions and CTEs
2. Optimize them with indexes
3. Create materialized views for expensive queries
4. Add a migration system for schema evolution

By the end, SoundStream will have a performant analytics layer on top of the streaming data you've been collecting since Week 2.

---

## REQUIREMENTS

### 1. Analytics Queries (5 queries using window functions and CTEs)

Create a file `soundstream/analytics/queries.py` (or `.sql`) with these queries:

**Query 1: Trending Tracks**
Return the top 20 most-streamed tracks in the last 7 days. Include: track title, artist name, stream count this week, and rank. Use ROW_NUMBER() or RANK() partitioned appropriately.

**Query 2: Listener Retention**
Compare this week's active users to last week's. For each user who was active both weeks, show their stream count for each week and the change. Use LAG() to get the previous week's count. Also compute overall retention rate (users active both weeks / users active last week).

**Query 3: Artist Revenue Report**
Calculate revenue per artist assuming $0.004 per stream. Show: artist name, total streams, total revenue, and a running total of revenue ordered by total streams descending. Use SUM() OVER() for the running total. Use a CTE for the base aggregation.

**Query 4: Playlist Popularity**
Rank tracks by how many distinct playlists they appear in. Show: track title, artist name, playlist count, and dense rank. Use DENSE_RANK(). Only show top 20.

**Query 5: User Listening Diversity**
For each user, count how many unique genres they've listened to (through track -> album -> artist -> genre). Compute the percentile rank of each user's genre diversity using PERCENT_RANK(). Show: username, unique genres, percentile rank.

### 2. Index Optimization

For each of the 5 queries above:
- Run EXPLAIN ANALYZE before adding indexes
- Add appropriate indexes (single-column, composite, or partial as needed)
- Run EXPLAIN ANALYZE after and verify improvement
- Create the indexes in a file `soundstream/analytics/indexes.sql`

Target: each query should run in under 100ms on the existing dataset.

### 3. Materialized Views

Create 2 materialized views in `soundstream/analytics/materialized_views.sql`:

**`mv_trending_tracks`**: Pre-computed version of Query 1 (trending tracks), refreshed on demand.

**`mv_artist_revenue`**: Pre-computed version of Query 3 (artist revenue summary), refreshed on demand.

Each materialized view should have an appropriate index for common access patterns.

### 4. Materialized View Refresh Script

Create `soundstream/analytics/refresh_views.py`:
- Refreshes both materialized views
- Logs the refresh time for each view
- Can be called from the command line: `python -m soundstream.analytics.refresh_views`

### 5. Migration System

Create a simple migration system in `soundstream/migrations/`:

**Migration runner** (`soundstream/migrations/runner.py`):
- Tracks applied migrations in a `schema_migrations` table (version, applied_at)
- Applies pending migrations in order
- Supports rollback of the last migration
- Can be run from command line: `python -m soundstream.migrations.runner migrate` and `python -m soundstream.migrations.runner rollback`

**Migration 001** (`soundstream/migrations/001_add_stream_quality.sql`):
- UP: Add a `quality` column (VARCHAR(10), default 'standard') to the `streams` table and a `play_count` column (INTEGER, default 0) to the `tracks` table
- DOWN: Remove both columns

### 6. Tests

Add tests to ensure:
- Each analytics query returns results (not empty)
- Materialized views contain data after refresh
- Migration applies and rolls back cleanly
- Indexes exist after running the index script

---

## ACCEPTANCE CRITERIA

Run each of these and verify:

1. **Analytics queries work:**
   - Run each of the 5 queries and confirm non-empty, correct results
   - `EXPLAIN ANALYZE` on each shows execution time < 100ms

2. **Materialized views:**
   - `SELECT COUNT(*) FROM mv_trending_tracks;` returns rows
   - `SELECT COUNT(*) FROM mv_artist_revenue;` returns rows
   - `python -m soundstream.analytics.refresh_views` completes without errors and logs timing

3. **Migrations:**
   - `python -m soundstream.migrations.runner migrate` adds the new columns
   - Verify: `\d streams` shows `quality` column, `\d tracks` shows `play_count` column
   - `python -m soundstream.migrations.runner rollback` removes them
   - Verify: columns are gone
   - Re-run migrate to leave schema in the migrated state

4. **Tests pass:**
   - `pytest` runs with all tests passing (including new analytics tests and previous Week 3 tests)

5. **No regressions:**
   - All API endpoints from Week 3 still work
   - `docker compose up` still starts cleanly
