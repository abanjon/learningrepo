# Week 3, Session 4: API Testing & Request Validation
**Domain:** Inventory management API
**Concepts:** TestClient, pytest with FastAPI, testing CRUD endpoints, testing validation errors, test fixtures for API tests
**Prerequisites:** pytest fundamentals (Week 2 session 3), FastAPI basics (sessions 1-2)

---

## FOLLOW-ALONG

### Step 1: Project Setup

```bash
mkdir inventory-api && cd inventory-api
uv init
uv add fastapi uvicorn
uv add --dev pytest httpx
```

Note: FastAPI's `TestClient` is built on top of `httpx`, which is why we need to install it. Unlike `requests`, `httpx` supports async and is the modern standard for HTTP testing in Python.

### Step 2: The Application

```python
# inventory-api/main.py

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="Inventory Management API", version="1.0.0")


# --- Models ---

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    sku: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[A-Za-z0-9\-]+$",  # Only alphanumeric and hyphens
        description="Stock Keeping Unit -- unique product identifier",
    )
    quantity: int = Field(..., ge=0, description="Current stock count")
    price: float = Field(..., gt=0, description="Price in dollars, must be positive")
    category: str = Field(..., min_length=1, max_length=100)


class ProductResponse(BaseModel):
    id: int
    name: str
    sku: str
    quantity: int
    price: float
    category: str


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    quantity: Optional[int] = Field(default=None, ge=0)
    price: Optional[float] = Field(default=None, gt=0)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)


# --- Storage ---
# In-memory for testability. A real app would use a database, but
# in-memory storage makes tests fast and isolated -- no database setup needed.
products: list[dict] = []
next_id: int = 1


def reset_storage():
    """Clear all products and reset the ID counter.
    This exists specifically for testing -- each test starts with a clean slate."""
    global products, next_id
    products = []
    next_id = 1


def find_product(product_id: int) -> dict:
    for product in products:
        if product["id"] == product_id:
            return product
    raise HTTPException(status_code=404, detail=f"Product {product_id} not found")


def find_product_by_sku(sku: str) -> Optional[dict]:
    """SKUs should be unique. This helper checks for duplicates."""
    for product in products:
        if product["sku"].lower() == sku.lower():
            return product
    return None


# --- Routes ---

@app.post("/products", response_model=ProductResponse, status_code=201)
def create_product(product: ProductCreate):
    global next_id

    # Business rule: SKUs must be unique across all products.
    # The database would enforce this with a UNIQUE constraint;
    # with in-memory storage, we enforce it manually.
    existing = find_product_by_sku(product.sku)
    if existing:
        raise HTTPException(
            status_code=409,  # 409 Conflict -- the resource already exists
            detail=f"Product with SKU '{product.sku}' already exists",
        )

    new_product = {
        "id": next_id,
        "name": product.name,
        "sku": product.sku,
        "quantity": product.quantity,
        "price": product.price,
        "category": product.category,
    }
    products.append(new_product)
    next_id += 1
    return new_product


@app.get("/products", response_model=list[ProductResponse])
def list_products(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    min_price: Optional[float] = Query(default=None, gt=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(default=None, gt=0, description="Maximum price filter"),
):
    result = products

    if category:
        result = [p for p in result if p["category"].lower() == category.lower()]
    if min_price is not None:
        result = [p for p in result if p["price"] >= min_price]
    if max_price is not None:
        result = [p for p in result if p["price"] <= max_price]

    return result


@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int):
    return find_product(product_id)


@app.put("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, updates: ProductUpdate):
    product = find_product(product_id)
    update_data = updates.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    for key, value in update_data.items():
        product[key] = value

    return product


@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int):
    product = find_product(product_id)
    products.remove(product)
```

### Step 3: Test Configuration

```python
# inventory-api/conftest.py

import pytest
from fastapi.testclient import TestClient
from main import app, reset_storage


@pytest.fixture
def client():
    """Provides a fresh TestClient with empty storage for each test.

    Why a fixture instead of a global client?
    1. reset_storage() runs before EACH test, so tests are isolated.
       Test A creating a product doesn't affect Test B.
    2. The fixture pattern is standard pytest -- consistent with what
       you learned in Week 2.
    3. If we later switch to a database, we just change this fixture
       to set up/tear down a test database.
    """
    reset_storage()
    return TestClient(app)


@pytest.fixture
def sample_product():
    """Reusable product data for tests that need to create a product.

    Extracting test data into fixtures keeps tests focused on behavior,
    not on data setup. If the schema changes, you update one fixture
    instead of 20 tests.
    """
    return {
        "name": "Wireless Mouse",
        "sku": "WM-001",
        "quantity": 50,
        "price": 29.99,
        "category": "Electronics",
    }


@pytest.fixture
def created_product(client, sample_product):
    """A product that's already been created via the API.

    Fixture composition: this fixture USES the client and sample_product
    fixtures. pytest resolves the dependency chain automatically.
    Use this when your test needs an existing product but you don't
    want to repeat the POST call in every test.
    """
    response = client.post("/products", json=sample_product)
    return response.json()
```

### Step 4: Tests for Creating Products

```python
# inventory-api/test_products.py

class TestCreateProduct:
    """Group related tests in a class. No __init__ needed --
    pytest discovers test methods by the `test_` prefix."""

    def test_create_product_success(self, client, sample_product):
        """Happy path: valid data creates a product and returns 201."""
        response = client.post("/products", json=sample_product)

        # Always check the status code FIRST. If this fails,
        # the response body tells you what went wrong.
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Wireless Mouse"
        assert data["sku"] == "WM-001"
        assert data["quantity"] == 50
        assert data["price"] == 29.99
        assert data["category"] == "Electronics"
        # The server should have assigned an ID
        assert "id" in data
        assert isinstance(data["id"], int)

    def test_create_product_auto_increments_id(self, client, sample_product):
        """Each new product gets a unique, incrementing ID."""
        resp1 = client.post("/products", json=sample_product)

        # Modify the SKU so it doesn't conflict
        sample_product["sku"] = "WM-002"
        resp2 = client.post("/products", json=sample_product)

        assert resp1.json()["id"] == 1
        assert resp2.json()["id"] == 2

    def test_create_product_duplicate_sku(self, client, sample_product):
        """SKUs must be unique. Second create with same SKU gets 409 Conflict."""
        client.post("/products", json=sample_product)
        response = client.post("/products", json=sample_product)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_product_empty_name(self, client, sample_product):
        """Empty name should fail validation. Pydantic enforces min_length=1."""
        sample_product["name"] = ""
        response = client.post("/products", json=sample_product)

        # 422 is FastAPI/Pydantic's validation error status code.
        assert response.status_code == 422

    def test_create_product_negative_price(self, client, sample_product):
        """Price must be positive. Pydantic's gt=0 catches this."""
        sample_product["price"] = -5.00
        response = client.post("/products", json=sample_product)

        assert response.status_code == 422

    def test_create_product_zero_price(self, client, sample_product):
        """Zero price should also fail -- gt=0 means strictly greater than zero."""
        sample_product["price"] = 0
        response = client.post("/products", json=sample_product)

        assert response.status_code == 422

    def test_create_product_missing_required_field(self, client):
        """Omitting a required field should return 422 with field-level detail."""
        response = client.post("/products", json={"name": "Keyboard"})

        assert response.status_code == 422
        # The error detail should mention the missing fields
        errors = response.json()["detail"]
        # errors is a list of validation error objects
        assert len(errors) > 0

    def test_create_product_invalid_sku_format(self, client, sample_product):
        """SKU only allows alphanumeric characters and hyphens."""
        sample_product["sku"] = "INVALID SKU!@#"
        response = client.post("/products", json=sample_product)

        assert response.status_code == 422


class TestGetProduct:

    def test_get_product_success(self, client, created_product):
        """Fetch an existing product by ID."""
        product_id = created_product["id"]
        response = client.get(f"/products/{product_id}")

        assert response.status_code == 200
        assert response.json()["name"] == "Wireless Mouse"

    def test_get_product_not_found(self, client):
        """Requesting a nonexistent ID returns 404."""
        response = client.get("/products/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_product_invalid_id_type(self, client):
        """Non-integer ID gets caught by FastAPI's path parameter validation."""
        response = client.get("/products/abc")

        assert response.status_code == 422


class TestListProducts:

    def test_list_empty(self, client):
        """No products exist yet -- should return an empty list, not an error."""
        response = client.get("/products")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_with_products(self, client, sample_product):
        """List returns all created products."""
        client.post("/products", json=sample_product)

        response = client.get("/products")

        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_filter_by_category(self, client, sample_product):
        """Category filter returns only matching products."""
        client.post("/products", json=sample_product)

        # Create a product in a different category
        other = sample_product.copy()
        other["sku"] = "KB-001"
        other["name"] = "Keyboard"
        other["category"] = "Peripherals"
        client.post("/products", json=other)

        response = client.get("/products?category=Electronics")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["category"] == "Electronics"

    def test_filter_by_price_range(self, client, sample_product):
        """Price range filters work together."""
        client.post("/products", json=sample_product)

        cheap = sample_product.copy()
        cheap.update({"sku": "CH-001", "name": "Cable", "price": 5.99})
        client.post("/products", json=cheap)

        expensive = sample_product.copy()
        expensive.update({"sku": "EX-001", "name": "Monitor", "price": 499.99})
        client.post("/products", json=expensive)

        response = client.get("/products?min_price=10&max_price=100")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Wireless Mouse"


class TestUpdateProduct:

    def test_update_product_success(self, client, created_product):
        """Update a single field -- other fields stay unchanged."""
        product_id = created_product["id"]
        response = client.put(
            f"/products/{product_id}",
            json={"price": 24.99},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 24.99
        # Name shouldn't change
        assert data["name"] == "Wireless Mouse"

    def test_update_product_not_found(self, client):
        response = client.put("/products/999", json={"price": 10.0})

        assert response.status_code == 404

    def test_update_product_no_fields(self, client, created_product):
        """Sending an empty update body should return 400."""
        product_id = created_product["id"]
        response = client.put(f"/products/{product_id}", json={})

        assert response.status_code == 400


class TestDeleteProduct:

    def test_delete_product_success(self, client, created_product):
        """Delete returns 204 and the product is gone."""
        product_id = created_product["id"]
        response = client.delete(f"/products/{product_id}")

        assert response.status_code == 204

        # Verify it's actually gone
        get_response = client.get(f"/products/{product_id}")
        assert get_response.status_code == 404

    def test_delete_product_not_found(self, client):
        response = client.delete("/products/999")

        assert response.status_code == 404
```

### Step 5: Run the Tests

```bash
uv run pytest -v
```

You should see all tests passing with clear names describing what each test checks. The `-v` flag shows each test name -- useful for understanding test coverage at a glance.

```bash
# Run tests with short summary of failures (if any)
uv run pytest -v --tb=short

# Run only one test class
uv run pytest -v -k "TestCreateProduct"

# Run a specific test
uv run pytest -v -k "test_create_product_negative_price"
```

### Key Concepts Recap

| Concept | What We Did | Why |
|---------|------------|-----|
| `TestClient` | `client = TestClient(app)` | Send HTTP requests without a running server |
| Fixtures | `@pytest.fixture` with `reset_storage()` | Isolate tests from each other |
| Fixture composition | `created_product` uses `client` and `sample_product` | Reduce repetition in test setup |
| Status code assertions | `assert response.status_code == 201` | Always verify the status code first |
| Validation error testing | Send bad data, expect 422 | Verify your Pydantic models actually catch bad input |
| Class-based grouping | `class TestCreateProduct:` | Organize tests by feature/endpoint |

---

## INDEPENDENT

### What to Build

Add three new features to the inventory API and write comprehensive tests for each. All tests must pass.

### Feature 1: Bulk Product Creation

Add a POST endpoint at `/products/bulk` that accepts a JSON list of products and creates them all. The endpoint should return a list of the created products with status 201.

If any product in the batch has a duplicate SKU (either duplicated within the batch itself, or matching an existing product), the entire batch should be rejected. None of the products should be created -- it's all or nothing. Return a 409 with a message indicating which SKU(s) caused the conflict.

**Tests to write:**
- Successful bulk creation of 3 products
- Batch rejected when one product has a duplicate SKU (matching an existing product)
- Batch rejected when two products within the same batch share a SKU
- All-or-nothing behavior: verify no products were created after a rejected batch
- Empty list submission returns 400

### Feature 2: Low Stock Alert

Add a GET endpoint at `/products/low-stock` that accepts a `threshold` query parameter (default: 10) and returns all products whose quantity is at or below that threshold, sorted by quantity ascending (lowest stock first).

**Tests to write:**
- Returns products below the threshold
- Default threshold is 10 when not specified
- Custom threshold (e.g., `?threshold=5`) works
- Products above the threshold are excluded
- Returns empty list when all products are well-stocked
- Results are sorted by quantity ascending

### Feature 3: Edge Case Tests

Write tests for input edge cases on the existing create endpoint. These tests verify that your validation is robust.

**Tests to write:**
- Product with a name that's exactly 200 characters (the max) -- should succeed
- Product with a name that's 201 characters -- should fail
- SKU with special characters (spaces, exclamation marks, underscores) -- should fail per the regex pattern
- SKU with hyphens -- should succeed
- Price with many decimal places (e.g., 19.999999) -- should succeed (your API doesn't restrict decimal places)
- Negative quantity -- should fail
- Quantity of exactly 0 -- should succeed (ge=0 means greater than or equal)

### Route Ordering Note

Think carefully about where you put the `/products/bulk` and `/products/low-stock` routes relative to `/products/{product_id}`. The same route ordering issue from session 1 applies here.

### Verification

Run `uv run pytest -v` and confirm all tests pass, including both the existing tests and your new ones.

---

## REVIEW CHECKLIST

- [ ] POST `/products/bulk` creates multiple products in a single request
- [ ] Bulk endpoint rejects the entire batch on duplicate SKU (all-or-nothing)
- [ ] Bulk endpoint catches duplicates within the submitted batch
- [ ] GET `/products/low-stock` returns products at or below threshold
- [ ] Default threshold is 10, custom threshold works
- [ ] Low-stock results are sorted by quantity ascending
- [ ] Edge case tests cover boundary values (max length, zero quantity, etc.)
- [ ] Route ordering is correct (literal routes before parameterized)
- [ ] ALL tests pass with `uv run pytest -v`
- [ ] Tests are organized in logical classes or clear naming structure

---

## QUIZ

**Answer all 15 questions. You need 8/10 correct on any set of 10 to pass.**

---

**Q1 (Multiple Choice).** What does FastAPI's `TestClient` do?
- A) Starts a real HTTP server and sends requests to it
- B) Sends HTTP requests directly to the ASGI app without starting a server
- C) Generates test cases automatically from route definitions
- D) Mocks all HTTP responses

---

**Q2 (Short Answer).** Why is it important to call `reset_storage()` before each test in the fixture? What could go wrong without it?

---

**Q3 (Spot the Bug).** This test is supposed to verify that deleting a product works, but it has a subtle flaw:

```python
def test_delete_product(client, sample_product):
    client.post("/products", json=sample_product)
    client.delete("/products/1")

    response = client.get("/products")
    assert len(response.json()) == 0
```

What makes this test fragile?

---

**Q4 (Multiple Choice).** What status code does FastAPI return when Pydantic validation fails on a request body?
- A) 400
- B) 404
- C) 422
- D) 500

---

**Q5 (What does this code output?).** What does this test assert?

```python
def test_example(client):
    response = client.post("/products", json={"name": "X", "sku": "A-1", "quantity": 5, "price": 10.0, "category": "Test"})
    assert response.status_code == 201
    response = client.post("/products", json={"name": "Y", "sku": "A-1", "quantity": 3, "price": 20.0, "category": "Test"})
    assert response.status_code == 409
```

What behavior is being tested, and why is 409 the expected status code?

---

**Q6 (Short Answer).** Explain fixture composition with an example. Why is it useful?

---

**Q7 (Multiple Choice).** Which `pytest` flag shows the name of each individual test as it runs?
- A) `-s`
- B) `-v`
- C) `--tb=short`
- D) `-x`

---

**Q8 (Spot the Bug).** This test always passes, even when the API is broken. Why?

```python
def test_create_product(client):
    response = client.post("/products", json={
        "name": "Widget",
        "sku": "W-1",
        "quantity": 10,
        "price": 5.99,
        "category": "Gadgets",
    })
    data = response.json()
    assert data["name"]
```

---

**Q9 (Short Answer).** What is the difference between `assert response.status_code == 200` and `response.raise_for_status()`? Which is preferred in tests and why?

---

**Q10 (What does this code output?).** What happens when this test runs?

```python
@pytest.fixture
def client():
    reset_storage()
    return TestClient(app)

def test_a(client):
    client.post("/products", json=valid_product)
    assert len(client.get("/products").json()) == 1

def test_b(client):
    assert len(client.get("/products").json()) == 0
```

Does `test_b` pass or fail? Why?

---

**Q11 (Multiple Choice).** What does the `-k` flag do in pytest?
- A) Keeps running after the first failure
- B) Filters tests by keyword expression (test name matching)
- C) Kills the test process after timeout
- D) Shows test coverage by keyword

---

**Q12 (Short Answer).** Why should you test validation errors (like sending negative prices or empty names) rather than just testing happy paths?

---

**Q13 (Spot the Bug).** This test is supposed to check that updating a product changes its price. What's the problem?

```python
def test_update_price(client, created_product):
    response = client.put(f"/products/{created_product['id']}", json={"price": 19.99})
    assert response.json()["price"] == 19.99

    original = client.get(f"/products/{created_product['id']}")
    assert original.json()["price"] == 29.99  # Original price
```

---

**Q14 (Multiple Choice).** When testing an endpoint that should return 204 No Content, what should you verify?
- A) Only the status code
- B) The status code and that the response body is empty
- C) The status code and that the resource is actually gone (follow-up GET returns 404)
- D) Both B and C

---

**Q15 (Short Answer).** You have an endpoint that creates a resource and returns 201. Name three things you should assert in a "happy path" test for this endpoint.

---

### ANSWER KEY

**Q1:** B) Sends HTTP requests directly to the ASGI app without starting a server. TestClient creates an in-process test transport that calls your FastAPI app's ASGI interface directly. This makes tests fast (no network overhead) and simple (no port management or server process).

**Q2:** Without `reset_storage()`, tests share state. If `test_a` creates a product, `test_b` would see it in the product list. This creates order-dependent tests: they pass when run together in one order but fail in another. Isolated tests are more reliable and easier to debug because each test's behavior depends only on its own setup.

**Q3:** The test hardcodes `"/products/1"` instead of using the ID from the create response. If the ID assignment logic changes, or if tests run in a different order (and reset_storage timing changes the next_id), this test breaks. Fix: capture the created product's ID from the POST response and use it in the delete call.

**Q4:** C) 422 Unprocessable Entity. FastAPI uses Pydantic for request validation, and any validation failure returns 422 with a structured error body listing which fields failed and why.

**Q5:** The test verifies that creating two products with the same SKU ("A-1") results in a 409 Conflict for the second attempt. 409 is appropriate because the client is trying to create a resource that conflicts with an existing one (the SKU uniqueness constraint). The first POST succeeds (201), the second is rejected (409).

**Q6:** Fixture composition is when one fixture depends on other fixtures. For example, `created_product(client, sample_product)` uses both the `client` fixture (for making API calls) and the `sample_product` fixture (for the data). pytest resolves the dependency chain automatically. It's useful because it builds reusable layers: `sample_product` provides data, `client` provides the test client, and `created_product` combines them to provide a pre-created product. Changes to the product data only need updating in `sample_product`.

**Q7:** B) `-v` (verbose). It shows each test's full name and PASSED/FAILED status. `-s` shows print output, `--tb=short` shortens traceback, `-x` stops at first failure.

**Q8:** `assert data["name"]` only checks that the `name` key exists and is truthy (non-empty). It doesn't verify the VALUE. If the API returned `"name": "WRONG_NAME"`, this test would still pass. Fix: `assert data["name"] == "Widget"`. Always assert specific expected values, not just truthiness.

**Q9:** `assert response.status_code == 200` checks the exact status code and gives a clear failure message showing the actual code. `response.raise_for_status()` raises an exception for any 4xx/5xx code but doesn't let you test for specific error codes (like 404 vs 422). In tests, explicit status code assertions are preferred because (1) you test the EXACT code, not just "success" or "failure," and (2) the assertion failure message is more informative.

**Q10:** `test_b` PASSES. The `client` fixture runs `reset_storage()` before each test. So even though `test_a` created a product, `test_b` gets a fresh client with empty storage. This is fixture isolation in action.

**Q11:** B) Filters tests by keyword expression. `pytest -k "create"` runs only tests with "create" in their name. You can also combine with `and`, `or`, `not`: `pytest -k "create and not duplicate"`.

**Q12:** Validation errors are your API's first line of defense against bad data. Testing them ensures: (1) Malicious or malformed input is rejected before reaching your business logic or database. (2) Error messages are helpful for API consumers to fix their requests. (3) Pydantic constraints actually work as expected (e.g., you intended gt=0 but wrote ge=0). If you only test happy paths, you might deploy an API that accepts negative prices or empty names.

**Q13:** The second assertion (`original.json()["price"] == 29.99`) FAILS. The PUT endpoint updated the product's price to 19.99, and the GET afterward reflects that update. The test seems to expect that the GET returns the old price, but the update was persistent. The test is contradicting itself -- it verifies the update worked (line 2) then checks that it didn't (line 4).

**Q14:** D) Both B and C. A complete test for DELETE should verify: (1) the status code is 204, (2) the response body is empty (204 means "No Content"), and (3) the resource is actually gone (a follow-up GET returns 404). Checking only the status code misses cases where the delete "succeeds" but the resource is still there.

**Q15:** Three things to assert: (1) **Status code is 201** -- confirms the resource was created. (2) **Response body contains expected field values** -- the returned data matches what was sent (name, price, etc.). (3) **Server-generated fields are present and valid** -- the response includes an `id` (and it's an integer), plus any other server-set fields like `created_at`. Optional bonus: verify a follow-up GET for the new ID returns the same data.
