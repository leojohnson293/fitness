"""
Workouts router — CRUD for workouts + workout_sets tables.
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, HTTPException

from database import get_pool
from models.schemas import WorkoutCreate, WorkoutUpdate, WorkoutOut, SetCreate, SetOut

router = APIRouter()


async def _fetch_sets(conn, workout_id: int) -> List[dict]:
    rows = await conn.fetch(
        "SELECT * FROM workout_sets WHERE workout_id = $1 ORDER BY set_number",
        workout_id,
    )
    return [dict(r) for r in rows]


@router.post("/", response_model=WorkoutOut, status_code=201)
async def create_workout(workout: WorkoutCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO workouts
                    (log_date, session_type, duration_min, rpe, notes)
                VALUES ($1,$2,$3,$4,$5)
                RETURNING *
                """,
                workout.log_date, workout.session_type,
                workout.duration_min, workout.rpe, workout.notes,
            )
            wo = dict(row)

            sets = []
            for s in workout.sets:
                srow = await conn.fetchrow(
                    """
                    INSERT INTO workout_sets
                        (workout_id, exercise, set_number, reps, weight_kg, notes)
                    VALUES ($1,$2,$3,$4,$5,$6)
                    RETURNING *
                    """,
                    wo["id"], s.exercise, s.set_number,
                    s.reps, s.weight_kg, s.notes,
                )
                sets.append(dict(srow))

    wo["sets"] = sets
    return wo


@router.get("/", response_model=List[WorkoutOut])
async def list_workouts(
    start_date: Optional[date] = None,
    end_date:   Optional[date] = None,
    limit:      int = 30,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM workouts
            WHERE ($1::date IS NULL OR log_date >= $1)
              AND ($2::date IS NULL OR log_date <= $2)
            ORDER BY log_date DESC, created_at DESC
            LIMIT $3
            """,
            start_date, end_date, limit,
        )
        result = []
        for r in rows:
            wo = dict(r)
            wo["sets"] = await _fetch_sets(conn, wo["id"])
            result.append(wo)
    return result


@router.get("/{workout_id}", response_model=WorkoutOut)
async def get_workout(workout_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM workouts WHERE id = $1", workout_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Workout not found")
        wo = dict(row)
        wo["sets"] = await _fetch_sets(conn, workout_id)
    return wo


@router.patch("/{workout_id}", response_model=WorkoutOut)
async def update_workout(workout_id: int, updates: WorkoutUpdate):
    fields = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields))
    values = list(fields.values())

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE workouts SET {set_clause} WHERE id = $1 RETURNING *",
            workout_id, *values,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Workout not found")
        wo = dict(row)
        wo["sets"] = await _fetch_sets(conn, workout_id)
    return wo


@router.delete("/{workout_id}", status_code=204)
async def delete_workout(workout_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM workouts WHERE id = $1", workout_id
        )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Workout not found")


# ── Sets sub-resource ─────────────────────────────────────────────────────────

@router.post("/{workout_id}/sets", response_model=SetOut, status_code=201)
async def add_set(workout_id: int, s: SetCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM workouts WHERE id = $1", workout_id
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Workout not found")
        row = await conn.fetchrow(
            """
            INSERT INTO workout_sets
                (workout_id, exercise, set_number, reps, weight_kg, notes)
            VALUES ($1,$2,$3,$4,$5,$6)
            RETURNING *
            """,
            workout_id, s.exercise, s.set_number,
            s.reps, s.weight_kg, s.notes,
        )
    return dict(row)


@router.delete("/{workout_id}/sets/{set_id}", status_code=204)
async def delete_set(workout_id: int, set_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM workout_sets WHERE id = $1 AND workout_id = $2",
            set_id, workout_id,
        )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Set not found")
