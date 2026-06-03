"""
Fitness Tracker — FastAPI Backend
==================================
Run:
    uvicorn main:app --reload

Interactive API docs:
    http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

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


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Fitness Tracker API is running"}
