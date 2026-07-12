"""
tests/test_templates.py
────────────────────────
Unit tests for the /templates endpoints, including the new PATCH.
Database is mocked via conftest.py — no real PostgreSQL needed.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'fitness_app'))

from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

FAKE_TEMPLATE = {
    "id": 1,
    "name": "Post-gym lunch",
    "meal_type": "Lunch",
    "description": "Chicken and rice",
    "created_at": "2026-07-04T12:00:00",
}


# ── GET /templates/ ────────────────────────────────────────────────────────────

def test_list_templates_returns_200(mock_db_pool):
    mock_db_pool.fetch.return_value = []
    response = client.get("/templates/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ── GET /templates/{id} ────────────────────────────────────────────────────────

def test_get_template_found(mock_db_pool):
    mock_db_pool.fetchrow.return_value = FAKE_TEMPLATE
    mock_db_pool.fetch.return_value = []  # items
    response = client.get("/templates/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Post-gym lunch"


def test_get_template_not_found(mock_db_pool):
    mock_db_pool.fetchrow.return_value = None
    response = client.get("/templates/99999")
    assert response.status_code == 404


# ── PATCH /templates/{id} ──────────────────────────────────────────────────────

def test_update_template_metadata(mock_db_pool):
    """PATCH with just a name change should return 200."""
    mock_db_pool.fetchrow.return_value = {**FAKE_TEMPLATE, "name": "Renamed lunch"}
    mock_db_pool.fetch.return_value = []
    response = client.patch("/templates/1", json={"name": "Renamed lunch"})
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed lunch"


def test_update_template_meal_type(mock_db_pool):
    """PATCH changing meal_type should return 200."""
    mock_db_pool.fetchrow.return_value = {**FAKE_TEMPLATE, "meal_type": "Dinner"}
    mock_db_pool.fetch.return_value = []
    response = client.patch("/templates/1", json={"meal_type": "Dinner"})
    assert response.status_code == 200
    assert response.json()["meal_type"] == "Dinner"


def test_update_template_items(mock_db_pool):
    """PATCH replacing items should return 200."""
    mock_db_pool.fetchrow.return_value = FAKE_TEMPLATE
    mock_db_pool.fetch.return_value = []
    response = client.patch("/templates/1", json={
        "items": [{"food_id": 2, "grams": 150}]
    })
    assert response.status_code == 200


def test_update_template_not_found(mock_db_pool):
    mock_db_pool.fetchrow.return_value = None
    response = client.patch("/templates/99999", json={"name": "Ghost"})
    assert response.status_code == 404


def test_update_template_no_fields(mock_db_pool):
    """PATCH with empty body should return 400."""
    response = client.patch("/templates/1", json={})
    assert response.status_code == 400


# ── DELETE /templates/{id} ─────────────────────────────────────────────────────

def test_delete_template_success(mock_db_pool):
    mock_db_pool.execute.return_value = "DELETE 1"
    response = client.delete("/templates/1")
    assert response.status_code == 204


def test_delete_template_not_found(mock_db_pool):
    mock_db_pool.execute.return_value = "DELETE 0"
    response = client.delete("/templates/99999")
    assert response.status_code == 404
