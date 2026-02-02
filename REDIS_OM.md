RedisOM (for Python) is an “object mapper” on top of Redis that lets you define **Pydantic-style models** and then **save / fetch / query** them in Redis using a fluent API. It’s designed to work best with **Redis Stack** (or Redis with **Search & Query** + **JSON**) because “real querying” (`.find(...)`, full-text search, sorting, etc.) is powered by RediSearch/Redis Query Engine. ([Redis][1])

---

## Install via `pyproject.toml`

Minimal example (PEP 621 style):

```toml
[project]
dependencies = [
  "redis-om>=0.3",   # package name on PyPI is `redis-om`
]
```

PyPI name / install guidance: ([PyPI][2])

---

## Mental model: `get()` vs `find()`

* `Model.get(pk)` → fetch by primary key (no search index needed).
* `Model.find(...)` → uses Redis “Search & Query”, so you need:

  1. Redis Stack (or modules), and
  2. to run RedisOM’s **Migrator** to create the search index. ([Redis][1])

---

## Practical example model (JSON, mixed field types)

This assumes Redis Stack (JSON + Search). RedisOM’s own tutorial uses `JsonModel`, indexed fields, full-text search, and nested embedded models in the same style. ([Redis][1])

```python
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import PositiveInt
from redis_om import (
    EmbeddedJsonModel,
    Field,
    JsonModel,
    Migrator,
    get_redis_connection,
)

# Uses REDIS_OM_URL if set, otherwise defaults to localhost.
redis = get_redis_connection()

class Dimensions(EmbeddedJsonModel):
    width_cm: float = Field(index=True)
    height_cm: float = Field(index=True)
    depth_cm: float = Field(index=True)

class Product(JsonModel):
    # Strings
    sku: str = Field(index=True)
    name: str = Field(index=True)

    # Numerics
    price: float = Field(index=True)
    rating: PositiveInt = Field(index=True)

    # Booleans
    in_stock: bool = Field(index=True)

    # Lists
    tags: List[str] = Field(index=True)

    # Full text search (good for “description contains …” queries)
    description: str = Field(index=True, full_text_search=True)

    # Nested JSON object
    dims: Optional[Dimensions] = Field(index=True)

    # Datetime (often stored as string; index if you want sorting/filtering)
    created_at: datetime = Field(index=True)

    class Meta:
        database = redis

# Create / update the RediSearch index for all your models
Migrator().run()
```

Notes:

* `.run()` is the “make queries work” step (creates the indexes in Redis). ([Stack Overflow][3])
* Full text search is typically enabled via `Field(index=True, full_text_search=True)` and queried with the `%` operator (shown in Redis’s tutorial). ([Redis][1])

---

## CRUD: create, read, update, delete

### Create

```python
p = Product(
    sku="SKU-123",
    name="Adjustable Kettlebell",
    price=149.99,
    rating=5,
    in_stock=True,
    tags=["fitness", "strength"],
    description="Compact adjustable kettlebell for home workouts.",
    dims=Dimensions(width_cm=20.0, height_cm=30.0, depth_cm=20.0),
    created_at=datetime.utcnow(),
)

p.save()              # writes JSON + updates indexes
product_id = p.pk     # RedisOM generates IDs by default (ULIDs in the tutorial) :contentReference[oaicite:6]{index=6}
```

### Read by primary key

```python
same = Product.get(product_id)
```

### Update

```python
same.price = 139.99
same.in_stock = False
same.save()
```

### Delete

```python
same.delete()
```

---

## Querying: filters, “contains”, full-text, ordering

RedisOM’s tutorial shows the basic pattern:

* `Model.find((A) & (B)).all()`
* `.sort_by("field")` ([Redis][1])
* list/array “contains” using `<<` ([Redis][1])
* full-text using `%` ([Redis][1])

### Filters

```python
# price >= 50 AND in_stock == True
q = Product.find((Product.price >= 50) & (Product.in_stock == True))
results = q.all()
```

### “tags contains …”

```python
# Find products whose tags array contains "fitness"
results = Product.find(Product.tags << "fitness").all()
```

### Full-text search on description

```python
# Find products whose description includes “compact”
results = Product.find(Product.description % "compact").all()
```

### Order by a field

```python
# Cheapest first
results = Product.find().sort_by("price").all()

# Most expensive first (many RedisOM examples use "-" for descending)
results = Product.find().sort_by("-price").all()
```

---

## Limit/offset pagination

RedisOM’s query object supports pagination-style access (commonly via `.page(offset=..., limit=...)`). This maps to RediSearch’s LIMIT/OFFSET behavior under the hood.

```python
offset = 0
limit = 25

page_1 = Product.find(Product.in_stock == True).sort_by("-created_at").page(
    offset=offset,
    limit=limit,
)
page_2 = Product.find(Product.in_stock == True).sort_by("-created_at").page(
    offset=offset + limit,
    limit=limit,
)
```

Two important Redis/RediSearch realities to keep in mind:

* RediSearch has a **default max search results cap** (commonly 10,000). You can change it via `FT.CONFIG SET MAXSEARCHRESULTS ...`. ([Stack Overflow][4])
* If you expect *very large* result sets, consider designing around cursor-like pagination (e.g., “created_at < last_seen_created_at”) rather than deep offsets, for performance and predictability.

---

## FastAPI integration pattern

FastAPI doesn’t change RedisOM much; the main thing is: create the Redis connection once, run migrations on startup, and keep endpoints thin.

```python
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI()

@app.on_event("startup")
def startup():
    Migrator().run()  # ensure indexes exist before handling requests

class ProductCreate(BaseModel):
    sku: str
    name: str
    price: float
    rating: int
    in_stock: bool
    tags: list[str]
    description: str

@app.post("/products")
def create_product(payload: ProductCreate):
    p = Product(**payload.model_dump(), created_at=datetime.utcnow())
    p.save()
    return p

@app.get("/products/{pk}")
def get_product(pk: str):
    try:
        return Product.get(pk)
    except KeyError:
        raise HTTPException(status_code=404, detail="Not found")

@app.get("/products")
def list_products(
    q: str | None = None,
    in_stock: bool | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=200),
    sort: str = Query("-created_at"),
):
    query = Product.find()

    if in_stock is not None:
        query = Product.find(Product.in_stock == in_stock)

    if q:
        # full-text search over description
        query = query.find(Product.description % q) if hasattr(query, "find") else Product.find(Product.description % q)

    items = query.sort_by(sort).page(offset=offset, limit=limit)
    return {"offset": offset, "limit": limit, "results": items}
```

(You’ll likely tidy the query building a bit, but this shows the core mechanics: `.find(...)`, `.sort_by(...)`, `.page(...)`.)

---

## When you *might* hit issues (and how to avoid them)

* If `.find()` returns nothing / errors: check you’re running Redis Stack (or modules) and that `Migrator().run()` executed successfully. ([Redis][1])
* If pagination past ~10k starts behaving oddly: you may be running into RediSearch’s max results cap; adjust `MAXSEARCHRESULTS` or redesign pagination. ([Stack Overflow][4])

---

If you tell me what your real data model looks like (even just a rough Pydantic class), I can translate it into a RedisOM `JsonModel` + show the exact query patterns (including which fields should be `index=True` vs `full_text_search=True`, and which sorts will work well).

[1]: https://redis.io/docs/latest/integrate/redisom-for-python/ "RedisOM for Python | Docs"
[2]: https://pypi.org/project/redis-om/?utm_source=chatgpt.com "redis-om"
[3]: https://stackoverflow.com/questions/76429326/difference-of-get-and-find-in-redis-om-redisjson?utm_source=chatgpt.com "Difference of get() and find() in redis-om redisjson"
[4]: https://stackoverflow.com/questions/74617094/redis-search-offset-limit?utm_source=chatgpt.com "Redis Search offset limit"
