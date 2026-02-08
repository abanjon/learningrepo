# Week 3, Session 1: FastAPI Basics
**Domain:** Todo list API
**Concepts:** FastAPI, routes, HTTP methods, Pydantic models, path/query parameters, status codes, automatic docs
**Prerequisites:** Python environment with `uv`, basic Python classes and data validation from Weeks 1-2

---

## FOLLOW-ALONG

### Step 1: Project Setup

Create a new directory and install dependencies:

```bash
mkdir todo-api && cd todo-api
uv init
uv add fastapi uvicorn
```

Create the main application file:

```python
# todo-api/main.py

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# FastAPI() creates the application instance.
# The metadata here populates the auto-generated Swagger docs at /docs --
# this is one of FastAPI's killer features for API development.
app = FastAPI(
    title="Todo API",
    description="A simple todo list API to learn FastAPI fundamentals",
    version="1.0.0",
)


# --- Pydantic Models ---
# Pydantic models serve double duty in FastAPI:
# 1. They validate incoming request data automatically (bad data = 422 error)
# 2. They document the expected request/response shape in Swagger docs
# Separating "create" and "response" models is a common pattern because
# the client shouldn't set fields like `id` or `created_at` -- the server owns those.

class TodoCreate(BaseModel):
    """Schema for creating a new todo. The client sends this."""
    title: str = Field(
        ...,                    # ... means required -- no default value
        min_length=1,           # Pydantic validates this; empty strings get rejected
        max_length=200,
        description="What needs to be done",
    )
    priority: str = Field(
        default="medium",
        pattern="^(low|medium|high)$",  # regex constraint -- only these 3 values allowed
        description="Priority level: low, medium, or high",
    )
    completed: bool = Field(
        default=False,
        description="Whether the todo is done",
    )


class TodoResponse(BaseModel):
    """Schema for returning a todo to the client. Includes server-generated fields."""
    id: int
    title: str
    priority: str
    completed: bool
    created_at: str  # ISO format string for JSON serialization simplicity


class TodoUpdate(BaseModel):
    """Schema for updating a todo. All fields optional because you might
    only want to change the title without touching priority."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    priority: Optional[str] = Field(default=None, pattern="^(low|medium|high)$")
    completed: Optional[bool] = None


# --- In-Memory Storage ---
# A list works fine for learning. In session 2 we'll swap this for a real database.
# The counter gives us auto-incrementing IDs (like a database sequence).
todos: list[dict] = []
next_id: int = 1


# --- Helper ---
# Extracting "find by ID or 404" into a helper avoids repeating this logic
# in every endpoint that takes a todo ID. DRY principle.
def find_todo(todo_id: int) -> dict:
    """Find a todo by ID or raise 404."""
    for todo in todos:
        if todo["id"] == todo_id:
            return todo
    # HTTPException is FastAPI's way of returning error responses.
    # It short-circuits the request -- nothing after this line runs.
    raise HTTPException(status_code=404, detail=f"Todo {todo_id} not found")


# --- Routes ---

@app.get("/todos", response_model=list[TodoResponse])
def list_todos(
    # Query parameters are defined as function arguments.
    # FastAPI knows these are query params (not path params) because
    # they aren't in the URL path string.
    completed: Optional[bool] = Query(
        default=None,
        description="Filter by completion status: true or false",
    ),
):
    """List all todos, optionally filtered by completion status.

    GET /todos           -> all todos
    GET /todos?completed=true  -> only completed todos
    GET /todos?completed=false -> only pending todos
    """
    if completed is not None:
        # Filter in-memory. With a database, this would be a WHERE clause.
        return [t for t in todos if t["completed"] == completed]
    return todos


@app.post("/todos", response_model=TodoResponse, status_code=201)
def create_todo(todo: TodoCreate):
    """Create a new todo.

    POST with JSON body: {"title": "Buy groceries", "priority": "high"}
    Returns 201 Created -- not 200 -- because a new resource was created.
    This is a REST convention: 201 means "I made something new."
    """
    global next_id

    new_todo = {
        "id": next_id,
        "title": todo.title,
        "priority": todo.priority,
        "completed": todo.completed,
        # Store creation time so we can sort/filter by recency later.
        "created_at": datetime.now().isoformat(),
    }
    todos.append(new_todo)
    next_id += 1

    return new_todo


@app.get("/todos/{todo_id}", response_model=TodoResponse)
def get_todo(
    # Path parameters are defined by {name} in the route AND as a function argument.
    # FastAPI automatically converts the URL string to the declared type (int here).
    # If someone requests /todos/abc, FastAPI returns 422 before your code even runs.
    todo_id: int,
):
    """Get a single todo by its ID.

    Why a separate endpoint from list_todos? REST convention:
    - GET /todos     -> collection (list)
    - GET /todos/42  -> single resource
    This makes APIs predictable and cacheable.
    """
    return find_todo(todo_id)


@app.put("/todos/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: int, updates: TodoUpdate):
    """Update a todo's fields.

    PUT semantically means "replace the resource," but using Optional fields
    lets us do partial updates. Some APIs use PATCH for partial updates instead.
    The key thing: only non-None fields get changed.
    """
    todo = find_todo(todo_id)

    # model_dump(exclude_unset=True) gives us ONLY the fields the client
    # actually sent. If they sent {"title": "New title"}, we get just that --
    # we don't accidentally overwrite priority with None.
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        todo[key] = value

    return todo


@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    """Delete a todo.

    Returns 204 No Content -- the standard response for successful deletes.
    204 means "it worked, but there's nothing to send back."
    We don't return the deleted todo because the client already knows what it deleted.
    """
    todo = find_todo(todo_id)
    todos.remove(todo)
    # No return value -- FastAPI sends an empty 204 response.
```

Run the server:

```bash
uv run uvicorn main:app --reload
```

The `--reload` flag watches for file changes and restarts automatically -- essential during development.

### Step 2: Explore the Automatic Docs

Open your browser to **http://127.0.0.1:8000/docs**. This is Swagger UI, generated automatically from your route decorators and Pydantic models. Every endpoint, every parameter, every request/response schema is documented without writing a single line of documentation.

You can also visit **http://127.0.0.1:8000/redoc** for an alternative docs layout.

### Step 3: Test with curl

Open a new terminal and run these commands:

```bash
# Create a todo -- POST sends a JSON body, gets back the created resource with ID
curl -X POST http://127.0.0.1:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Learn FastAPI", "priority": "high"}'

# Create another
curl -X POST http://127.0.0.1:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy groceries", "priority": "low"}'

# List all todos
curl http://127.0.0.1:8000/todos

# Get one by ID
curl http://127.0.0.1:8000/todos/1

# Update it -- only the fields you send get changed
curl -X PUT http://127.0.0.1:8000/todos/1 \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'

# Filter by completion status
curl "http://127.0.0.1:8000/todos?completed=true"
curl "http://127.0.0.1:8000/todos?completed=false"

# Delete
curl -X DELETE http://127.0.0.1:8000/todos/2

# Try to get a deleted todo -- should return 404
curl http://127.0.0.1:8000/todos/2
```

### Step 4: See Validation in Action

```bash
# Empty title -- Pydantic rejects this with a 422 and a clear error message
curl -X POST http://127.0.0.1:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "", "priority": "high"}'

# Invalid priority -- doesn't match the regex pattern
curl -X POST http://127.0.0.1:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "priority": "urgent"}'

# Wrong type for path param -- FastAPI catches this before your code runs
curl http://127.0.0.1:8000/todos/abc

# Missing required field (title) -- 422 with field-level error detail
curl -X POST http://127.0.0.1:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"priority": "high"}'
```

Notice how every validation error returns a 422 with a structured JSON body showing exactly which field failed and why. You didn't write any of that error handling -- Pydantic and FastAPI did it.

### Key Concepts Recap

| Concept | What It Does |
|---------|-------------|
| `@app.get("/path")` | Maps a URL + HTTP method to a Python function |
| `{todo_id}` in path | Path parameter -- part of the URL itself |
| `Query()` parameter | Query parameter -- after the `?` in the URL |
| `response_model` | Tells FastAPI what shape the response should be (for docs + validation) |
| `status_code` | Override the default 200 OK with the appropriate HTTP status |
| `HTTPException` | Return an error response with a status code and message |
| Pydantic `BaseModel` | Validates request data and generates docs automatically |
| `Field(...)` | Add constraints (min_length, pattern, etc.) to model fields |

---

## INDEPENDENT

### What to Build

Add three new features to the Todo API. Keep the server running with `--reload` so your changes take effect immediately.

### Feature 1: Toggle Completion

Add a PATCH endpoint at `/todos/{id}/toggle` that flips a todo's `completed` field. If it's `false`, set it to `true`; if it's `true`, set it to `false`. Return the updated todo. Use the PATCH HTTP method because you're making a small, targeted change to one field -- this is the conventional REST choice for partial modifications.

**Expected behavior:**
- `PATCH /todos/1/toggle` on an incomplete todo → returns the todo with `completed: true`
- Calling it again → returns the todo with `completed: false`
- `PATCH /todos/999/toggle` → returns 404

### Feature 2: Stats Endpoint

Add a GET endpoint at `/todos/stats` that returns aggregate counts. It should return a JSON object with three integer fields: total number of todos, how many are completed, and how many are pending.

**Expected behavior:**
- With 3 todos (1 completed, 2 pending): `{"total": 3, "completed": 1, "pending": 2}`
- With no todos: `{"total": 0, "completed": 0, "pending": 0}`

**Important note about route ordering:** Think about what happens when FastAPI sees `GET /todos/stats`. Could it confuse "stats" for a todo ID? Consider where you place this route relative to `GET /todos/{todo_id}`.

### Feature 3: Additional Query Parameters

Extend the `GET /todos` endpoint to support two more query parameters:
- `priority` -- filter by priority level (e.g., `?priority=high`)
- `search` -- case-insensitive substring match on the title (e.g., `?search=grocery`)

These should stack with the existing `completed` filter. So `?completed=false&priority=high` returns only uncompleted high-priority todos.

**Expected behavior:**
- `GET /todos?priority=high` → only high-priority todos
- `GET /todos?search=learn` → todos whose title contains "learn" (case-insensitive)
- `GET /todos?completed=false&priority=high&search=fix` → all three filters applied

### Testing Your Work

Create a few todos with different priorities and titles, then test each new feature with curl or the Swagger docs at `/docs`.

---

## REVIEW CHECKLIST

- [ ] PATCH `/todos/{id}/toggle` correctly flips the `completed` boolean
- [ ] PATCH returns 404 for missing IDs
- [ ] GET `/todos/stats` returns correct counts for total, completed, pending
- [ ] `/todos/stats` route doesn't conflict with `/todos/{todo_id}` (route ordering)
- [ ] `?priority=` filter works on GET `/todos`
- [ ] `?search=` filter is case-insensitive
- [ ] Multiple query parameters can be combined
- [ ] Student created a Pydantic model for the stats response (good practice, not strictly required)
- [ ] Code runs without errors with `--reload`

---

## QUIZ

**Answer all 15 questions. You need 8/10 correct on any set of 10 to pass.**

---

**Q1 (Multiple Choice).** What HTTP method is most appropriate for an endpoint that creates a new resource?
- A) GET
- B) POST
- C) PUT
- D) PATCH

---

**Q2 (Short Answer).** What status code should a successful POST endpoint return when it creates a new resource, and why is it different from a regular 200?

---

**Q3 (What does this code output?).** Given this route:

```python
@app.get("/items/{item_id}")
def get_item(item_id: int):
    return {"item_id": item_id}
```

What happens when a client requests `GET /items/hello`?

---

**Q4 (Multiple Choice).** In FastAPI, what is the difference between a path parameter and a query parameter?
- A) Path parameters are in the URL path (`/items/42`), query parameters are after the `?` (`/items?id=42`)
- B) Path parameters are optional, query parameters are required
- C) Path parameters are strings only, query parameters support all types
- D) There is no difference -- they are interchangeable

---

**Q5 (Spot the Bug).** What's wrong with this code?

```python
class UserCreate(BaseModel):
    name: str
    email: str

@app.post("/users")
def create_user(user: UserCreate):
    # save user to database...
    return {"id": 1, "name": user.name, "email": user.email}
```

Hint: Think about the HTTP status code.

---

**Q6 (Short Answer).** Why does FastAPI require you to define a Pydantic model for POST request bodies instead of just accepting a raw dictionary?

---

**Q7 (Multiple Choice).** What status code does `HTTPException(status_code=404, detail="Not found")` return?
- A) 200 OK
- B) 400 Bad Request
- C) 404 Not Found
- D) 500 Internal Server Error

---

**Q8 (What does this code output?).** Given:

```python
class Item(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
```

What happens when the client sends `{"name": "Widget", "price": -5}`?

---

**Q9 (Multiple Choice).** When you define routes, the order matters. Given these two routes:

```python
@app.get("/users/me")
def get_current_user(): ...

@app.get("/users/{user_id}")
def get_user(user_id: str): ...
```

What happens if you swap their order (put `{user_id}` first)?
- A) Both routes still work correctly
- B) `/users/me` gets captured by `{user_id}` with `user_id="me"`
- C) FastAPI raises an error at startup
- D) The second route is silently ignored

---

**Q10 (Short Answer).** What does the `response_model` parameter in a route decorator do? Give two benefits of using it.

---

**Q11 (Spot the Bug).** This endpoint should return only active users, but it returns all users. Why?

```python
@app.get("/users")
def list_users(active: bool = None):
    if active:
        return [u for u in users if u["active"] == active]
    return users
```

---

**Q12 (Multiple Choice).** What HTTP status code means "the request was understood but the data sent didn't pass validation"?
- A) 400 Bad Request
- B) 404 Not Found
- C) 422 Unprocessable Entity
- D) 500 Internal Server Error

---

**Q13 (Short Answer).** Explain the difference between `PUT` and `PATCH` in REST conventions. When would you use each?

---

**Q14 (What does this code output?).** Given:

```python
@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    return {"message": "deleted"}
```

What does the client receive when calling `DELETE /items/1`?

---

**Q15 (Multiple Choice).** What does `Field(default="medium", pattern="^(low|medium|high)$")` do in a Pydantic model?
- A) Sets the field to "medium" and prevents any other value
- B) Sets a default of "medium" and validates that values match the regex pattern
- C) Creates three separate fields: low, medium, and high
- D) Sets the field to "medium" only when pattern matching fails

---

### ANSWER KEY

**Q1:** B) POST. POST is the standard HTTP method for creating new resources. GET retrieves, PUT replaces, PATCH partially updates.

**Q2:** 201 Created. It specifically indicates a new resource was created, unlike 200 which just means "success." REST conventions use specific status codes so clients can distinguish between different success types without parsing the response body.

**Q3:** FastAPI returns a **422 Unprocessable Entity** error. Because `item_id` is typed as `int`, FastAPI tries to convert "hello" to an integer, fails, and returns a validation error. Your function code never executes.

**Q4:** A) Path parameters are in the URL path, query parameters are after the `?`. Path params are typically required and identify a specific resource. Query params are typically optional and filter/modify the response.

**Q5:** The endpoint returns 200 by default, but it should return **201 Created** since it's creating a new resource. Fix: `@app.post("/users", status_code=201)`.

**Q6:** Two reasons: (1) **Automatic validation** -- Pydantic checks types, required fields, and constraints before your code runs, so you don't need manual validation logic. (2) **Automatic documentation** -- the model schema appears in the Swagger docs, so API consumers know exactly what to send.

**Q7:** C) 404 Not Found. The `status_code` parameter directly sets the HTTP response status code.

**Q8:** FastAPI returns a **422 Unprocessable Entity** error with a detail message explaining that `price` must be greater than 0. The `gt=0` constraint in `Field` rejects negative numbers and zero.

**Q9:** B) `/users/me` gets captured by `{user_id}` with `user_id="me"`. FastAPI matches routes in definition order, so the `{user_id}` pattern matches first. The literal `/users/me` route never gets a chance. Always put specific routes before parameterized ones.

**Q10:** `response_model` tells FastAPI the expected shape of the response. Benefits: (1) It **filters the response** to only include fields defined in the model (preventing accidental data leaks like passwords). (2) It **documents the response schema** in Swagger docs so API consumers know what to expect.

**Q11:** The bug is `if active:`. When `active=False`, Python treats `False` as falsy, so the filter is skipped and all users are returned. Fix: use `if active is not None:` to distinguish between "not provided" (None) and "explicitly set to False."

**Q12:** C) 422 Unprocessable Entity. This is what FastAPI returns when Pydantic validation fails. 400 is a more general "bad request." 422 specifically means the syntax was fine but the content didn't validate.

**Q13:** **PUT** replaces the entire resource -- the client sends a complete representation. **PATCH** partially updates -- the client sends only the fields to change. Use PUT when replacing (e.g., updating a user profile form), use PATCH for small targeted changes (e.g., toggling a completed status).

**Q14:** The client receives an **empty response with status 204**. Status code 204 means "No Content" -- the server intentionally sends no body. The `return {"message": "deleted"}` is ignored by FastAPI because 204 responses must have no body per the HTTP spec.

**Q15:** B) Sets a default of "medium" and validates that values match the regex pattern. If no value is provided, "medium" is used. If a value IS provided (like "urgent"), it must match the regex `^(low|medium|high)$` or Pydantic returns a validation error.
