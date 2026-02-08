# Week 3, Session 3: Docker Compose
**Domain:** Blog platform
**Concepts:** Docker Compose, multi-container apps, service networking, volumes, environment variables, health checks
**Prerequisites:** Docker basics (Week 1), FastAPI + PostgreSQL (sessions 1-2)

---

## FOLLOW-ALONG

### Step 1: Project Structure

```bash
mkdir blog-platform && cd blog-platform
mkdir app
```

We'll create four files: the FastAPI application, its dependencies, a Dockerfile, and a Docker Compose configuration.

### Step 2: Application Code

```python
# blog-platform/app/main.py

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="Blog Platform API", version="1.0.0")


# --- Configuration from Environment Variables ---
# Hardcoding database credentials is a security and portability problem.
# Environment variables let the SAME code run in different environments
# (dev, staging, production) just by changing the config.
# os.environ.get() reads the variable, with a fallback default for local dev.
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "5432")),
    "dbname": os.environ.get("DB_NAME", "blog"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "postgres"),
}


@contextmanager
def get_db():
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(300) NOT NULL,
                    content TEXT NOT NULL,
                    author VARCHAR(100) NOT NULL,
                    published BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS comments (
                    id SERIAL PRIMARY KEY,
                    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                    author VARCHAR(100) NOT NULL,
                    body TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)


@app.on_event("startup")
def startup():
    init_db()


# --- Models ---

class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1, max_length=100)
    published: bool = False


class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    author: str
    published: bool
    created_at: str


class CommentCreate(BaseModel):
    author: str = Field(..., min_length=1, max_length=100)
    body: str = Field(..., min_length=1)


class CommentResponse(BaseModel):
    id: int
    post_id: int
    author: str
    body: str
    created_at: str


# --- Routes ---

@app.get("/health")
def health_check():
    """Health endpoint for Docker and load balancers to verify the app is alive.
    Checks both the app AND the database connection -- if either is down,
    the health check fails and Docker can restart the container."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unhealthy: {e}")


@app.post("/posts", response_model=PostResponse, status_code=201)
def create_post(post: PostCreate):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO posts (title, content, author, published)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (post.title, post.content, post.author, post.published),
            )
            created = cur.fetchone()
            created["created_at"] = created["created_at"].isoformat()
            return created


@app.get("/posts", response_model=list[PostResponse])
def list_posts(published: Optional[bool] = None):
    with get_db() as conn:
        with conn.cursor() as cur:
            query = "SELECT * FROM posts"
            params = []
            if published is not None:
                query += " WHERE published = %s"
                params.append(published)
            query += " ORDER BY created_at DESC"
            cur.execute(query, params)
            posts = cur.fetchall()
            for p in posts:
                p["created_at"] = p["created_at"].isoformat()
            return posts


@app.get("/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
            post = cur.fetchone()
            if not post:
                raise HTTPException(status_code=404, detail="Post not found")
            post["created_at"] = post["created_at"].isoformat()
            return post


@app.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=201)
def add_comment(post_id: int, comment: CommentCreate):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM posts WHERE id = %s", (post_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Post not found")

            cur.execute(
                """
                INSERT INTO comments (post_id, author, body)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (post_id, comment.author, comment.body),
            )
            created = cur.fetchone()
            created["created_at"] = created["created_at"].isoformat()
            return created


@app.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
def list_comments(post_id: int):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM posts WHERE id = %s", (post_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Post not found")

            cur.execute(
                "SELECT * FROM comments WHERE post_id = %s ORDER BY created_at",
                (post_id,),
            )
            comments = cur.fetchall()
            for c in comments:
                c["created_at"] = c["created_at"].isoformat()
            return comments
```

### Step 3: Requirements File

```
# blog-platform/app/requirements.txt
# Pinning versions prevents "it worked yesterday" problems.
# In production, use a lockfile (like uv.lock). For Docker,
# requirements.txt is the standard format pip understands.
fastapi==0.115.0
uvicorn==0.30.0
psycopg2-binary==2.9.9
```

### Step 4: Dockerfile

```dockerfile
# blog-platform/Dockerfile

# Start from a slim Python image. "slim" variants exclude build tools
# and docs, making the image ~100MB smaller. Use the full image if you
# need to compile C extensions.
FROM python:3.12-slim

# Set the working directory inside the container.
# All subsequent commands (COPY, RUN, CMD) are relative to this path.
WORKDIR /app

# Copy requirements FIRST, before the rest of the code.
# Docker caches each layer. If requirements.txt hasn't changed,
# Docker skips the pip install step on rebuild -- saving minutes.
# This is why we don't just COPY . . in one step.
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the application code. This layer changes frequently
# (every code edit), but the pip install layer above is cached.
COPY app/ .

# Document which port the container uses. This doesn't actually
# publish the port -- it's metadata for humans and tools.
EXPOSE 8000

# The command that runs when the container starts.
# 0.0.0.0 is critical -- without it, uvicorn only listens on localhost
# inside the container, which means nothing outside can reach it.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 5: Docker Compose Configuration

```yaml
# blog-platform/docker-compose.yml

# Docker Compose lets you define and run multi-container applications.
# Instead of managing each container separately, you describe the whole
# stack in one file and start everything with `docker compose up`.

services:
  # --- PostgreSQL Database ---
  db:
    image: postgres:16
    # Restart policy: if the container crashes, Docker restarts it.
    # "unless-stopped" means it restarts unless you explicitly stop it.
    restart: unless-stopped
    environment:
      # These environment variables are read by the official postgres image
      # to create the initial database and user on first startup.
      POSTGRES_DB: blog
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      # host:container -- expose PostgreSQL on the host so you can
      # connect with psql or a GUI tool for debugging.
      # In production, you'd remove this to keep the database internal.
      - "5433:5432"
    volumes:
      # Named volume for data persistence. Without this, your data
      # disappears when the container is removed.
      # Named volumes are managed by Docker and survive container recreation.
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      # Docker periodically runs this command to check if PostgreSQL is ready.
      # Other services can use `depends_on: condition: service_healthy`
      # to wait for the database before starting.
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s        # Check every 5 seconds
      timeout: 5s          # Give up after 5 seconds per check
      retries: 5           # Mark unhealthy after 5 consecutive failures
      start_period: 10s    # Grace period for initial startup

  # --- FastAPI Application ---
  app:
    # Build the image from the Dockerfile in the current directory.
    # Compose runs `docker build .` using the Dockerfile we wrote.
    build: .
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      # These variables are read by our app's DB_CONFIG.
      # DB_HOST is "db" -- the SERVICE NAME, not localhost.
      # Docker Compose creates a network where services can reach
      # each other by name. The app container resolves "db" to the
      # database container's IP address automatically.
      DB_HOST: db
      DB_PORT: "5432"
      DB_NAME: blog
      DB_USER: postgres
      DB_PASSWORD: postgres
    depends_on:
      db:
        # Wait for the database to be healthy before starting the app.
        # Without this, the app might start and crash because PostgreSQL
        # isn't ready yet. The condition uses the healthcheck we defined above.
        condition: service_healthy

# Named volumes are declared at the top level.
# Docker manages the storage location on the host filesystem.
volumes:
  pgdata:
```

### Step 6: Environment Variables File

```bash
# blog-platform/.env
# Docker Compose automatically reads this file.
# Variables here are available in docker-compose.yml with ${VAR_NAME} syntax.
# We're keeping it simple and hardcoding in the YAML for now,
# but in a real project you'd reference .env variables to keep
# secrets out of version control.
POSTGRES_DB=blog
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

**Important:** Add `.env` to your `.gitignore`. Credentials should never be committed to git.

### Step 7: Build and Run

```bash
# Build images and start all services in the background (-d = detached)
docker compose up --build -d

# Watch the logs to see both services starting
docker compose logs -f

# Wait until you see the FastAPI startup message, then Ctrl+C the logs
```

### Step 8: Test the Running Stack

```bash
# Health check -- verifies both the app and database are working
curl http://127.0.0.1:8000/health

# Create a post
curl -X POST http://127.0.0.1:8000/posts \
  -H "Content-Type: application/json" \
  -d '{"title": "My First Post", "content": "Hello from Docker!", "author": "student", "published": true}'

# List posts
curl http://127.0.0.1:8000/posts

# Add a comment
curl -X POST http://127.0.0.1:8000/posts/1/comments \
  -H "Content-Type: application/json" \
  -d '{"author": "reader", "body": "Great post!"}'

# Get comments
curl http://127.0.0.1:8000/posts/1/comments
```

### Step 9: Verify Data Persistence

```bash
# Stop and remove containers (but NOT volumes)
docker compose down

# Start again
docker compose up -d

# Your data is still there because of the named volume
curl http://127.0.0.1:8000/posts

# Compare: if you also remove volumes, data is gone
# docker compose down -v  (DON'T run this now -- just know the flag exists)
```

### Step 10: Useful Compose Commands

```bash
# See running containers and their status
docker compose ps

# View logs for a specific service
docker compose logs app
docker compose logs db

# Restart just one service (e.g., after code changes)
docker compose restart app

# Stop everything
docker compose down

# Stop everything AND delete the database volume (nuclear option)
docker compose down -v

# Rebuild after changing the Dockerfile or requirements
docker compose up --build -d
```

### Key Concepts Recap

| Concept | Example | Why It Matters |
|---------|---------|---------------|
| Service networking | `DB_HOST: db` | Containers find each other by service name, not IP |
| Named volumes | `pgdata:/var/lib/postgresql/data` | Data persists across container restarts |
| Health checks | `pg_isready` | Prevents app from starting before DB is ready |
| `depends_on` + condition | `service_healthy` | Orchestrates startup order |
| Build context | `build: .` | Compose builds your Dockerfile automatically |
| Port mapping | `"8000:8000"` | Exposes container ports to the host |
| Environment variables | `DB_HOST: db` | Configures app without changing code |

---

## INDEPENDENT

### What to Build

Add three enhancements to the blog platform's Docker Compose setup.

### Enhancement 1: Database Management UI

Add a third service to `docker-compose.yml` for a database management web UI. Use the `adminer` image (it's lightweight and requires zero configuration). It should be accessible on port 8080 of your host machine. Adminer needs to connect to the same database network, so think about which service it depends on and how it will find the database.

**Expected behavior:**
- After running `docker compose up -d`, visiting `http://localhost:8080` opens Adminer
- You can log in with your PostgreSQL credentials and browse the blog database tables
- The "server" field in Adminer should use the Docker service name of the database, not "localhost"

### Enhancement 2: Hot Reload with Bind Mount

Right now, changing a Python file requires rebuilding the Docker image (`docker compose up --build`). Add a bind mount that maps your local `app/` directory into the container, and modify the app service's command to include the `--reload` flag. This way, editing code on your host machine immediately takes effect in the running container.

**Expected behavior:**
- Start the stack with `docker compose up -d`
- Edit `app/main.py` on your host (e.g., change the API title)
- The change is visible immediately without rebuilding (check `/docs` in your browser)

Think about the difference between a bind mount (maps a host directory) and a named volume (managed by Docker). Bind mounts are specified with a path, like `./app:/app`, not a volume name.

### Enhancement 3: Environment-Specific Override File

Create a `docker-compose.dev.yml` file that overrides the base configuration for development. It should:
- Add the bind mount from Enhancement 2 (so the base file stays clean for production)
- Add the `--reload` flag to the app's command
- Expose PostgreSQL on port 5433 (so you can connect with local tools during development)

The base `docker-compose.yml` should work for production (no bind mounts, no reload, no exposed DB port). The dev override adds developer conveniences.

**Expected behavior:**
- Production: `docker compose up -d` uses only the base file
- Development: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d` adds dev features
- Both modes should work correctly without conflicts

### Clean Up

After testing, run `docker compose down` to stop everything. Use `docker compose down -v` only if you want to wipe the database.

---

## REVIEW CHECKLIST

- [ ] Adminer service added, accessible at port 8080, can connect to the database
- [ ] Bind mount correctly maps `./app` to `/app` in the container
- [ ] Hot reload works (code changes reflect without rebuild)
- [ ] `docker-compose.dev.yml` uses correct override syntax
- [ ] Base `docker-compose.yml` is clean (no dev-specific config)
- [ ] `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` works
- [ ] Student understands the difference between bind mounts and named volumes
- [ ] No credentials committed to git (`.env` in `.gitignore`)

---

## QUIZ

**Answer all 15 questions. You need 8/10 correct on any set of 10 to pass.**

---

**Q1 (Multiple Choice).** In Docker Compose, how does one service connect to another by name (e.g., the app connects to the database using hostname "db")?
- A) You must manually configure DNS in each container
- B) Docker Compose creates a shared network where service names resolve to container IPs
- C) Services share the host's network and use localhost
- D) You must link containers explicitly with the `links` directive

---

**Q2 (Short Answer).** What is the difference between a named volume and a bind mount? Give one use case for each.

---

**Q3 (Spot the Bug).** This Dockerfile has a performance problem. What is it?

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

---

**Q4 (Multiple Choice).** What does `docker compose down -v` do that `docker compose down` does not?
- A) Removes all Docker images from the system
- B) Removes named volumes, deleting persisted data
- C) Forces a rebuild of all images
- D) Stops containers more aggressively (sends SIGKILL)

---

**Q5 (What does this code output?).** Given this docker-compose.yml:

```yaml
services:
  app:
    build: .
    environment:
      DB_HOST: db
    depends_on:
      - db
  db:
    image: postgres:16
```

The app starts and tries to connect to the database immediately. What's likely to happen?

---

**Q6 (Short Answer).** Why does the uvicorn command in a Dockerfile use `--host 0.0.0.0` instead of the default `127.0.0.1`?

---

**Q7 (Multiple Choice).** What does the `EXPOSE 8000` instruction in a Dockerfile do?
- A) Publishes port 8000 to the host machine
- B) Documents that the container listens on port 8000 (metadata only)
- C) Opens port 8000 in the container's firewall
- D) Creates a port mapping between host and container

---

**Q8 (Spot the Bug).** This health check never succeeds. Why?

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 3
```

---

**Q9 (Short Answer).** Explain what `depends_on` with `condition: service_healthy` does. Why is it better than a plain `depends_on: - db`?

---

**Q10 (Multiple Choice).** What is the purpose of the `restart: unless-stopped` policy?
- A) Restarts the container only if it exits with a non-zero exit code
- B) Restarts the container whenever it stops, except when explicitly stopped by the user
- C) Prevents the container from ever being stopped
- D) Restarts the container exactly once after failure

---

**Q11 (What does this code output?).** Given this Dockerfile:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

You change one line in `app.py` and rebuild. Which layers does Docker re-run?

---

**Q12 (Multiple Choice).** In `docker-compose.yml`, what does `ports: ["5433:5432"]` mean?
- A) The container listens on 5433, the host exposes 5432
- B) The host's port 5433 maps to the container's port 5432
- C) Both host and container use ports 5433 and 5432
- D) Port 5433 is an alias for port 5432

---

**Q13 (Short Answer).** Why should you put `.env` in `.gitignore`? What could go wrong if you commit it?

---

**Q14 (Spot the Bug).** This override file is supposed to add a bind mount for hot reload, but it doesn't work. Why?

```yaml
# docker-compose.dev.yml
services:
  app:
    volumes:
      - ./app:/app
    command: uvicorn main:app --host 0.0.0.0 --reload
```

Hint: Think about what `command` expects in a compose file.

---

**Q15 (Multiple Choice).** When using `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`, how are the two files combined?
- A) The second file completely replaces the first
- B) The second file's values are merged into the first, overriding on conflict
- C) Docker randomly picks one file to use
- D) The files must have no overlapping service names

---

### ANSWER KEY

**Q1:** B) Docker Compose creates a shared network where service names resolve to container IPs. When you define services in a compose file, Docker creates a default network and registers each service name as a DNS entry pointing to that container's IP.

**Q2:** **Named volume** (e.g., `pgdata:/var/lib/postgresql/data`): Managed by Docker, stored in Docker's storage area, persists across container recreations. Best for database storage where you want Docker to manage the data. **Bind mount** (e.g., `./app:/app`): Maps a specific host directory into the container. Changes on either side are instantly visible to the other. Best for development (hot reload) where you want to edit files on the host and see changes in the container.

**Q3:** The `COPY . .` is done BEFORE `pip install`. This means every time any file changes (even a single line of Python code), Docker invalidates the cache for the COPY layer and re-runs pip install. Fix: copy `requirements.txt` first, run pip install, THEN copy the rest of the code. This way pip install is only re-run when dependencies change.

**Q4:** B) Removes named volumes, deleting persisted data. `docker compose down` stops and removes containers and networks. Adding `-v` also removes named volumes declared in the compose file, which means your database data is permanently deleted.

**Q5:** The app will likely crash with a connection error. `depends_on` without a health check condition only waits for the container to *start*, not for PostgreSQL to be *ready*. PostgreSQL takes several seconds to initialize, and the app tries to connect immediately. Fix: add a healthcheck to the db service and use `depends_on: db: condition: service_healthy`.

**Q6:** `127.0.0.1` (localhost) inside a container means "only accept connections from within this container." Other containers and the host can't reach it. `0.0.0.0` means "listen on all network interfaces," which includes the Docker bridge network that other containers and port mappings use.

**Q7:** B) Documents that the container listens on port 8000 (metadata only). `EXPOSE` does not actually publish the port. You still need `ports: ["8000:8000"]` in docker-compose.yml to make it accessible from the host. `EXPOSE` is documentation for people reading the Dockerfile.

**Q8:** The healthcheck uses `-U postgres` but the database was created with `POSTGRES_USER: admin`. `pg_isready` checks if PostgreSQL is accepting connections for the specified user. Since the user is "admin", the check should be `pg_isready -U admin`.

**Q9:** `depends_on` with `condition: service_healthy` waits for the dependency's healthcheck to pass before starting the dependent service. Plain `depends_on` only waits for the container to *start* (which can be milliseconds), not for the application inside to be *ready*. With databases, there's a significant gap between "container started" and "database accepting connections."

**Q10:** B) Restarts the container whenever it stops, except when explicitly stopped by the user (via `docker compose stop` or `docker compose down`). If the container crashes or the host reboots, Docker will restart it automatically.

**Q11:** Docker re-runs only `COPY . .` and `CMD` (the layers after the last unchanged layer). The `COPY requirements.txt`, `RUN pip install` layers are cached because `requirements.txt` didn't change. This is why we copy requirements separately -- to avoid reinstalling dependencies on every code change.

**Q12:** B) The host's port 5433 maps to the container's port 5432. Format is `host:container`. Requests to `localhost:5433` on your machine are forwarded to port 5432 inside the container.

**Q13:** `.env` files often contain passwords, API keys, and other secrets. If committed to git, those secrets are in the repository history permanently (even if you delete the file later). Anyone with access to the repo can read them. In production environments, secrets should come from a secrets manager, not files in version control.

**Q14:** This is actually a trick question -- the YAML itself is syntactically valid and should work. The most common real issue is that the bind mount `./app:/app` overlaps with the `COPY app/ .` in the Dockerfile, which is intentional (the bind mount overrides the copied files). If the student says it works, they're right. If there IS a problem, it's likely that the `command` needs to be specified as a list `["uvicorn", "main:app", "--host", "0.0.0.0", "--reload"]` for consistency, though the string form also works in Compose.

**Q15:** B) The second file's values are merged into the first, overriding on conflict. This is how override files work: Compose does a deep merge. New keys are added, existing keys are replaced. So `docker-compose.dev.yml` can add volumes and override the command while keeping all the base configuration (image, environment, ports, etc.).
