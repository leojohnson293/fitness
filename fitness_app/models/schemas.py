"""
Pydantic schemas for request validation and response serialisation.
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ── Foods ─────────────────────────────────────────────────────────────────────

class FoodBase(BaseModel):
    name:             str
    brand:            Optional[str]   = None
    kcal_per_100g:    Optional[float] = Field(None, ge=0)
    protein_per_100g: Optional[float] = Field(None, ge=0)
    carbs_per_100g:   Optional[float] = Field(None, ge=0)
    fat_per_100g:     Optional[float] = Field(None, ge=0)
    fibre_per_100g:   Optional[float] = Field(None, ge=0)

class FoodCreate(FoodBase):
    source:      Optional[str] = "custom"
    external_id: Optional[str] = None

class FoodOut(FoodBase):
    id:          int
    source:      str
    external_id: Optional[str]
    created_at:  datetime

    class Config:
        from_attributes = True


# ── Meal items ────────────────────────────────────────────────────────────────

class MealItemCreate(BaseModel):
    food_id: int
    grams:   float = Field(..., gt=0)

class MealItemOut(BaseModel):
    id:      int
    food_id: int
    grams:   float
    food:    Optional[FoodOut] = None  # populated on read

    class Config:
        from_attributes = True


# ── Meals ─────────────────────────────────────────────────────────────────────
# Two ways to log a meal:
#   1. Pass `items` (list of food_id + grams) — macros calculated automatically
#   2. Pass macro fields directly (legacy / quick log without food library)

class MealCreate(BaseModel):
    log_date:    date
    meal_type:   Optional[str] = None
    description: Optional[str] = None
    # Direct macros (used when no items provided)
    calories:    Optional[int]   = Field(None, ge=0)
    protein_g:   Optional[float] = Field(None, ge=0)
    carbs_g:     Optional[float] = Field(None, ge=0)
    fat_g:       Optional[float] = Field(None, ge=0)
    fibre_g:     Optional[float] = Field(None, ge=0)
    # Food items (preferred — auto-calculates macros)
    items:       List[MealItemCreate] = []

class MealUpdate(BaseModel):
    meal_type:   Optional[str]   = None
    description: Optional[str]   = None
    calories:    Optional[int]   = None
    protein_g:   Optional[float] = None
    carbs_g:     Optional[float] = None
    fat_g:       Optional[float] = None
    fibre_g:     Optional[float] = None

class MealOut(BaseModel):
    id:          int
    log_date:    date
    meal_type:   Optional[str]
    description: Optional[str]
    calories:    Optional[int]
    protein_g:   Optional[float]
    carbs_g:     Optional[float]
    fat_g:       Optional[float]
    fibre_g:     Optional[float]
    items:       List[MealItemOut] = []
    created_at:  datetime

    class Config:
        from_attributes = True


# ── Meal templates ────────────────────────────────────────────────────────────

class TemplateCreate(BaseModel):
    name:        str
    meal_type:   Optional[str] = None
    description: Optional[str] = None
    items:       List[MealItemCreate] = []

class TemplateOut(BaseModel):
    id:          int
    name:        str
    meal_type:   Optional[str]
    description: Optional[str]
    items:       List[MealItemOut] = []
    created_at:  datetime


# ── Weight ────────────────────────────────────────────────────────────────────

class WeightCreate(BaseModel):
    log_date:  date
    weight_kg: float = Field(..., gt=0)
    waist_cm:  Optional[float] = None
    notes:     Optional[str]   = None

class WeightUpdate(BaseModel):
    weight_kg: Optional[float] = None
    waist_cm:  Optional[float] = None
    notes:     Optional[str]   = None

class WeightOut(WeightCreate):
    id:              int
    rolling_7d_avg:  Optional[float] = None
    created_at:      datetime

    class Config:
        from_attributes = True


# ── Workouts ──────────────────────────────────────────────────────────────────

class SetCreate(BaseModel):
    exercise:   str
    set_number: int = Field(..., ge=1)
    reps:       Optional[int]   = Field(None, ge=0)
    weight_kg:  Optional[float] = Field(None, ge=0)
    notes:      Optional[str]   = None

class SetOut(SetCreate):
    id:         int
    workout_id: int

    class Config:
        from_attributes = True

class WorkoutCreate(BaseModel):
    log_date:     date
    session_type: Optional[str] = None
    duration_min: Optional[int] = None
    rpe:          Optional[int] = Field(None, ge=1, le=10)
    notes:        Optional[str] = None
    sets:         List[SetCreate] = []

class WorkoutUpdate(BaseModel):
    session_type: Optional[str] = None
    duration_min: Optional[int] = None
    rpe:          Optional[int] = Field(None, ge=1, le=10)
    notes:        Optional[str] = None

class WorkoutOut(BaseModel):
    id:           int
    log_date:     date
    session_type: Optional[str]
    duration_min: Optional[int]
    rpe:          Optional[int]
    notes:        Optional[str]
    created_at:   datetime
    sets:         List[SetOut] = []

    class Config:
        from_attributes = True


# ── Summary ───────────────────────────────────────────────────────────────────

class DailyNutrition(BaseModel):
    log_date:        date
    total_kcal:      Optional[float]
    total_protein_g: Optional[float]
    total_carbs_g:   Optional[float]
    total_fat_g:     Optional[float]
