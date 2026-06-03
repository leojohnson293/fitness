"""
Foods router — manage your food library + search Open Food Facts.

Endpoints:
  GET    /foods                List all custom foods
  GET    /foods/search?q=...   Search local library
  POST   /foods                Add a custom food
  GET    /foods/{id}           Get one food
  DELETE /foods/{id}           Delete a food
  GET    /foods/off?q=...      Search Open Food Facts (external)
  POST   /foods/import         Import an Open Food Facts result into your library
"""

from typing import List, Optional
import httpx
from fastapi import APIRouter, HTTPException, Query

from database import get_pool
from models.schemas import FoodCreate, FoodOut

router = APIRouter()

OFF_SEARCH_URL = "https://search.openfoodfacts.org/search"
OFF_PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"


# ── Local library ─────────────────────────────────────────────────────────────

@router.post("/", response_model=FoodOut, status_code=201)
async def create_food(food: FoodCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO foods
                (name, brand, source, external_id,
                 kcal_per_100g, protein_per_100g,
                 carbs_per_100g, fat_per_100g, fibre_per_100g)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            ON CONFLICT (source, external_id)
                WHERE external_id IS NOT NULL
            DO UPDATE SET name = EXCLUDED.name
            RETURNING *
            """,
            food.name, food.brand, food.source or "custom", food.external_id,
            food.kcal_per_100g, food.protein_per_100g,
            food.carbs_per_100g, food.fat_per_100g, food.fibre_per_100g,
        )
    return dict(row)


@router.get("/", response_model=List[FoodOut])
async def list_foods(limit: int = 100):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM foods ORDER BY name LIMIT $1", limit
        )
    return [dict(r) for r in rows]


@router.get("/search", response_model=List[FoodOut])
async def search_local(q: str = Query(..., min_length=1), limit: int = 20):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM foods
            WHERE LOWER(name) LIKE LOWER($1)
               OR LOWER(brand) LIKE LOWER($1)
            ORDER BY name
            LIMIT $2
            """,
            f"%{q}%", limit,
        )
    return [dict(r) for r in rows]


@router.get("/{food_id}", response_model=FoodOut)
async def get_food(food_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM foods WHERE id = $1", food_id)
    if not row:
        raise HTTPException(404, "Food not found")
    return dict(row)


@router.delete("/{food_id}", status_code=204)
async def delete_food(food_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            result = await conn.execute("DELETE FROM foods WHERE id = $1", food_id)
        except Exception as e:
            raise HTTPException(409, f"Cannot delete — food is used in meals: {e}")
    if result == "DELETE 0":
        raise HTTPException(404, "Food not found")


# ── Open Food Facts integration ───────────────────────────────────────────────

@router.get("/off/search")
async def search_off(q: str = Query(..., min_length=2), page_size: int = 10):
    """Search Open Food Facts via the Search-a-licious API."""
    params = {
        "q": q,
        "page_size": page_size,
        "fields": "code,product_name,brands,nutriments",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(OFF_SEARCH_URL, params=params)
        r.raise_for_status()
        data = r.json()

    results = []
    for p in data.get("hits", []):
        n = p.get("nutriments", {})
        # Brand can be a list, string, or None — normalise to string
        brand = p.get("brands")
        if isinstance(brand, list):
            brand = ", ".join(brand) if brand else None
        results.append({
            "external_id":      p.get("code"),
            "name":             p.get("product_name") or "Unknown",
            "brand":            brand,
            "kcal_per_100g":    n.get("energy-kcal_100g"),
            "protein_per_100g": n.get("proteins_100g"),
            "carbs_per_100g":   n.get("carbohydrates_100g"),
            "fat_per_100g":     n.get("fat_100g"),
            "fibre_per_100g":   n.get("fiber_100g"),
        })
    # Filter out incomplete entries
    return [r for r in results if r["name"] and r["kcal_per_100g"] is not None]


@router.post("/import", response_model=FoodOut, status_code=201)
async def import_off(food: FoodCreate):
    """Import an Open Food Facts result into the local library."""
    food.source = "openfoodfacts"
    return await create_food(food)