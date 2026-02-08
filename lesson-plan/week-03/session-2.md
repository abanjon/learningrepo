# Week 3, Session 2: Database-Backed API Endpoints
**Domain:** Recipe collection API
**Concepts:** FastAPI + psycopg2, connection pooling, CRUD with real database, error handling in APIs, response models
**Prerequisites:** FastAPI basics (session 1), PostgreSQL running in Docker (Week 1), SQL JOINs (Week 2)

---

## FOLLOW-ALONG

### Step 1: Project Setup

```bash
mkdir recipe-api && cd recipe-api
uv init
uv add fastapi uvicorn psycopg2-binary
```

Make sure PostgreSQL is running (from your Week 1 Docker setup). Connect and create the database:

```bash
docker exec -it postgres psql -U postgres -c "CREATE DATABASE recipes;"
```

### Step 2: Database Schema and Connection

```python
# recipe-api/database.py

import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Store connection config in one place. In production you'd use environment
# variables or a config file -- hardcoding credentials is a Week 3 shortcut
# we'll fix when we add Docker Compose in session 3.
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "recipes",
    "user": "postgres",
    "password": "postgres",
}


@contextmanager
def get_db():
    """Context manager for database connections.

    Why a context manager instead of a global connection?
    1. Each request gets its own connection -- no shared state between requests.
    2. The connection is always closed, even if an exception occurs.
    3. We commit on success and rollback on failure -- proper transaction handling.

    In production, you'd use a connection POOL (like psycopg2.pool or SQLAlchemy)
    so you reuse connections instead of opening/closing on every request.
    For learning, this pattern teaches the right structure.
    """
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()  # Auto-commit if no exception was raised
    except Exception:
        conn.rollback()  # Undo partial changes on error
        raise
    finally:
        conn.close()  # Always release the connection


def init_db():
    """Create tables if they don't exist.

    This runs once at startup. IF NOT EXISTS makes it safe to call repeatedly --
    it won't destroy existing data. Two tables with a foreign key relationship:
    recipes (parent) and ingredients (child).
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS recipes (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    cuisine VARCHAR(100) NOT NULL,
                    prep_time_min INTEGER NOT NULL CHECK (prep_time_min > 0),
                    servings INTEGER NOT NULL CHECK (servings > 0),
                    instructions TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS ingredients (
                    id SERIAL PRIMARY KEY,
                    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    quantity DECIMAL(10, 2) NOT NULL,
                    unit VARCHAR(50) NOT NULL
                );
            """)
```

Key design choices:
- `ON DELETE CASCADE` means deleting a recipe automatically deletes its ingredients. Without this, you'd get foreign key errors when trying to delete recipes that have ingredients.
- `CHECK` constraints enforce business rules at the database level -- even if your API validation has a bug, the database won't accept a recipe with 0 servings.
- `RealDictCursor` returns rows as dictionaries instead of tuples, so `row["title"]` works instead of `row[0]`.

### Step 3: Pydantic Models

```python
# recipe-api/models.py

from pydantic import BaseModel, Field
from typing import Optional


class IngredientCreate(BaseModel):
    """What the client sends when adding an ingredient to a recipe."""
    name: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0, description="Amount of the ingredient")
    unit: str = Field(..., min_length=1, max_length=50, description="e.g., cups, grams, pieces")


class IngredientResponse(BaseModel):
    """What the API returns for an ingredient."""
    id: int
    recipe_id: int
    name: str
    quantity: float
    unit: str


class RecipeCreate(BaseModel):
    """What the client sends to create a recipe.
    Note: no `id` or `created_at` -- the database generates those."""
    title: str = Field(..., min_length=1, max_length=200)
    cuisine: str = Field(..., min_length=1, max_length=100)
    prep_time_min: int = Field(..., gt=0, description="Prep time in minutes")
    servings: int = Field(..., gt=0)
    instructions: str = Field(..., min_length=1)


class RecipeResponse(BaseModel):
    """What the API returns for a recipe."""
    id: int
    title: str
    cuisine: str
    prep_time_min: int
    servings: int
    instructions: str
    created_at: str  # Serialized as ISO string


class RecipeUpdate(BaseModel):
    """Partial update -- all fields optional."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    cuisine: Optional[str] = Field(default=None, min_length=1, max_length=100)
    prep_time_min: Optional[int] = Field(default=None, gt=0)
    servings: Optional[int] = Field(default=None, gt=0)
    instructions: Optional[str] = Field(default=None, min_length=1)
```

### Step 4: Main Application with Routes

```python
# recipe-api/main.py

from fastapi import FastAPI, HTTPException, Query
from typing import Optional
from database import get_db, init_db
from models import (
    RecipeCreate, RecipeResponse, RecipeUpdate,
    IngredientResponse,
)

app = FastAPI(title="Recipe Collection API", version="1.0.0")


@app.on_event("startup")
def startup():
    """Runs once when the server starts.
    Creates tables if they don't exist. This is a simple approach --
    in production, you'd use a migration tool like Alembic."""
    init_db()


# --- Recipe CRUD ---

@app.post("/recipes", response_model=RecipeResponse, status_code=201)
def create_recipe(recipe: RecipeCreate):
    """Create a new recipe.

    RETURNING * is a PostgreSQL feature that gives back the inserted row,
    including server-generated fields (id, created_at). Without it, you'd
    need a second query to fetch the created recipe.
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO recipes (title, cuisine, prep_time_min, servings, instructions)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                # Always use parameterized queries (%s placeholders).
                # NEVER use f-strings or .format() with SQL -- that's how SQL injection happens.
                # psycopg2 handles escaping and type conversion safely.
                (recipe.title, recipe.cuisine, recipe.prep_time_min,
                 recipe.servings, recipe.instructions),
            )
            created = cur.fetchone()
            created["created_at"] = created["created_at"].isoformat()
            return created


@app.get("/recipes", response_model=list[RecipeResponse])
def list_recipes(
    cuisine: Optional[str] = Query(
        default=None,
        description="Filter by cuisine type, e.g., Italian",
    ),
):
    """List all recipes, optionally filtered by cuisine.

    Building queries dynamically: we start with a base query and conditionally
    add WHERE clauses. The params list keeps parameter binding safe.
    This pattern scales well when you have multiple optional filters.
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            query = "SELECT * FROM recipes"
            params = []

            if cuisine:
                # ILIKE is case-insensitive LIKE -- PostgreSQL-specific.
                # So ?cuisine=italian matches "Italian", "ITALIAN", etc.
                query += " WHERE cuisine ILIKE %s"
                params.append(cuisine)

            query += " ORDER BY created_at DESC"

            cur.execute(query, params)
            recipes = cur.fetchall()

            for r in recipes:
                r["created_at"] = r["created_at"].isoformat()
            return recipes


@app.get("/recipes/{recipe_id}", response_model=RecipeResponse)
def get_recipe(recipe_id: int):
    """Get a single recipe by ID."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
            recipe = cur.fetchone()

            if not recipe:
                # Returning 404 for missing resources is a REST convention.
                # The client can distinguish "not found" from "server error" (500)
                # or "bad request" (400).
                raise HTTPException(status_code=404, detail=f"Recipe {recipe_id} not found")

            recipe["created_at"] = recipe["created_at"].isoformat()
            return recipe


@app.put("/recipes/{recipe_id}", response_model=RecipeResponse)
def update_recipe(recipe_id: int, updates: RecipeUpdate):
    """Update a recipe's fields. Only non-None fields are changed.

    Building a dynamic UPDATE query: we only SET the fields the client
    actually sent. This prevents accidentally nulling out fields.
    """
    update_data = updates.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    with get_db() as conn:
        with conn.cursor() as cur:
            # Check the recipe exists first
            cur.execute("SELECT id FROM recipes WHERE id = %s", (recipe_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail=f"Recipe {recipe_id} not found")

            # Build SET clause dynamically: "title = %s, cuisine = %s"
            set_clause = ", ".join(f"{key} = %s" for key in update_data)
            values = list(update_data.values()) + [recipe_id]

            cur.execute(
                f"UPDATE recipes SET {set_clause} WHERE id = %s RETURNING *",
                values,
            )
            updated = cur.fetchone()
            updated["created_at"] = updated["created_at"].isoformat()
            return updated


@app.delete("/recipes/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int):
    """Delete a recipe and all its ingredients (CASCADE handles ingredients)."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM recipes WHERE id = %s RETURNING id", (recipe_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail=f"Recipe {recipe_id} not found")


# --- Ingredient Routes ---

@app.get("/recipes/{recipe_id}/ingredients", response_model=list[IngredientResponse])
def get_recipe_ingredients(recipe_id: int):
    """Get all ingredients for a recipe.

    Nested routes like /recipes/{id}/ingredients express the parent-child
    relationship in the URL itself. The client doesn't need to know about
    the ingredients table -- they just follow the recipe's URL structure.
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            # Verify recipe exists first -- return 404 for the recipe, not an empty list
            cur.execute("SELECT id FROM recipes WHERE id = %s", (recipe_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail=f"Recipe {recipe_id} not found")

            cur.execute(
                "SELECT * FROM ingredients WHERE recipe_id = %s ORDER BY name",
                (recipe_id,),
            )
            return cur.fetchall()
```

### Step 5: Seed Data and Test

Run the server:

```bash
uv run uvicorn main:app --reload
```

Create some test data:

```bash
# Create a recipe
curl -X POST http://127.0.0.1:8000/recipes \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Spaghetti Carbonara",
    "cuisine": "Italian",
    "prep_time_min": 30,
    "servings": 4,
    "instructions": "Cook pasta. Fry guanciale. Mix eggs and cheese. Combine."
  }'

# Create another
curl -X POST http://127.0.0.1:8000/recipes \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Chicken Tikka Masala",
    "cuisine": "Indian",
    "prep_time_min": 45,
    "servings": 6,
    "instructions": "Marinate chicken. Grill. Simmer in spiced tomato sauce."
  }'

# Filter by cuisine
curl "http://127.0.0.1:8000/recipes?cuisine=Italian"

# Get ingredients for recipe 1 (empty so far)
curl http://127.0.0.1:8000/recipes/1/ingredients

# Try to get a recipe that doesn't exist
curl http://127.0.0.1:8000/recipes/999

# Update a recipe
curl -X PUT http://127.0.0.1:8000/recipes/1 \
  -H "Content-Type: application/json" \
  -d '{"prep_time_min": 25}'

# Delete a recipe
curl -X DELETE http://127.0.0.1:8000/recipes/2
```

### Step 6: Try SQL Injection (and See It Fail)

```bash
# This is what SQL injection looks like -- someone tries to sneak SQL into a field.
# Because we use parameterized queries (%s), psycopg2 escapes this safely.
# It just creates a recipe with a weird title -- no SQL is executed.
curl -X POST http://127.0.0.1:8000/recipes \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Evil Recipe\"; DROP TABLE recipes; --",
    "cuisine": "Hacker",
    "prep_time_min": 1,
    "servings": 1,
    "instructions": "Nice try."
  }'

# Verify the table still exists
curl http://127.0.0.1:8000/recipes
```

### Key Concepts Recap

| Concept | What We Used | Why |
|---------|-------------|-----|
| Context manager | `get_db()` | Automatic connection cleanup and transaction handling |
| Parameterized queries | `%s` placeholders | Prevents SQL injection |
| `RETURNING *` | After INSERT/UPDATE/DELETE | Gets back the affected row without a second query |
| `ON DELETE CASCADE` | Foreign key constraint | Child rows auto-deleted when parent is removed |
| `ILIKE` | Cuisine filter | Case-insensitive pattern matching (PostgreSQL) |
| Dynamic query building | Conditional WHERE/SET | Handles optional filters and partial updates safely |

---

## INDEPENDENT

### What to Build

Add three new features to the Recipe API. Keep the server running with `--reload`.

### Feature 1: Add Ingredients to a Recipe

Create a POST endpoint at `/recipes/{recipe_id}/ingredients` that adds an ingredient to a recipe. The request body should contain the ingredient's name, quantity, and unit. Return the created ingredient with a 201 status code.

Make sure to verify the recipe exists before inserting. If the recipe doesn't exist, return a 404.

**Expected behavior:**
- `POST /recipes/1/ingredients` with `{"name": "spaghetti", "quantity": 400, "unit": "grams"}` → returns the ingredient with its ID and recipe_id, status 201
- `POST /recipes/999/ingredients` with any body → returns 404

### Feature 2: Search Recipes by Ingredient

Create a GET endpoint at `/recipes/search` that accepts a query parameter `ingredient` and returns all recipes that contain a matching ingredient. The search should be case-insensitive.

This requires a JOIN between the recipes and ingredients tables. Think about whether you need an INNER JOIN or LEFT JOIN for this use case, and whether you might get duplicate recipes if a recipe has multiple matching ingredients.

**Expected behavior:**
- `GET /recipes/search?ingredient=chicken` → returns all recipes that have an ingredient with "chicken" in the name
- `GET /recipes/search?ingredient=xyz` → returns an empty list, not a 404
- The search should match partial names (so "chick" matches "chicken breast")
- Each recipe should appear only once, even if it has multiple matching ingredients

### Feature 3: Cuisine Statistics

Create a GET endpoint at `/cuisines/stats` that returns aggregate statistics grouped by cuisine. For each cuisine, return the number of recipes and the average prep time.

You'll need a GROUP BY query with COUNT and AVG aggregate functions. Round the average prep time to one decimal place.

**Expected behavior:**
- `GET /cuisines/stats` → returns something like:
  ```
  [
    {"cuisine": "Italian", "recipe_count": 3, "avg_prep_time": 27.3},
    {"cuisine": "Indian", "recipe_count": 2, "avg_prep_time": 40.0}
  ]
  ```
- Order results by recipe count descending (most popular cuisines first)
- If there are no recipes, return an empty list

### Seed Data

You'll need to add ingredients to your recipes before testing Feature 2. Use your new Feature 1 endpoint to add them.

---

## REVIEW CHECKLIST

- [ ] POST `/recipes/{id}/ingredients` creates an ingredient and returns 201
- [ ] POST `/recipes/{id}/ingredients` returns 404 for nonexistent recipe
- [ ] GET `/recipes/search?ingredient=X` uses a JOIN to find recipes by ingredient name
- [ ] Ingredient search is case-insensitive (ILIKE or LOWER())
- [ ] No duplicate recipes in search results (DISTINCT or GROUP BY)
- [ ] GET `/cuisines/stats` returns correct counts and averages
- [ ] Stats results are ordered by recipe_count descending
- [ ] All queries use parameterized placeholders (no f-strings with SQL)
- [ ] Student created appropriate Pydantic response models for new endpoints

---

## QUIZ

**Answer all 15 questions. You need 8/10 correct on any set of 10 to pass.**

---

**Q1 (Multiple Choice).** What is the primary purpose of a database connection pool?
- A) To encrypt database connections
- B) To reuse existing connections instead of opening/closing on every request
- C) To store multiple databases in memory
- D) To limit the number of tables in a database

---

**Q2 (Spot the Bug).** What's the security vulnerability in this code?

```python
@app.get("/users")
def search_users(name: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM users WHERE name = '{name}'")
            return cur.fetchall()
```

---

**Q3 (Short Answer).** Explain what `ON DELETE CASCADE` does on a foreign key constraint and why it's useful for the recipe/ingredient relationship.

---

**Q4 (Multiple Choice).** What does `RETURNING *` do in this SQL statement?

```sql
INSERT INTO recipes (title, cuisine) VALUES ('Pasta', 'Italian') RETURNING *;
```

- A) Returns all rows in the recipes table
- B) Returns the newly inserted row with all its columns (including generated ones like id)
- C) Returns the count of rows affected
- D) Returns the table schema

---

**Q5 (What does this code output?).** Given this endpoint:

```python
@app.get("/items/{item_id}")
def get_item(item_id: int):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM items WHERE id = %s", (item_id,))
            item = cur.fetchone()
            return item
```

What does the client receive when `item_id=999` and no item with that ID exists?

---

**Q6 (Short Answer).** Why should you verify that a parent resource exists before inserting a child resource (e.g., checking the recipe exists before adding an ingredient), even though the database has a foreign key constraint?

---

**Q7 (Multiple Choice).** What HTTP status code should you return when a client sends a request body that's syntactically valid JSON but contains invalid data (e.g., negative prep time)?
- A) 400 Bad Request
- B) 404 Not Found
- C) 422 Unprocessable Entity
- D) 500 Internal Server Error

---

**Q8 (Spot the Bug).** This endpoint should return only the fields defined in `RecipeResponse`, but it's leaking an internal field. Why?

```python
class RecipeResponse(BaseModel):
    id: int
    title: str

@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
            recipe = cur.fetchone()
            return recipe  # returns {"id": 1, "title": "Pasta", "secret_notes": "..."}
```

---

**Q9 (Short Answer).** What is the difference between `cur.fetchone()` and `cur.fetchall()`? When would you use each?

---

**Q10 (What does this code output?).** What happens when this code runs?

```python
@contextmanager
def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

with get_db() as conn:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO recipes (title) VALUES ('Soup')")
        raise ValueError("something broke")
```

Is the recipe "Soup" in the database after this code runs? Why or why not?

---

**Q11 (Multiple Choice).** Which of these is the correct way to pass parameters to a psycopg2 query?
- A) `cur.execute("SELECT * FROM t WHERE id = %d", (5,))`
- B) `cur.execute("SELECT * FROM t WHERE id = %s", (5,))`
- C) `cur.execute("SELECT * FROM t WHERE id = ?", (5,))`
- D) `cur.execute(f"SELECT * FROM t WHERE id = {5}")`

---

**Q12 (Short Answer).** In the recipe API, the `list_recipes` endpoint builds a query dynamically:

```python
query = "SELECT * FROM recipes"
if cuisine:
    query += " WHERE cuisine ILIKE %s"
```

Why use `ILIKE` instead of `=` for the cuisine filter?

---

**Q13 (Multiple Choice).** What does a `RealDictCursor` do in psycopg2?
- A) Returns rows as Python dictionaries with column names as keys
- B) Creates real-time database cursors that stream data
- C) Returns rows as named tuples
- D) Enables dictionary-based parameterized queries

---

**Q14 (Spot the Bug).** This dynamic UPDATE query has a subtle issue. What is it?

```python
def update_recipe(recipe_id: int, updates: RecipeUpdate):
    update_data = updates.model_dump(exclude_unset=True)
    set_clause = ", ".join(f"{key} = %s" for key in update_data)
    values = list(update_data.values())
    cur.execute(f"UPDATE recipes SET {set_clause} WHERE id = %s RETURNING *", values)
```

---

**Q15 (Short Answer).** Why is it better to return an empty list (with 200 status) instead of a 404 when a search query returns no results? When IS 404 appropriate?

---

### ANSWER KEY

**Q1:** B) To reuse existing connections instead of opening/closing on every request. Opening a database connection involves a TCP handshake, authentication, and memory allocation -- expensive operations. A pool keeps connections open and hands them out to requests, dramatically improving performance.

**Q2:** SQL injection vulnerability. The code uses an f-string to embed user input directly into SQL. An attacker could send `name = "'; DROP TABLE users; --"` and it would execute as SQL. Fix: use parameterized queries: `cur.execute("SELECT * FROM users WHERE name = %s", (name,))`.

**Q3:** `ON DELETE CASCADE` automatically deletes child rows when the parent row is deleted. For recipes/ingredients: when you delete a recipe, all its ingredients are automatically removed. Without it, you'd either get a foreign key violation error when trying to delete a recipe that has ingredients, or you'd have orphaned ingredient rows with no parent recipe.

**Q4:** B) Returns the newly inserted row with all its columns, including server-generated values like `id` (from SERIAL) and `created_at` (from DEFAULT NOW()). Without RETURNING, you'd need a separate SELECT query to get the complete row.

**Q5:** The client receives `null` (JSON null) with a 200 status code. `fetchone()` returns `None` when no row is found, and FastAPI serializes `None` as `null`. This is a bug -- the endpoint should check for `None` and raise an `HTTPException(status_code=404)` instead.

**Q6:** Two reasons: (1) **Better error messages.** The foreign key violation from PostgreSQL produces a generic database error (500), but checking first lets you return a clean 404 with a descriptive message. (2) **API contract.** Clients expect 404 for "resource not found," not 500 which implies a server bug.

**Q7:** C) 422 Unprocessable Entity. This is the standard code for "the syntax is valid but the content doesn't pass validation rules." FastAPI/Pydantic returns 422 automatically for validation failures. 400 is more general; 422 is more specific.

**Q8:** The endpoint returns the raw dictionary from the database (`return recipe`) instead of filtering it through the `RecipeResponse` model. To fix, either use `response_model=RecipeResponse` in the decorator (which FastAPI uses to filter the output), or explicitly construct a `RecipeResponse(**recipe)`. Without `response_model`, FastAPI just serializes whatever you return.

**Q9:** `fetchone()` returns a single row (or None if no results). `fetchall()` returns a list of all rows (or an empty list). Use `fetchone()` when you expect exactly one result (get by ID). Use `fetchall()` when you expect multiple results (list/search queries). Using `fetchall()` for a single-row query wastes memory; using `fetchone()` for a multi-row query loses all but the first result.

**Q10:** No, "Soup" is NOT in the database. The `raise ValueError` causes the context manager's `except` block to run, which calls `conn.rollback()`. This undoes the INSERT. Then the `finally` block closes the connection. The exception is re-raised after rollback. This is exactly why the context manager pattern is valuable -- it prevents partial writes from corrupting your data.

**Q11:** B) `cur.execute("SELECT * FROM t WHERE id = %s", (5,))`. psycopg2 always uses `%s` as the placeholder, regardless of the parameter type. psycopg2 handles type conversion internally. `%d` and `?` are not valid psycopg2 placeholders. Option D is SQL injection.

**Q12:** `ILIKE` is case-insensitive, so `?cuisine=italian` matches "Italian", "ITALIAN", and "italian". Using `=` would require the client to match the exact case stored in the database, which is bad user experience. `ILIKE` is PostgreSQL-specific; the standard SQL equivalent would be `WHERE LOWER(cuisine) = LOWER(%s)`.

**Q13:** A) Returns rows as Python dictionaries with column names as keys. Instead of accessing columns by index (`row[0]`), you use names (`row["title"]`). This makes code more readable and resilient to column order changes.

**Q14:** The `recipe_id` is not included in the `values` list. The query has `WHERE id = %s` at the end but the `values` list only contains the update fields. This will cause a "not enough arguments" error. Fix: `values = list(update_data.values()) + [recipe_id]`.

**Q15:** An empty list with 200 means "the query worked, there are just no results." This is semantically correct -- the collection exists, it's just empty for this filter. 404 means "the resource itself doesn't exist." Use 404 when requesting a specific resource by ID (e.g., `/recipes/999`). Don't use 404 for empty search results because the search endpoint exists -- it just found nothing.
