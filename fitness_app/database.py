"""
Database connection using asyncpg (async PostgreSQL driver).
"""

import os
import asyncpg

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set — use run.sh or export it manually")

_pool = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=10)
    return _pool


async def create_tables():
    """Create all tables if they don't exist yet."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            -- ── Foods library ──────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS foods (
                id              BIGSERIAL PRIMARY KEY,
                name            VARCHAR(200) NOT NULL,
                brand           VARCHAR(100),
                source          VARCHAR(20) DEFAULT 'custom',
                external_id     VARCHAR(100),
                kcal_per_100g   NUMERIC(6,1),
                protein_per_100g NUMERIC(6,1),
                carbs_per_100g  NUMERIC(6,1),
                fat_per_100g    NUMERIC(6,1),
                fibre_per_100g  NUMERIC(6,1),
                created_at      TIMESTAMPTZ DEFAULT now(),
                UNIQUE (source, external_id)
            );

            CREATE INDEX IF NOT EXISTS idx_foods_name ON foods (LOWER(name));

            -- ── Existing meals table (unchanged) ─────────────────────────────
            CREATE TABLE IF NOT EXISTS meals (
                id          BIGSERIAL PRIMARY KEY,
                log_date    DATE NOT NULL,
                meal_type   VARCHAR(50),
                description TEXT,
                calories    INTEGER,
                protein_g   NUMERIC(6,1),
                carbs_g     NUMERIC(6,1),
                fat_g       NUMERIC(6,1),
                fibre_g     NUMERIC(6,1),
                created_at  TIMESTAMPTZ DEFAULT now()
            );

            -- ── Meal items: foods + quantities for each meal ────────────────
            CREATE TABLE IF NOT EXISTS meal_items (
                id          BIGSERIAL PRIMARY KEY,
                meal_id     BIGINT REFERENCES meals(id) ON DELETE CASCADE,
                food_id     BIGINT REFERENCES foods(id) ON DELETE RESTRICT,
                grams       NUMERIC(7,1) NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_meal_items_meal ON meal_items (meal_id);

            -- ── Meal templates ─────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS meal_templates (
                id          BIGSERIAL PRIMARY KEY,
                name        VARCHAR(100) NOT NULL,
                meal_type   VARCHAR(50),
                description TEXT,
                created_at  TIMESTAMPTZ DEFAULT now()
            );

            CREATE TABLE IF NOT EXISTS meal_template_items (
                id              BIGSERIAL PRIMARY KEY,
                template_id     BIGINT REFERENCES meal_templates(id) ON DELETE CASCADE,
                food_id         BIGINT REFERENCES foods(id) ON DELETE RESTRICT,
                grams           NUMERIC(7,1) NOT NULL
            );

            -- ── Workouts (unchanged) ────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS workouts (
                id           BIGSERIAL PRIMARY KEY,
                log_date     DATE NOT NULL,
                session_type VARCHAR(100),
                duration_min INTEGER,
                rpe          SMALLINT CHECK (rpe BETWEEN 1 AND 10),
                notes        TEXT,
                created_at   TIMESTAMPTZ DEFAULT now()
            );

            CREATE TABLE IF NOT EXISTS workout_sets (
                id          BIGSERIAL PRIMARY KEY,
                workout_id  BIGINT REFERENCES workouts(id) ON DELETE CASCADE,
                exercise    VARCHAR(100),
                set_number  SMALLINT,
                reps        SMALLINT,
                weight_kg   NUMERIC(6,2),
                notes       TEXT
            );

            -- ── Weight log (unchanged) ──────────────────────────────────────
            CREATE TABLE IF NOT EXISTS weight_log (
                id          BIGSERIAL PRIMARY KEY,
                log_date    DATE NOT NULL,
                weight_kg   NUMERIC(5,2) NOT NULL,
                waist_cm    NUMERIC(5,1),
                notes       TEXT,
                created_at  TIMESTAMPTZ DEFAULT now()
            );

            -- ── Views ──────────────────────────────────────────────────────
            CREATE OR REPLACE VIEW daily_nutrition AS
            SELECT
                log_date,
                ROUND(SUM(calories))              AS total_kcal,
                ROUND(SUM(protein_g)::numeric, 1) AS total_protein_g,
                ROUND(SUM(carbs_g)::numeric,   1) AS total_carbs_g,
                ROUND(SUM(fat_g)::numeric,     1) AS total_fat_g
            FROM meals
            GROUP BY log_date
            ORDER BY log_date DESC;

            CREATE OR REPLACE VIEW rolling_weight AS
            SELECT
                log_date,
                weight_kg,
                waist_cm,
                ROUND(AVG(weight_kg) OVER (
                    ORDER BY log_date
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                )::numeric, 2) AS rolling_7d_avg
            FROM weight_log
            ORDER BY log_date DESC;
        """)
