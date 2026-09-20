-- Migration 002: Switch all primary keys from BIGSERIAL to UUID
--
-- Existing rows get a fresh random UUID, and every foreign key is re-pointed
-- at the new UUID by joining on the old integer id, so all relationships
-- (meal → items, template → items, workout → sets, item → food) survive.
--
-- Irreversible: the old integer ids are dropped. Back up with pg_dump first.
-- Requires PostgreSQL 13+ for the built-in gen_random_uuid().
-- _migrations keeps its SERIAL id — it's internal bookkeeping.

-- ── 1. Give every row a new UUID ───────────────────────────────────────────
ALTER TABLE foods               ADD COLUMN new_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE meals               ADD COLUMN new_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE meal_templates      ADD COLUMN new_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE workouts            ADD COLUMN new_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE weight_log          ADD COLUMN new_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE meal_items          ADD COLUMN new_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE meal_template_items ADD COLUMN new_id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE workout_sets        ADD COLUMN new_id UUID NOT NULL DEFAULT gen_random_uuid();

-- ── 2. Map child foreign keys onto the parents' new UUIDs ──────────────────
ALTER TABLE meal_items          ADD COLUMN new_meal_id UUID, ADD COLUMN new_food_id UUID;
ALTER TABLE meal_template_items ADD COLUMN new_template_id UUID, ADD COLUMN new_food_id UUID;
ALTER TABLE workout_sets        ADD COLUMN new_workout_id UUID;

UPDATE meal_items mi          SET new_meal_id     = m.new_id FROM meals m          WHERE m.id = mi.meal_id;
UPDATE meal_items mi          SET new_food_id     = f.new_id FROM foods f          WHERE f.id = mi.food_id;
UPDATE meal_template_items ti SET new_template_id = t.new_id FROM meal_templates t WHERE t.id = ti.template_id;
UPDATE meal_template_items ti SET new_food_id     = f.new_id FROM foods f          WHERE f.id = ti.food_id;
UPDATE workout_sets ws        SET new_workout_id  = w.new_id FROM workouts w       WHERE w.id = ws.workout_id;

-- ── 3. Drop the old integer columns ────────────────────────────────────────
-- Children first: dropping their FK columns also drops the FK constraints
-- and idx_meal_items_meal. No CASCADE, so anything unexpected that depends
-- on these columns makes the migration fail (and roll back) instead of
-- being silently dropped.
ALTER TABLE meal_items          DROP COLUMN meal_id,     DROP COLUMN food_id, DROP COLUMN id;
ALTER TABLE meal_template_items DROP COLUMN template_id, DROP COLUMN food_id, DROP COLUMN id;
ALTER TABLE workout_sets        DROP COLUMN workout_id,  DROP COLUMN id;

ALTER TABLE foods          DROP COLUMN id;
ALTER TABLE meals          DROP COLUMN id;
ALTER TABLE meal_templates DROP COLUMN id;
ALTER TABLE workouts       DROP COLUMN id;
ALTER TABLE weight_log     DROP COLUMN id;

-- ── 4. Rename the UUID columns into place and restore the keys ─────────────
ALTER TABLE foods          RENAME COLUMN new_id TO id;
ALTER TABLE meals          RENAME COLUMN new_id TO id;
ALTER TABLE meal_templates RENAME COLUMN new_id TO id;
ALTER TABLE workouts       RENAME COLUMN new_id TO id;
ALTER TABLE weight_log     RENAME COLUMN new_id TO id;

ALTER TABLE foods          ADD PRIMARY KEY (id);
ALTER TABLE meals          ADD PRIMARY KEY (id);
ALTER TABLE meal_templates ADD PRIMARY KEY (id);
ALTER TABLE workouts       ADD PRIMARY KEY (id);
ALTER TABLE weight_log     ADD PRIMARY KEY (id);

ALTER TABLE meal_items RENAME COLUMN new_id      TO id;
ALTER TABLE meal_items RENAME COLUMN new_meal_id TO meal_id;
ALTER TABLE meal_items RENAME COLUMN new_food_id TO food_id;
ALTER TABLE meal_items
    ADD PRIMARY KEY (id),
    ADD CONSTRAINT meal_items_meal_id_fkey FOREIGN KEY (meal_id) REFERENCES meals(id) ON DELETE CASCADE,
    ADD CONSTRAINT meal_items_food_id_fkey FOREIGN KEY (food_id) REFERENCES foods(id) ON DELETE RESTRICT;
CREATE INDEX idx_meal_items_meal ON meal_items (meal_id);

ALTER TABLE meal_template_items RENAME COLUMN new_id          TO id;
ALTER TABLE meal_template_items RENAME COLUMN new_template_id TO template_id;
ALTER TABLE meal_template_items RENAME COLUMN new_food_id     TO food_id;
ALTER TABLE meal_template_items
    ADD PRIMARY KEY (id),
    ADD CONSTRAINT meal_template_items_template_id_fkey FOREIGN KEY (template_id) REFERENCES meal_templates(id) ON DELETE CASCADE,
    ADD CONSTRAINT meal_template_items_food_id_fkey     FOREIGN KEY (food_id)     REFERENCES foods(id)          ON DELETE RESTRICT;

ALTER TABLE workout_sets RENAME COLUMN new_id         TO id;
ALTER TABLE workout_sets RENAME COLUMN new_workout_id TO workout_id;
ALTER TABLE workout_sets
    ADD PRIMARY KEY (id),
    ADD CONSTRAINT workout_sets_workout_id_fkey FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE;
