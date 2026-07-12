"""
Meal templates router — save and reuse common meals.
 
Endpoints:
  POST   /templates         Create a template
  GET    /templates         List all templates
  GET    /templates/{id}    Get one template with items
  POST   /templates/{id}/use Apply template to a date (creates a meal)
  DELETE /templates/{id}    Delete a template
"""
 
import json
from datetime import date as DateType
from typing import List
from fastapi import APIRouter, HTTPException, Body
 
from database import get_pool
from models.schemas import (
    TemplateCreate,TemplateUpdate, TemplateOut,
    MealCreate, MealItemCreate, MealOut,
)
from routers.meals import create_meal, _fetch_items
 
router = APIRouter()
 
 
async def _fetch_template_items(conn, template_id):
    rows = await conn.fetch(
        """
        SELECT mti.*, row_to_json(f) AS food_data
        FROM meal_template_items mti
        LEFT JOIN foods f ON f.id = mti.food_id
        WHERE mti.template_id = $1
        """,
        template_id,
    )
    items = []
    for r in rows:
        d = dict(r)
        food = d.pop("food_data", None)
        if isinstance(food, str):
            food = json.loads(food)
        d["food"] = food
        items.append(d)
    return items
 
 
@router.post("/", response_model=TemplateOut, status_code=201)
async def create_template(tpl: TemplateCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO meal_templates (name, meal_type, description)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                tpl.name, tpl.meal_type, tpl.description,
            )
            t = dict(row)
            for item in tpl.items:
                await conn.execute(
                    """
                    INSERT INTO meal_template_items (template_id, food_id, grams)
                    VALUES ($1, $2, $3)
                    """,
                    t["id"], item.food_id, item.grams,
                )
            t["items"] = await _fetch_template_items(conn, t["id"])
    return t
 
 
@router.get("/", response_model=List[TemplateOut])
async def list_templates():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM meal_templates ORDER BY name"
        )
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = await _fetch_template_items(conn, d["id"])
            result.append(d)
    return result
 
 
@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(template_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM meal_templates WHERE id = $1", template_id
        )
        if not row:
            raise HTTPException(404, "Template not found")
        d = dict(row)
        d["items"] = await _fetch_template_items(conn, template_id)
    return d
 
 
@router.post("/{template_id}/use", response_model=MealOut, status_code=201)
async def use_template(
    template_id: int,
    log_date: DateType = Body(..., embed=True),
):
    """Create a new meal from a template on the given date."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM meal_templates WHERE id = $1", template_id
        )
        if not row:
            raise HTTPException(404, "Template not found")
        items = await _fetch_template_items(conn, template_id)
 
    meal = MealCreate(
        log_date=log_date,
        meal_type=row["meal_type"],
        description=row["description"] or row["name"],
        items=[MealItemCreate(food_id=i["food_id"], grams=i["grams"]) for i in items],
    )
    return await create_meal(meal)
 

@router.patch("/{template_id}", response_model=TemplateOut)
async def update_template(template_id: int, updates: TemplateUpdate):
    """
    Update a template's metadata (name, meal_type, description)
    and/or replace its items entirely.
 
    Items semantics: if `items` is provided, the existing items are
    deleted and replaced with the new list (replace-all). If `items`
    is omitted, existing items are left untouched.
    """
    data = updates.model_dump(exclude_unset=True)
    items = data.pop("items", None)
    meta = {k: v for k, v in data.items() if v is not None}
 
    if not meta and items is None:
        raise HTTPException(400, "No fields to update")
 
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            if meta:
                set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(meta))
                row = await conn.fetchrow(
                    f"UPDATE meal_templates SET {set_clause} WHERE id = $1 RETURNING *",
                    template_id, *meta.values(),
                )
            else:
                row = await conn.fetchrow(
                    "SELECT * FROM meal_templates WHERE id = $1", template_id
                )
            if not row:
                raise HTTPException(404, "Template not found")
 
            if items is not None:
                await conn.execute(
                    "DELETE FROM meal_template_items WHERE template_id = $1",
                    template_id,
                )
                for item in items:
                    await conn.execute(
                        """
                        INSERT INTO meal_template_items (template_id, food_id, grams)
                        VALUES ($1, $2, $3)
                        """,
                        template_id, item["food_id"], item["grams"],
                    )
 
            d = dict(row)
            d["items"] = await _fetch_template_items(conn, template_id)
    return d
 
@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM meal_templates WHERE id = $1", template_id
        )
    if result == "DELETE 0":
        raise HTTPException(404, "Template not found")