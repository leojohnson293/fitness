"""
tests/test_meals.py
────────────────────
Unit tests for the /meals endpoints.
Database is mocked via conftest.py — no real PostgreSQL needed.
"""
 
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'fitness_app'))
 
from uuid import UUID
from fastapi.testclient import TestClient
import main
 
client = TestClient(main.app)

FAKE_ID    = "00000000-0000-0000-0000-000000000001"
MISSING_ID = "00000000-0000-0000-0000-000000099999"
 
 
# ── Health check ───────────────────────────────────────────────────────────────
 
def test_health_check():
    """App should return 200 on /health."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
 
 
def test_root_serves_html():
    """Root route should serve the frontend HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
 
 
# ── GET /meals/ ────────────────────────────────────────────────────────────────
 
def test_list_meals_returns_200(mock_db_pool):
    mock_db_pool.fetch.return_value = []
    response = client.get("/meals/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
 
 
def test_list_meals_with_limit(mock_db_pool):
    mock_db_pool.fetch.return_value = []
    response = client.get("/meals/?limit=10")
    assert response.status_code == 200
 
 
def test_list_meals_with_date_filter(mock_db_pool):
    mock_db_pool.fetch.return_value = []
    response = client.get("/meals/?start_date=2026-01-01&end_date=2026-12-31")
    assert response.status_code == 200
 
 
# ── POST /meals/ ───────────────────────────────────────────────────────────────
 
def test_create_meal_quick_log(mock_db_pool):
    mock_db_pool.fetchrow.return_value = {
        "id": FAKE_ID, "log_date": "2026-07-03", "meal_type": "lunch",
        "description": "Test meal", "calories": 500, "protein_g": 40.0,
        "carbs_g": 50.0, "fat_g": 15.0, "fibre_g": 5.0,
        "created_at": "2026-07-03T12:00:00",
    }
    mock_db_pool.fetch.return_value = []
    response = client.post("/meals/", json={
        "log_date": "2026-07-03", "meal_type": "lunch",
        "description": "Test meal", "calories": 500,
        "protein_g": 40.0, "carbs_g": 50.0, "fat_g": 15.0,
        "fibre_g": 5.0, "items": []
    })
    assert response.status_code == 201
 
 
def test_create_meal_missing_date():
    response = client.post("/meals/", json={"meal_type": "lunch", "calories": 500})
    assert response.status_code == 422


def test_create_meal_with_items_matches_food_by_uuid(mock_db_pool):
    """asyncpg returns UUID objects — the food lookup must match them against item.food_id."""
    food_row = {
        "id": UUID(FAKE_ID), "kcal_per_100g": 400.0, "protein_per_100g": 80.0,
        "carbs_per_100g": 6.0, "fat_per_100g": 8.0, "fibre_per_100g": 2.0,
    }
    mock_db_pool.fetch.side_effect = [[food_row], []]  # foods lookup, then meal items
    mock_db_pool.fetchrow.return_value = {
        "id": UUID(FAKE_ID), "log_date": "2026-07-03", "meal_type": "snack",
        "description": "Shake", "calories": 120, "protein_g": 24.0,
        "carbs_g": 1.8, "fat_g": 2.4, "fibre_g": 0.6,
        "created_at": "2026-07-03T12:00:00",
    }
    response = client.post("/meals/", json={
        "log_date": "2026-07-03", "meal_type": "snack",
        "items": [{"food_id": FAKE_ID, "grams": 30}],
    })
    assert response.status_code == 201
 
 
# ── GET /meals/{id} ────────────────────────────────────────────────────────────
 
def test_get_meal_not_found(mock_db_pool):
    mock_db_pool.fetchrow.return_value = None
    response = client.get(f"/meals/{MISSING_ID}")
    assert response.status_code == 404


def test_get_meal_malformed_id():
    """A non-UUID id is rejected by FastAPI before reaching the database."""
    response = client.get("/meals/42")
    assert response.status_code == 422
 
 
def test_get_meal_found(mock_db_pool):
    mock_db_pool.fetchrow.return_value = {
        "id": FAKE_ID, "log_date": "2026-07-03", "meal_type": "lunch",
        "description": "Test meal", "calories": 500, "protein_g": 40.0,
        "carbs_g": 50.0, "fat_g": 15.0, "fibre_g": 5.0,
        "created_at": "2026-07-03T12:00:00",
    }
    mock_db_pool.fetch.return_value = []
    response = client.get(f"/meals/{FAKE_ID}")
    assert response.status_code == 200
    assert response.json()["id"] == FAKE_ID
 
 
# ── DELETE /meals/{id} ─────────────────────────────────────────────────────────
 
def test_delete_meal_not_found(mock_db_pool):
    mock_db_pool.execute.return_value = "DELETE 0"
    response = client.delete(f"/meals/{MISSING_ID}")
    assert response.status_code == 404
 
 
def test_delete_meal_success(mock_db_pool):
    mock_db_pool.execute.return_value = "DELETE 1"
    response = client.delete(f"/meals/{FAKE_ID}")
    assert response.status_code == 204
 
 
# ── GET /meals/summary ─────────────────────────────────────────────────────────
 
def test_nutrition_summary_returns_200(mock_db_pool):
    mock_db_pool.fetch.return_value = []
    response = client.get("/meals/summary")
    assert response.status_code == 200
    assert isinstance(response.json(), list)