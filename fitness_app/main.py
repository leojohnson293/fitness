"""
Fitness Tracker — FastAPI Backend
==================================
Run:
    ./run.sh        → dev  (port 8001, fitness_dev db)
    ./run.sh prod   → prod (port 8000, fitness db)
    python main.py  → reads PORT env var (default 8001)

Interactive API docs:
    http://localhost:<PORT>/docs
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database import create_tables
from routers import meals, weight, workouts, foods, templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title="Fitness Tracker API",
    description="CRUD API for diet, weight and workout logging.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meals.router,     prefix="/meals",     tags=["Meals"])
app.include_router(foods.router,     prefix="/foods",     tags=["Foods"])
app.include_router(templates.router, prefix="/templates", tags=["Templates"])
app.include_router(weight.router,    prefix="/weight",    tags=["Weight"])
app.include_router(workouts.router,  prefix="/workouts",  tags=["Workouts"])


@app.get("/", tags=["Frontend"], include_in_schema=False)
async def serve_frontend():
    return FileResponse("index.html")

@app.get("/health", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Fitness Tracker API is running"}


if __name__ == "__main__":
    # Read PORT from environment so dev (.env.dev=8001) and prod (.env.prod=8000)
    # are picked up automatically. Defaults to 8000 (prod) if not set.
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
