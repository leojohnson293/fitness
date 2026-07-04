"""
tests/test_meals.py
────────────────────
Unit tests for the /meals endpoints.
Database is mocked via conftest.py — no real PostgreSQL needed.
"""
 
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'fitness_app'))
 
from fastapi.testclient import TestClient
import main
 
client = TestClient(main.app)
 
 
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
        "id": 1, "log_date": "2026-07-03", "meal_type": "lunch",
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
 
 
# ── GET /meals/{id} ────────────────────────────────────────────────────────────
 
def test_get_meal_not_found(mock_db_pool):
    mock_db_pool.fetchrow.return_value = None
    response = client.get("/meals/99999")
    assert response.status_code == 404
 
 
def test_get_meal_found(mock_db_pool):
    mock_db_pool.fetchrow.return_value = {
        "id": 1, "log_date": "2026-07-03", "meal_type": "lunch",
        "description": "Test meal", "calories": 500, "protein_g": 40.0,
        "carbs_g": 50.0, "fat_g": 15.0, "fibre_g": 5.0,
        "created_at": "2026-07-03T12:00:00",
    }
    mock_db_pool.fetch.return_value = []
    response = client.get("/meals/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1
 
 
# ── DELETE /meals/{id} ─────────────────────────────────────────────────────────
 
def test_delete_meal_not_found(mock_db_pool):
    mock_db_pool.execute.return_value = "DELETE 0"
    response = client.delete("/meals/99999")
    assert response.status_code == 404
 
 
def test_delete_meal_success(mock_db_pool):
    mock_db_pool.execute.return_value = "DELETE 1"
    response = client.delete("/meals/1")
    assert response.status_code == 204
 
 
# ── GET /meals/summary ─────────────────────────────────────────────────────────
 
def test_nutrition_summary_returns_200(mock_db_pool):
    mock_db_pool.fetch.return_value = []
    response = client.get("/meals/summary")
    assert response.status_code == 200
    assert isinstance(response.json(), list)