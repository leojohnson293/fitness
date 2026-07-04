"""
tests/test_foods.py
────────────────────
Unit tests for the /foods endpoints.
Database is mocked via conftest.py — no real PostgreSQL needed.
External Open Food Facts API is mocked inline.
"""
 
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'fitness_app'))
 
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import main
 
client = TestClient(main.app)
 
FAKE_FOOD = {
    "id": 1, "name": "PhD Whey Protein", "brand": "PhD",
    "source": "custom", "external_id": None,
    "kcal_per_100g": 400.0, "protein_per_100g": 80.0,
    "carbs_per_100g": 6.0, "fat_per_100g": 8.0,
    "fibre_per_100g": 2.0, "created_at": "2026-07-04T07:00:00",
}
 
 
# ── POST /foods/ ───────────────────────────────────────────────────────────────
 
def test_create_food(mock_db_pool):
    mock_db_pool.fetchrow.return_value = FAKE_FOOD
    response = client.post("/foods/", json={
        "name": "PhD Whey Protein", "brand": "PhD",
        "kcal_per_100g": 400.0, "protein_per_100g": 80.0,
        "carbs_per_100g": 6.0, "fat_per_100g": 8.0,
    })
    assert response.status_code == 201
    assert response.json()["name"] == "PhD Whey Protein"
 
 
def test_create_food_missing_name():
    response = client.post("/foods/", json={"kcal_per_100g": 400.0})
    assert response.status_code == 422
 
 
# ── GET /foods/ ────────────────────────────────────────────────────────────────
 
def test_list_foods_returns_200(mock_db_pool):
    mock_db_pool.fetch.return_value = []
    response = client.get("/foods/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
 
 
def test_list_foods_with_data(mock_db_pool):
    mock_db_pool.fetch.return_value = [FAKE_FOOD]
    response = client.get("/foods/")
    assert response.status_code == 200
    assert len(response.json()) == 1
 
 
def test_list_foods_with_limit(mock_db_pool):
    mock_db_pool.fetch.return_value = []
    response = client.get("/foods/?limit=10")
    assert response.status_code == 200
 
 
# ── GET /foods/search ──────────────────────────────────────────────────────────
 
def test_search_local_returns_200(mock_db_pool):
    mock_db_pool.fetch.return_value = [FAKE_FOOD]
    response = client.get("/foods/search?q=phd")
    assert response.status_code == 200
 
 
def test_search_local_empty_results(mock_db_pool):
    mock_db_pool.fetch.return_value = []
    response = client.get("/foods/search?q=xyz")
    assert response.status_code == 200
    assert response.json() == []
 
 
def test_search_local_missing_query():
    response = client.get("/foods/search")
    assert response.status_code == 422
 
 
# ── GET /foods/{id} ────────────────────────────────────────────────────────────
 
def test_get_food_found(mock_db_pool):
    mock_db_pool.fetchrow.return_value = FAKE_FOOD
    response = client.get("/foods/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1
 
 
def test_get_food_not_found(mock_db_pool):
    mock_db_pool.fetchrow.return_value = None
    response = client.get("/foods/99999")
    assert response.status_code == 404
 
 
# ── DELETE /foods/{id} ─────────────────────────────────────────────────────────
 
def test_delete_food_success(mock_db_pool):
    mock_db_pool.execute.return_value = "DELETE 1"
    response = client.delete("/foods/1")
    assert response.status_code == 204
 
 
def test_delete_food_not_found(mock_db_pool):
    mock_db_pool.execute.return_value = "DELETE 0"
    response = client.delete("/foods/99999")
    assert response.status_code == 404
 
 
# ── GET /foods/off/search ──────────────────────────────────────────────────────
 
def test_search_off_returns_results():
    mock_response = MagicMock()
    mock_response.json.return_value = {"hits": [{
        "code": "123456", "product_name": "Banana", "brands": "Chiquita",
        "nutriments": {
            "energy-kcal_100g": 89.0, "proteins_100g": 1.1,
            "carbohydrates_100g": 23.0, "fat_100g": 0.3, "fiber_100g": 2.6,
        }
    }]}
    mock_response.raise_for_status = MagicMock()
 
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=mock_response))
        )
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        response = client.get("/foods/off/search?q=banana")
 
    assert response.status_code == 200
    assert isinstance(response.json(), list)
 
 
def test_search_off_missing_query():
    response = client.get("/foods/off/search")
    assert response.status_code == 422
 
 
def test_search_off_filters_incomplete():
    mock_response = MagicMock()
    mock_response.json.return_value = {"hits": [{
        "code": "999", "product_name": "Incomplete Food",
        "brands": None, "nutriments": {}
    }]}
    mock_response.raise_for_status = MagicMock()
 
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=mock_response))
        )
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        response = client.get("/foods/off/search?q=incomplete")
 
    assert response.status_code == 200
    assert response.json() == []
 
