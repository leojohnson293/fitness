""""
Meals router — CRUD for the meals table, with optional food items.
 
If `items` are provided when creating a meal, macros are calculated
automatically from the foods + grams. Otherwise the macro fields you
pass in are used directly (legacy / quick-log path).
"""
 
import json
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, HTTPException
 
from database import get_pool
from models.schemas import (
    MealCreate, MealUpdate, MealOut, DailyNutrition,
    MealItemOut, FoodOut,
)
 
router = APIRouter()
 
 
async def _calculate_macros(conn, items):
    """Sum up macros from food items × grams."""
    if not items:
        return None
    food_ids = [i.food_id for i in items]
    foods = {
        r["id"]: r for r in await conn.fetch(
            "SELECT * FROM foods WHERE id = ANY($1)", food_ids
        )
    }
    totals = {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fibre": 0}
    for item in items:
        f = foods.get(item.food_id)
        if not f:
            raise HTTPException(404, f"Food id {item.food_id} not found")
        ratio = float(item.grams) / 100.0
        totals["kcal"]    += float(f["kcal_per_100g"]    or 0) * ratio
        totals["protein"] += float(f["protein_per_100g"] or 0) * ratio
        totals["carbs"]   += float(f["carbs_per_100g"]   or 0) * ratio
        totals["fat"]     += float(f["fat_per_100g"]     or 0) * ratio
        totals["fibre"]   += float(f["fibre_per_100g"]   or 0) * ratio
    return {
        "calories":  round(totals["kcal"]),
        "protein_g": round(totals["protein"], 1),
        "carbs_g":   round(totals["carbs"],   1),
        "fat_g":     round(totals["fat"],     1),
        "fibre_g":   round(totals["fibre"],   1),
    }
 
 
async def _fetch_items(conn, meal_id):
    rows = await conn.fetch(
        """
        SELECT mi.*, row_to_json(f) AS food_data
        FROM meal_items mi
        LEFT JOIN foods f ON f.id = mi.food_id
        WHERE mi.meal_id = $1
        """,
        meal_id,
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
 
 
@router.post("/", response_model=MealOut, status_code=201)
async def create_meal(meal: MealCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # If items provided, calculate macros from them
            if meal.items:
                macros = await _calculate_macros(conn, meal.items)
                calories  = macros["calories"]
                protein_g = macros["protein_g"]
                carbs_g   = macros["carbs_g"]
                fat_g     = macros["fat_g"]
                fibre_g   = macros["fibre_g"]
            else:
                calories, protein_g = meal.calories, meal.protein_g
                carbs_g, fat_g, fibre_g = meal.carbs_g, meal.fat_g, meal.fibre_g
 
            row = await conn.fetchrow(
                """
                INSERT INTO meals
                    (log_date, meal_type, description, calories,
                     protein_g, carbs_g, fat_g, fibre_g)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                RETURNING *
                """,
                meal.log_date, meal.meal_type, meal.description,
                calories, protein_g, carbs_g, fat_g, fibre_g,
            )
            meal_dict = dict(row)
 
            # Insert items
            for item in meal.items:
                await conn.execute(
                    """
                    INSERT INTO meal_items (meal_id, food_id, grams)
                    VALUES ($1, $2, $3)
                    """,
                    meal_dict["id"], item.food_id, item.grams,
                )
 
            meal_dict["items"] = await _fetch_items(conn, meal_dict["id"])
 
    return meal_dict
 
 
@router.get("/", response_model=List[MealOut])
async def list_meals(
    start_date: Optional[date] = None,
    end_date:   Optional[date] = None,
    limit:      int = 50,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM meals
            WHERE ($1::date IS NULL OR log_date >= $1)
              AND ($2::date IS NULL OR log_date <= $2)
            ORDER BY log_date DESC, created_at DESC
            LIMIT $3
            """,
            start_date, end_date, limit,
        )
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = await _fetch_items(conn, d["id"])
            result.append(d)
    return result
 
 
@router.get("/summary", response_model=List[DailyNutrition])
async def nutrition_summary(
    start_date: Optional[date] = None,
    end_date:   Optional[date] = None,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM daily_nutrition
            WHERE ($1::date IS NULL OR log_date >= $1)
              AND ($2::date IS NULL OR log_date <= $2)
            ORDER BY log_date DESC
            """,
            start_date, end_date,
        )
    return [dict(r) for r in rows]
 
 
@router.get("/{meal_id}", response_model=MealOut)
async def get_meal(meal_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM meals WHERE id = $1", meal_id)
        if not row:
            raise HTTPException(404, "Meal not found")
        d = dict(row)
        d["items"] = await _fetch_items(conn, meal_id)
    return d
 
 
@router.patch("/{meal_id}", response_model=MealOut)
async def update_meal(meal_id: int, updates: MealUpdate):
    fields = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(400, "No fields to update")
 
    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields))
    values = list(fields.values())
 
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE meals SET {set_clause} WHERE id = $1 RETURNING *",
            meal_id, *values,
        )
        if not row:
            raise HTTPException(404, "Meal not found")
        d = dict(row)
        d["items"] = await _fetch_items(conn, meal_id)
    return d
 
 
@router.delete("/{meal_id}", status_code=204)
async def delete_meal(meal_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM meals WHERE id = $1", meal_id)
    if result == "DELETE 0":
        raise HTTPException(404, "Meal not found")