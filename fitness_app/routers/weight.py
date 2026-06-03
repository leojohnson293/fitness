"""
Weight router — CRUD for the weight_log table.
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, HTTPException

from database import get_pool
from models.schemas import WeightCreate, WeightUpdate, WeightOut

router = APIRouter()


@router.post("/", response_model=WeightOut, status_code=201)
async def create_weight_entry(entry: WeightCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO weight_log (log_date, weight_kg, waist_cm, notes)
            VALUES ($1, $2, $3, $4)
            RETURNING *
            """,
            entry.log_date, entry.weight_kg, entry.waist_cm, entry.notes,
        )
    return dict(row)


@router.get("/", response_model=List[WeightOut])
async def list_weight_entries(
    start_date: Optional[date] = None,
    end_date:   Optional[date] = None,
    limit:      int = 90,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                wl.*,
                rw.rolling_7d_avg
            FROM weight_log wl
            LEFT JOIN rolling_weight rw USING (log_date, weight_kg)
            WHERE ($1::date IS NULL OR wl.log_date >= $1)
              AND ($2::date IS NULL OR wl.log_date <= $2)
            ORDER BY wl.log_date DESC
            LIMIT $3
            """,
            start_date, end_date, limit,
        )
    return [dict(r) for r in rows]


@router.get("/{entry_id}", response_model=WeightOut)
async def get_weight_entry(entry_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM weight_log WHERE id = $1", entry_id
        )
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")
    return dict(row)


@router.patch("/{entry_id}", response_model=WeightOut)
async def update_weight_entry(entry_id: int, updates: WeightUpdate):
    fields = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields))
    values = list(fields.values())

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE weight_log SET {set_clause} WHERE id = $1 RETURNING *",
            entry_id, *values,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")
    return dict(row)


@router.delete("/{entry_id}", status_code=204)
async def delete_weight_entry(entry_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM weight_log WHERE id = $1", entry_id
        )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Entry not found")
