# Week 4, Session 3: Materialized Views & Aggregate Tables
**Domain:** Social media engagement metrics
**Concepts:** Views vs materialized views, REFRESH, aggregate tables, pre-computation patterns, CONCURRENTLY refresh
**Prerequisites:** PostgreSQL running in Docker, Python with psycopg2, comfort with JOINs and GROUP BY

---

## FOLLOW-ALONG

### Step 1: Create the social media database

We need multiple related tables to make the aggregation patterns meaningful. Posts, likes, comments, and follows give us rich engagement data to roll up.

```sql
-- File: social_media/schema.sql

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    -- We'll aggregate by date frequently, so storing created_at as TIMESTAMP
    -- lets us truncate to day/week/month as needed
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS likes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    post_id INTEGER NOT NULL REFERENCES posts(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    -- A user can only like a post once. This constraint prevents
    -- double-counting in our engagement metrics.
    UNIQUE (user_id, post_id)
);

CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    post_id INTEGER NOT NULL REFERENCES posts(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS follows (
    id SERIAL PRIMARY KEY,
    follower_id INTEGER NOT NULL REFERENCES users(id),
    following_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    -- Can't follow yourself, and can't follow the same person twice
    UNIQUE (follower_id, following_id),
    CHECK (follower_id != following_id)
);
```

### Step 2: Load seed data

We need enough data to make the performance difference between raw queries and materialized views visible.

```python
# File: social_media/generate_data.py

"""
Generate seed data for the social media engagement database.
We create ~50 users, ~5000 posts, ~20000 likes, ~8000 comments,
and ~500 follows -- enough to see meaningful engagement patterns
and measurable performance differences.
"""

import psycopg2
import random
from datetime import datetime, timedelta

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "postgres",
}

NUM_USERS = 50
NUM_POSTS = 5000
NUM_LIKES = 20000
NUM_COMMENTS = 8000
NUM_FOLLOWS = 500


def generate_data():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # --- Users ---
    print("Creating users...")
    for i in range(1, NUM_USERS + 1):
        cur.execute(
            "INSERT INTO users (username, display_name, created_at) VALUES (%s, %s, %s)",
            (f"user_{i}", f"User {i}", datetime(2023, 1, 1) + timedelta(days=random.randint(0, 200))),
        )
    conn.commit()

    # --- Posts: spread over 12 months so we can do time-based aggregations ---
    print("Creating posts...")
    base_date = datetime(2024, 1, 1)
    for i in range(NUM_POSTS):
        user_id = random.randint(1, NUM_USERS)
        # Some users post more than others -- this creates realistic skew
        # in engagement metrics (power law distribution)
        created_at = base_date + timedelta(
            days=random.randint(0, 365),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        cur.execute(
            "INSERT INTO posts (user_id, content, created_at) VALUES (%s, %s, %s)",
            (user_id, f"Post content #{i+1} from user {user_id}", created_at),
        )
    conn.commit()

    # --- Likes: randomly distributed with uniqueness constraint ---
    print("Creating likes...")
    likes_added = 0
    attempts = 0
    while likes_added < NUM_LIKES and attempts < NUM_LIKES * 3:
        user_id = random.randint(1, NUM_USERS)
        post_id = random.randint(1, NUM_POSTS)
        days_after_post = random.randint(0, 30)
        try:
            cur.execute(
                "INSERT INTO likes (user_id, post_id, created_at) VALUES (%s, %s, %s)",
                (user_id, post_id, base_date + timedelta(days=random.randint(0, 365) + days_after_post)),
            )
            conn.commit()
            likes_added += 1
        except psycopg2.errors.UniqueViolation:
            # Same user already liked this post -- skip
            conn.rollback()
        attempts += 1
    print(f"  Added {likes_added} likes")

    # --- Comments ---
    print("Creating comments...")
    for i in range(NUM_COMMENTS):
        user_id = random.randint(1, NUM_USERS)
        post_id = random.randint(1, NUM_POSTS)
        cur.execute(
            "INSERT INTO comments (user_id, post_id, content, created_at) VALUES (%s, %s, %s, %s)",
            (user_id, post_id, f"Comment #{i+1}", base_date + timedelta(days=random.randint(0, 365))),
        )
    conn.commit()

    # --- Follows ---
    print("Creating follows...")
    follows_added = 0
    attempts = 0
    while follows_added < NUM_FOLLOWS and attempts < NUM_FOLLOWS * 3:
        follower = random.randint(1, NUM_USERS)
        following = random.randint(1, NUM_USERS)
        if follower == following:
            attempts += 1
            continue
        try:
            cur.execute(
                "INSERT INTO follows (follower_id, following_id, created_at) VALUES (%s, %s, %s)",
                (follower, following, base_date + timedelta(days=random.randint(0, 365))),
            )
            conn.commit()
            follows_added += 1
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
        attempts += 1
    print(f"  Added {follows_added} follows")

    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    generate_data()
```

Run the script. Verify: `SELECT COUNT(*) FROM posts;` → ~5000, `SELECT COUNT(*) FROM likes;` → ~20000.

### Step 3: The problem — slow engagement queries on raw data

This is the query we'd run to build a "user engagement dashboard." It touches multiple tables with aggregations.

```sql
-- File: social_media/queries.sql

-- Time this query: it joins 4 tables and aggregates everything.
-- On 5K posts + 20K likes + 8K comments, it's already noticeable.
-- Imagine this on millions of rows.
EXPLAIN ANALYZE
SELECT
    u.username,
    u.display_name,
    COUNT(DISTINCT p.id) AS total_posts,
    COALESCE(SUM(post_likes.like_count), 0) AS total_likes_received,
    COALESCE(SUM(post_comments.comment_count), 0) AS total_comments_received,
    -- Engagement rate: (likes + comments) / posts. Guard against division by zero.
    CASE
        WHEN COUNT(DISTINCT p.id) > 0 THEN
            ROUND(
                (COALESCE(SUM(post_likes.like_count), 0) + COALESCE(SUM(post_comments.comment_count), 0))::numeric
                / COUNT(DISTINCT p.id),
                2
            )
        ELSE 0
    END AS engagement_rate
FROM users u
LEFT JOIN posts p ON u.id = p.user_id
LEFT JOIN (
    SELECT post_id, COUNT(*) AS like_count FROM likes GROUP BY post_id
) post_likes ON p.id = post_likes.post_id
LEFT JOIN (
    SELECT post_id, COUNT(*) AS comment_count FROM comments GROUP BY post_id
) post_comments ON p.id = post_comments.post_id
GROUP BY u.id, u.username, u.display_name
ORDER BY total_likes_received DESC;
```

Note the execution time. We'll beat it by orders of magnitude.

### Step 4: Regular view — does NOT help performance

A regular view is just a saved query. PostgreSQL re-executes the underlying query every time you SELECT from the view. It helps readability but not performance.

```sql
-- A view stores the query definition, NOT the results.
-- Every time you query this view, PostgreSQL runs the full join+aggregate.
CREATE OR REPLACE VIEW user_engagement AS
SELECT
    u.id AS user_id,
    u.username,
    u.display_name,
    COUNT(DISTINCT p.id) AS total_posts,
    COALESCE(SUM(post_likes.like_count), 0) AS total_likes_received,
    COALESCE(SUM(post_comments.comment_count), 0) AS total_comments_received,
    CASE
        WHEN COUNT(DISTINCT p.id) > 0 THEN
            ROUND(
                (COALESCE(SUM(post_likes.like_count), 0) + COALESCE(SUM(post_comments.comment_count), 0))::numeric
                / COUNT(DISTINCT p.id),
                2
            )
        ELSE 0
    END AS engagement_rate
FROM users u
LEFT JOIN posts p ON u.id = p.user_id
LEFT JOIN (SELECT post_id, COUNT(*) AS like_count FROM likes GROUP BY post_id) post_likes ON p.id = post_likes.post_id
LEFT JOIN (SELECT post_id, COUNT(*) AS comment_count FROM comments GROUP BY post_id) post_comments ON p.id = post_comments.post_id
GROUP BY u.id, u.username, u.display_name;

-- This is NOT faster -- it runs the same query under the hood:
EXPLAIN ANALYZE
SELECT * FROM user_engagement ORDER BY total_likes_received DESC;
```

Compare the execution time. It should be roughly the same as the raw query.

### Step 5: Materialized view — pre-computed results

A materialized view stores the query's **results** on disk. Querying it is as fast as querying a regular table. The tradeoff: results are stale until you explicitly refresh.

```sql
-- MATERIALIZED VIEW stores the result set physically on disk.
-- The query runs ONCE at creation time (and each REFRESH), not on every SELECT.
CREATE MATERIALIZED VIEW mv_daily_post_metrics AS
SELECT
    DATE_TRUNC('day', p.created_at)::date AS post_date,
    COUNT(p.id) AS posts_created,
    COALESCE(SUM(like_counts.likes), 0) AS total_likes,
    COALESCE(SUM(comment_counts.comments), 0) AS total_comments,
    -- Average engagement per post that day
    CASE
        WHEN COUNT(p.id) > 0 THEN
            ROUND(
                (COALESCE(SUM(like_counts.likes), 0) + COALESCE(SUM(comment_counts.comments), 0))::numeric
                / COUNT(p.id),
                2
            )
        ELSE 0
    END AS avg_engagement_per_post
FROM posts p
LEFT JOIN (
    SELECT post_id, COUNT(*) AS likes FROM likes GROUP BY post_id
) like_counts ON p.id = like_counts.post_id
LEFT JOIN (
    SELECT post_id, COUNT(*) AS comments FROM comments GROUP BY post_id
) comment_counts ON p.id = comment_counts.post_id
GROUP BY DATE_TRUNC('day', p.created_at)::date
ORDER BY post_date;

-- Querying the materialized view is dramatically faster because
-- it's reading from a pre-computed table, not re-running all those joins.
EXPLAIN ANALYZE
SELECT * FROM mv_daily_post_metrics WHERE post_date >= '2024-06-01';
```

Compare the execution time to Step 3. The materialized view should be 10-100x faster.

### Step 6: Refreshing the materialized view

Data changes constantly. The materialized view doesn't know about new posts, likes, or comments until you tell it to re-compute.

```sql
-- Standard refresh: locks the view during refresh (no reads allowed).
-- Fine for low-traffic scenarios or scheduled off-peak refreshes.
REFRESH MATERIALIZED VIEW mv_daily_post_metrics;

-- To use CONCURRENTLY (allows reads during refresh), you MUST have
-- a unique index on the materialized view. Without it, PostgreSQL errors out.
CREATE UNIQUE INDEX idx_mv_daily_post_date ON mv_daily_post_metrics (post_date);

-- Now this works: readers can query stale data while refresh runs in background.
-- Tradeoff: CONCURRENTLY is slower than a standard refresh because it
-- builds a new copy and swaps it in atomically.
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_post_metrics;
```

### Step 7: Aggregate table — permanent pre-computation

Sometimes you want a permanent table (not a view) that stores pre-aggregated data. This is common for monthly/weekly summaries that never change once the period is over.

```sql
-- An aggregate table is a regular table that stores pre-computed summaries.
-- Unlike a materialized view, you control exactly when and how data is inserted.
-- This is the pattern data warehouses use for summary tables.
CREATE TABLE IF NOT EXISTS monthly_engagement_summary (
    month DATE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    posts_created INTEGER NOT NULL DEFAULT 0,
    likes_received INTEGER NOT NULL DEFAULT 0,
    comments_received INTEGER NOT NULL DEFAULT 0,
    followers_gained INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (month, user_id)  -- One row per user per month
);

-- Populate it with a single INSERT...SELECT. This runs the heavy query
-- ONCE and stores the results permanently.
INSERT INTO monthly_engagement_summary (month, user_id, posts_created, likes_received, comments_received, followers_gained)
SELECT
    DATE_TRUNC('month', p.created_at)::date AS month,
    p.user_id,
    COUNT(DISTINCT p.id) AS posts_created,
    COALESCE(SUM(like_counts.likes), 0) AS likes_received,
    COALESCE(SUM(comment_counts.comments), 0) AS comments_received,
    COALESCE(follower_counts.gained, 0) AS followers_gained
FROM posts p
LEFT JOIN (
    SELECT post_id, COUNT(*) AS likes FROM likes GROUP BY post_id
) like_counts ON p.id = like_counts.post_id
LEFT JOIN (
    SELECT post_id, COUNT(*) AS comments FROM comments GROUP BY post_id
) comment_counts ON p.id = comment_counts.post_id
LEFT JOIN (
    SELECT
        following_id AS user_id,
        DATE_TRUNC('month', created_at)::date AS month,
        COUNT(*) AS gained
    FROM follows
    GROUP BY following_id, DATE_TRUNC('month', created_at)::date
) follower_counts ON p.user_id = follower_counts.user_id
    AND DATE_TRUNC('month', p.created_at)::date = follower_counts.month
GROUP BY DATE_TRUNC('month', p.created_at)::date, p.user_id, follower_counts.gained
ON CONFLICT (month, user_id) DO UPDATE SET
    posts_created = EXCLUDED.posts_created,
    likes_received = EXCLUDED.likes_received,
    comments_received = EXCLUDED.comments_received,
    followers_gained = EXCLUDED.followers_gained;

-- Querying the aggregate table is instant -- it's just a simple table scan
-- on a small table (50 users * 12 months = ~600 rows).
EXPLAIN ANALYZE
SELECT
    month,
    SUM(posts_created) AS total_posts,
    SUM(likes_received) AS total_likes,
    SUM(comments_received) AS total_comments
FROM monthly_engagement_summary
GROUP BY month
ORDER BY month;
```

### Step 8: Refresh logic in Python

In production, materialized views are refreshed on a schedule. Here's a simple Python script that does this and logs timing.

```python
# File: social_media/refresh_views.py

"""
Refresh all materialized views and log the time taken.
In production, this would be called by a scheduler (cron, Airflow, etc.)
on a cadence appropriate for your data freshness requirements.
"""

import psycopg2
import time
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "postgres",
}

# List all materialized views to refresh.
# In a real system, you might query pg_matviews to discover these dynamically.
MATERIALIZED_VIEWS = [
    "mv_daily_post_metrics",
]


def refresh_all_views():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True  # REFRESH MATERIALIZED VIEW can't run inside a transaction

    for view_name in MATERIALIZED_VIEWS:
        print(f"[{datetime.now().isoformat()}] Refreshing {view_name}...")
        start = time.time()

        with conn.cursor() as cur:
            # Use CONCURRENTLY if the view has a unique index,
            # so reads aren't blocked during refresh.
            try:
                cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
                method = "CONCURRENTLY"
            except psycopg2.errors.ObjectNotInPrerequisiteState:
                # No unique index -- fall back to standard refresh
                conn.rollback()  # Clear the error state
                cur.execute(f"REFRESH MATERIALIZED VIEW {view_name}")
                method = "standard"

        elapsed = time.time() - start
        print(f"  Done ({method}) in {elapsed:.2f}s")

    conn.close()
    print(f"[{datetime.now().isoformat()}] All views refreshed.")


if __name__ == "__main__":
    refresh_all_views()
```

Run this and verify the output shows timing for each view refresh.

---

## INDEPENDENT

You have 15-20 minutes. Write all three components in the `social_media/` directory.

### Task 1: Materialized view for "trending posts"

Create a materialized view called `mv_trending_posts` that identifies the most-engaged posts in the last 24 hours (use a relative window: `created_at >= NOW() - INTERVAL '24 hours'` for likes and comments, but include all posts from the last 7 days as candidates). Each row should contain the post ID, the author's username, the post content (truncated to 100 characters), the number of likes, the number of comments, and a total engagement score (likes + comments). Order by engagement score descending. Create a unique index on the view so it can be refreshed concurrently.

**Expected output columns:** `post_id`, `username`, `content_preview`, `recent_likes`, `recent_comments`, `engagement_score`

### Task 2: Aggregate table for follower growth by week

Create a table called `weekly_follower_growth` with columns: `week_start` (date), `user_id`, `new_followers` (count of follows created that week), `total_followers` (running total of followers as of end of that week). Write an INSERT...SELECT that populates this table. The running total should be computed using a window function within the INSERT query.

**Expected output when queried:** Each user-week combination shows how many new followers they gained and their cumulative total.

### Task 3: Python refresh function

Extend the `refresh_views.py` script from the follow-along. Add `mv_trending_posts` to the list of views to refresh. Also add a function that repopulates the `weekly_follower_growth` aggregate table (truncate and re-insert). The script should:
- Log the start time, end time, and duration for each refresh/repopulation
- Print a summary at the end showing total time across all operations
- Handle errors gracefully (if one view fails, continue with the others and report the failure at the end)

---

## REVIEW CHECKLIST

When reviewing the student's independent work, check for:

- [ ] **Task 1:** Materialized view is created with `CREATE MATERIALIZED VIEW`. Engagement is calculated from likes and comments. A unique index exists on the view. Results are ordered by engagement score.
- [ ] **Task 2:** The `weekly_follower_growth` table has correct columns and types. `INSERT...SELECT` populates it. A window function (`SUM() OVER (PARTITION BY user_id ORDER BY week_start)`) computes the running total.
- [ ] **Task 3:** Python script handles both materialized views and the aggregate table. Timing is logged for each operation. Error handling wraps each operation independently (one failure doesn't crash the whole script). Summary is printed at the end.
- [ ] All SQL creates/queries run without errors.
- [ ] Student ran the Python refresh script and showed the output.

---

## QUIZ

Answer all 15 questions. The session quiz will use 10 of these; extras are reserved for retries.

---

**Q1 (Multiple Choice).** What is the main difference between a regular view and a materialized view?

A) Regular views are faster to query
B) Materialized views store query results on disk; regular views re-execute the query each time
C) Regular views can be indexed; materialized views cannot
D) Materialized views update automatically when underlying data changes

---

**Q2 (Short Answer).** Why must you create a unique index on a materialized view before using `REFRESH MATERIALIZED VIEW CONCURRENTLY`?

---

**Q3 (Multiple Choice).** What happens when you query a materialized view after the underlying data has changed but before a REFRESH?

A) You get an error
B) You get the stale (pre-change) data
C) PostgreSQL automatically refreshes and returns fresh data
D) The query blocks until the data is refreshed

---

**Q4 (Spot the Bug).** A developer writes:

```sql
CREATE MATERIALIZED VIEW mv_stats AS
SELECT user_id, COUNT(*) AS post_count FROM posts GROUP BY user_id;

REFRESH MATERIALIZED VIEW CONCURRENTLY mv_stats;
```

The REFRESH fails. Why?

---

**Q5 (Short Answer).** Explain the difference between a materialized view and an aggregate table. When would you choose one over the other?

---

**Q6 (Multiple Choice).** What does `REFRESH MATERIALIZED VIEW CONCURRENTLY` do differently from a standard refresh?

A) It refreshes only the rows that changed
B) It allows reads on the old data while the refresh is running
C) It runs the refresh in a background process
D) It updates the view incrementally without re-running the full query

---

**Q7 (What does this code output?).** You create a materialized view:

```sql
CREATE MATERIALIZED VIEW mv_count AS SELECT COUNT(*) AS n FROM orders;
```

At creation, orders has 100 rows. You insert 50 more rows. What does `SELECT n FROM mv_count;` return?

---

**Q8 (Short Answer).** Name two disadvantages of materialized views compared to querying raw tables.

---

**Q9 (Multiple Choice).** Which statement about aggregate tables is TRUE?

A) Aggregate tables are a special PostgreSQL feature
B) Aggregate tables automatically stay in sync with source data
C) Aggregate tables are regular tables populated with pre-computed summaries
D) Aggregate tables cannot have indexes

---

**Q10 (Spot the Bug).** This Python refresh script has a problem:

```python
conn = psycopg2.connect(**DB_CONFIG)
with conn.cursor() as cur:
    cur.execute("REFRESH MATERIALIZED VIEW mv_metrics")
conn.commit()
```

What could go wrong, and how would you fix it?

---

**Q11 (Short Answer).** A materialized view takes 30 seconds to refresh. During that time, users query the view. Describe the behavior difference between `REFRESH` and `REFRESH CONCURRENTLY`.

---

**Q12 (Multiple Choice).** You have a dashboard that shows "top posts this month." The data only needs to be accurate within 1 hour. Which approach is BEST?

A) Query the raw tables directly every time the dashboard loads
B) Use a regular view
C) Use a materialized view refreshed every hour
D) Use a materialized view refreshed every minute

---

**Q13 (Short Answer).** What is the `ON CONFLICT ... DO UPDATE` pattern (upsert), and why is it useful when populating aggregate tables?

---

**Q14 (What does this code output?).** You have a materialized view with a unique index on `(user_id)`:

```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_user_stats;
-- Takes 5 seconds
```

Meanwhile, another session runs:

```sql
SELECT * FROM mv_user_stats WHERE user_id = 42;
```

What happens to the SELECT?

---

**Q15 (Multiple Choice).** When should you NOT use a materialized view?

A) When the underlying query is expensive and data freshness isn't critical
B) When the data must always be 100% up to date
C) When many users query the same aggregation
D) When you want to add indexes to speed up queries on the aggregated data

---

### ANSWER KEY

**Q1:** B -- Materialized views store query results physically on disk. Regular views just store the query definition and re-execute it every time they're queried.

**Q2:** CONCURRENTLY works by building a new version of the materialized view alongside the old one, then swapping them. To identify which rows changed (for the diff), PostgreSQL needs a unique index to match rows between the old and new versions. Without it, there's no reliable way to do the swap without blocking reads.

**Q3:** B -- You get stale data. Materialized views don't auto-refresh; they return whatever was computed at the last REFRESH (or at creation time).

**Q4:** There is no unique index on the materialized view. `REFRESH CONCURRENTLY` requires a unique index to identify rows for the diff-and-swap process. Fix: `CREATE UNIQUE INDEX ON mv_stats (user_id);` before the concurrent refresh.

**Q5:** A materialized view is managed by PostgreSQL -- you define a query, and PG stores the results and handles refresh via `REFRESH MATERIALIZED VIEW`. An aggregate table is a regular table that you populate and maintain yourself with INSERT/UPDATE/DELETE. Choose a materialized view when you want simplicity and the whole dataset refreshes together. Choose an aggregate table when you need incremental updates (e.g., only recompute the current month), custom upsert logic, or when different rows have different refresh schedules.

**Q6:** B -- CONCURRENTLY allows existing queries to continue reading the old (stale) data while the new version is being computed. A standard REFRESH acquires an exclusive lock that blocks all reads until it completes.

**Q7:** 100 -- The materialized view stores the result from creation time. The 50 new rows are not reflected until you run `REFRESH MATERIALIZED VIEW mv_count`.

**Q8:** (Any two of:) 1) Data staleness -- results don't reflect changes until refreshed. 2) Storage overhead -- the materialized results consume disk space. 3) Refresh cost -- running the full query periodically can be expensive. 4) Maintenance burden -- you need to schedule and monitor refreshes.

**Q9:** C -- Aggregate tables are just regular tables. There's no special PostgreSQL feature; it's a design pattern where you populate a normal table with pre-computed summaries using INSERT...SELECT or similar.

**Q10:** `REFRESH MATERIALIZED VIEW` cannot run inside a transaction block (when autocommit is off, which is psycopg2's default). The `conn.commit()` at the end won't help because the REFRESH needs autocommit. Fix: set `conn.autocommit = True` before executing the refresh.

**Q11:** Standard `REFRESH` acquires an exclusive lock on the materialized view. For 30 seconds, all SELECT queries against the view are blocked -- they queue up and wait. `REFRESH CONCURRENTLY` allows reads to continue returning stale data while the new version is computed in the background. When the new version is ready, it's swapped in atomically.

**Q12:** C -- A materialized view refreshed every hour matches the freshness requirement and avoids hitting the raw tables on every dashboard load. Option A is wasteful (expensive query on every load). Option B provides no performance benefit. Option D is over-refreshing relative to the 1-hour tolerance.

**Q13:** `ON CONFLICT ... DO UPDATE` (upsert) attempts an INSERT and, if a uniqueness conflict occurs, updates the existing row instead. It's useful for aggregate tables because you can re-run the population query idempotently -- if a summary row for (month, user_id) already exists, it gets updated rather than causing a duplicate key error. This makes incremental updates safe and repeatable.

**Q14:** The SELECT returns immediately with the old (pre-refresh) data. That's the entire point of CONCURRENTLY -- readers are not blocked. Once the 5-second refresh completes, subsequent SELECTs see the new data.

**Q15:** B -- If data must always be 100% up to date (zero staleness tolerance), a materialized view is the wrong tool because it always serves stale data between refreshes. Use a regular view or query the tables directly instead.
