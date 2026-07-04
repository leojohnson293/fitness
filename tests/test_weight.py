
"""
tests/test_weight.py
─────────────────────
Unit tests for the /weight endpoints.
Database is mocked via conftest.py — no real PostgreSQL needed.
"""
 
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'fitness_app'))
 
from fastapi.testclient import TestClient
import main
 
client = TestClient(main.app)
 
FAKE_ENTRY = {
    "id": 1, "log_date": "2026-07-04", "weight_kg": 83.0,
    "waist_cm": None, "notes": None,
    "created_at": "2026-07-04T07:00:00", "rolling_7d_avg": 83.0,
}
 
 
# ── POST /weight/ ──────────────────────────────────────────────────────────────
 
def test_create_weight_entry(mock_db_pool):
    mock_db_pool.fetchrow.return_value = FAKE_ENTRY
    response = client.post("/weight/", json={"log_date": "2026-07-04", "weight_kg": 83.0})
    assert response.status_code == 201
    assert response.json()["weight_kg"] == 83.0
 
 
def test_create_weight_entry_with_waist(mock_db_pool):
    mock_db_pool.fetchrow.return_value = {**FAKE_ENTRY, "waist_cm": 85.0}
    response = client.post("/weight/", json={"log_date": "2026-07-04", "weight_kg": 83.0, "waist_cm": 85.0})
    assert response.status_code == 201
    assert response.json()["waist_cm"] == 85.0
 
 
def test_create_weight_entry_missing_weight():
    response = client.post("/weight/", json={"log_date": "2026-07-04"})
    assert response.status_code == 422
 
 
def test_create_weight_entry_missing_date():
    response = client.post("/weight/", json={"weight_kg": 83.0})
    assert response.status_code == 422
 
 
# ── GET /weight/ ───────────────────────────────────────────────────────────────
 
def test_list_weight_entries_returns_200(mock_db_pool):
    mock_db_pool.fetch.return_value = []
    response = client.get("/weight/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
 
 
def test_list_weight_entries_with_data(mock_db_pool):
    mock_db_pool.fetch.return_value = [FAKE_ENTRY]
    response = client.get("/weight/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["weight_kg"] == 83.0
 
 
def test_list_weight_entries_with_limit(mock_db_pool):
    mock_db_pool.fetch.return_value = []
    response = client.get("/weight/?limit=7")
    assert response.status_code == 200
 
 
def test_list_weight_entries_with_date_filter(mock_db_pool):
    mock_db_pool.fetch.return_value = []
    response = client.get("/weight/?start_date=2026-01-01&end_date=2026-12-31")
    assert response.status_code == 200
 
 
# ── GET /weight/{id} ───────────────────────────────────────────────────────────
 
def test_get_weight_entry_found(mock_db_pool):
    mock_db_pool.fetchrow.return_value = FAKE_ENTRY
    response = client.get("/weight/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1
 
 
def test_get_weight_entry_not_found(mock_db_pool):
    mock_db_pool.fetchrow.return_value = None
    response = client.get("/weight/99999")
    assert response.status_code == 404
 
 
# ── PATCH /weight/{id} ─────────────────────────────────────────────────────────
 
def test_update_weight_entry(mock_db_pool):
    mock_db_pool.fetchrow.return_value = {**FAKE_ENTRY, "weight_kg": 82.5}
    response = client.patch("/weight/1", json={"weight_kg": 82.5})
    assert response.status_code == 200
    assert response.json()["weight_kg"] == 82.5
 
 
def test_update_weight_entry_not_found(mock_db_pool):
    mock_db_pool.fetchrow.return_value = None
    response = client.patch("/weight/99999", json={"weight_kg": 82.5})
    assert response.status_code == 404
 
 
def test_update_weight_entry_no_fields():
    response = client.patch("/weight/1", json={})
    assert response.status_code == 400
 
 
# ── DELETE /weight/{id} ────────────────────────────────────────────────────────
 
def test_delete_weight_entry_success(mock_db_pool):
    mock_db_pool.execute.return_value = "DELETE 1"
    response = client.delete("/weight/1")
    assert response.status_code == 204
 
 
def test_delete_weight_entry_not_found(mock_db_pool):
    mock_db_pool.execute.return_value = "DELETE 0"
    response = client.delete("/weight/99999")
    assert response.status_code == 404
