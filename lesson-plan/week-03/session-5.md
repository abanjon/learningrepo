# Week 3, Session 5: SoundStream -- API Layer & Containerization
**Branch:** cumulative
**Builds on:** Week 2 Session 5 (users, streams, playlists tables with streaming event ETL and dedup)
**Concepts applied:** FastAPI, database-backed endpoints, Docker Compose, API testing

---

## BRIEF

This week you built FastAPI apps, connected them to PostgreSQL, containerized them with Docker Compose, and tested them with TestClient. Now you'll apply all of that to SoundStream.

You will:
1. Create a FastAPI application that exposes SoundStream's data through API endpoints
2. Containerize the entire stack (PostgreSQL + API) with Docker Compose
3. Write tests to verify each endpoint works correctly

After this session, SoundStream will have a working API that external applications could consume -- this is how real data platforms expose their data to consumers.

---

## REQUIREMENTS

### Directory Structure

Create the following inside `soundstream/`:

```
soundstream/
├── api/
│   ├── main.py            # FastAPI application
│   ├── database.py        # Database connection helpers
│   ├── models.py          # Pydantic request/response models
│   └── requirements.txt   # Python dependencies for the API
├── tests/
│   └── test_api.py        # API tests
├── Dockerfile             # Builds the API image
├── docker-compose.yml     # PostgreSQL + API services
└── (existing files from Week 2)
```

### Database Connection

The API should connect to the same PostgreSQL database that has your existing SoundStream tables (artists, tracks, albums, users, streams, playlists). Use environment variables for all connection parameters. Use the context manager pattern from this week's sessions.

### API Endpoints

**1. GET /tracks/top**
- Query parameter: `limit` (optional, default 10, max 100)
- Returns the most-streamed tracks, ordered by stream count descending
- Each result should include: track name, artist name, album name, and total stream count
- This requires JOINing tracks with artists, albums, and aggregating the streams table

**2. GET /artists/{id}/stats**
- Returns stats for a single artist:
  - Artist name
  - Total stream count across all their tracks
  - Number of unique listeners (distinct user_ids from streams)
  - Their top track (most-streamed)
- Returns 404 if the artist ID doesn't exist

**3. GET /users/{id}/history**
- Query parameter: `limit` (optional, default 20, max 100)
- Returns a user's recent listening history, most recent first
- Each entry should include: track name, artist name, and when they streamed it
- Returns 404 if the user ID doesn't exist

**4. GET /search**
- Query parameter: `q` (required, minimum 1 character)
- Searches tracks and artists by name (case-insensitive, partial matching)
- Returns a JSON object with two lists: `tracks` (matching track names with artist) and `artists` (matching artist names)
- Returns 400 if `q` is empty or missing

**5. POST /streams**
- Records a new stream event
- Request body: `user_id`, `track_id`, `streamed_at` (ISO format timestamp)
- Validates that the user and track exist (404 if not)
- Prevents exact duplicate stream events (same user, same track, same timestamp) -- return 409 Conflict
- Returns 201 with the created stream record

**6. GET /health**
- Returns database connectivity status
- Used by Docker health checks

### Docker Compose Setup

- **db service:** PostgreSQL 16 with a named volume for data persistence, health check using `pg_isready`
- **api service:** Builds from the Dockerfile, depends on db with `service_healthy` condition, maps port 8000
- Environment variables configure the database connection (no hardcoded credentials in Python code)
- The database should be initialized with your existing SoundStream schema (you can use an init script mounted as a volume, or have the app create tables on startup)

### API Tests

Write at least 5 tests in `tests/test_api.py` using FastAPI's TestClient. At minimum, test:
- GET `/tracks/top` returns a list with track and artist names
- GET `/artists/{id}/stats` returns correct stat fields
- GET `/artists/{id}/stats` returns 404 for nonexistent artist
- POST `/streams` successfully creates a stream event
- POST `/streams` returns 409 for a duplicate stream event

You may need to seed test data in a fixture before running tests. If using an in-memory approach for tests, create a fixture that populates test data. If testing against the real database, use a test database that gets reset between runs.

---

## ACCEPTANCE CRITERIA

All of the following must pass for the session to be complete:

### 1. Docker Compose Starts Successfully
```bash
docker compose up --build -d
docker compose ps
```
Both the `db` and `api` services should show as "running" (and "healthy" if health checks are configured).

### 2. Health Check Passes
```bash
curl http://localhost:8000/health
```
Returns `{"status": "healthy", ...}` with a 200 status code.

### 3. API Endpoints Return Correct JSON
```bash
# Top tracks (should return a list with track/artist names and stream counts)
curl http://localhost:8000/tracks/top?limit=5

# Artist stats (use a valid artist ID from your seed data)
curl http://localhost:8000/artists/1/stats

# User history (use a valid user ID)
curl http://localhost:8000/users/1/history?limit=5

# Search
curl "http://localhost:8000/search?q=love"

# Record a stream (use valid user_id and track_id)
curl -X POST http://localhost:8000/streams \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "track_id": 1, "streamed_at": "2025-01-15T10:30:00"}'
```

Each endpoint should return well-structured JSON responses (not empty lists or error messages, assuming data exists).

### 4. Duplicate Stream Prevention
```bash
# Send the exact same stream event twice
curl -X POST http://localhost:8000/streams \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "track_id": 1, "streamed_at": "2025-01-15T10:30:00"}'
```
Second call returns 409 Conflict.

### 5. Tests Pass
```bash
uv run pytest tests/test_api.py -v
```
At least 5 tests, all passing.

### 6. Swagger Docs Accessible
Open `http://localhost:8000/docs` in a browser. All endpoints should be listed with their parameters and response schemas.
