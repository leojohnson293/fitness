"""
db/migrate.py
─────────────
Runs all pending SQL migrations in order.

Usage:
    python db/migrate.py

Reads DATABASE_URL from environment (set by run.sh via .env.dev or .env.prod).
Safe to run multiple times — already-applied migrations are skipped.
"""

import asyncio
import os
import sys
from pathlib import Path
import asyncpg


async def run_migrations():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL is not set — run via run.sh or export it manually")
        sys.exit(1)

    migrations_dir = Path(__file__).parent / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        print("⚠️  No migration files found in db/migrations/")
        return

    conn = await asyncpg.connect(db_url)

    try:
        # Create migration tracking table if it doesn't exist
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id          SERIAL PRIMARY KEY,
                filename    VARCHAR(200) NOT NULL UNIQUE,
                applied_at  TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Get already-applied migrations
        applied = {
            row["filename"]
            for row in await conn.fetch("SELECT filename FROM _migrations")
        }

        pending = [f for f in migration_files if f.name not in applied]

        if not pending:
            print("✅ All migrations already applied — nothing to do")
            return

        for migration_file in pending:
            print(f"⏳ Applying {migration_file.name} ...")
            sql = migration_file.read_text()

            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO _migrations (filename) VALUES ($1)",
                    migration_file.name
                )

            print(f"✅ {migration_file.name} applied")

        print(f"\n🎉 {len(pending)} migration(s) applied successfully")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_migrations())
