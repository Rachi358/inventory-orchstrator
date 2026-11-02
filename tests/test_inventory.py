
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)

HEADERS = {"X-Api-Key": settings.API_KEY_SECRET}


def test_missing_api_key():
    response = client.get("/api/v1/inventory")
    assert response.status_code == 401


def test_invalid_api_key():
    response = client.get(
        "/api/v1/inventory",
        headers={"X-Api-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_valid_api_key():
    response = client.get(
        "/api/v1/inventory",
        headers=HEADERS,
    )
    assert response.status_code == 200


def test_inventory_pagination():
    response = client.get(
        "/api/v1/inventory?limit=2&offset=0",
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) <= 2


def test_inventory_offset():
    page_1 = client.get(
        "/api/v1/inventory?limit=2&offset=0",
        headers=HEADERS,
    ).json()

    page_2 = client.get(
        "/api/v1/inventory?limit=2&offset=2",
        headers=HEADERS,
    ).json()

    page_1_skus = {item["sku"] for item in page_1["items"]}
    page_2_skus = {item["sku"] for item in page_2["items"]}

    assert page_1_skus.isdisjoint(page_2_skus)


def test_health_endpoint_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"



def test_reconciliation_returns_202():
    payload = {
        "items": [
            {"sku": "LAPTOP001", "stock_quantity": 50},
            {"sku": "MOUSE001", "stock_quantity": 150}
        ]
    }

    response = client.post(
        "/api/v1/inventory/reconcile",
        json=payload,
        headers=HEADERS,
    )

    assert response.status_code == 202
    assert response.json()["status"] == "PROCESSING"
    assert response.json()["items_received"] == 2


def test_reconciliation_persists_audit_log():
    payload = {
        "items": [
            {"sku": "LAPTOP001", "stock_quantity": 60}
        ]
    }

    response = client.post(
        "/api/v1/inventory/reconcile",
        json=payload,
        headers=HEADERS,
    )

    assert response.status_code == 202

    # BackgroundTasks complete before TestClient returns.
    audit_response = client.get(
        "/api/v1/inventory/audit-logs",
        headers=HEADERS,
    )

    assert audit_response.status_code == 200

    audit_data = audit_response.json()
    assert audit_data["count"] >= 1

    latest_log = audit_data["items"][0]
    assert latest_log["status"] == "SUCCESS"
    assert latest_log["skus_processed"] >= 1


def test_duplicate_sku_returns_422():
    payload = {
        "items": [
            {"sku": "LAPTOP001", "stock_quantity": 50},
            {"sku": "LAPTOP001", "stock_quantity": 70},
        ]
    }

    response = client.post(
        "/api/v1/inventory/reconcile",
        json=payload,
        headers=HEADERS,
    )

    assert response.status_code == 422


def test_unknown_sku_fails_reconciliation():
    payload = {
        "items": [
            {"sku": "UNKNOWN_SKU_999", "stock_quantity": 100}
        ]
    }

    response = client.post(
        "/api/v1/inventory/reconcile",
        json=payload,
        headers=HEADERS,
    )

    # Request is accepted; processing happens in the background.
    assert response.status_code == 202

    audit_response = client.get(
        "/api/v1/inventory/audit-logs",
        headers=HEADERS,
    )

    assert audit_response.status_code == 200

    audit_data = audit_response.json()
    latest_log = audit_data["items"][0]

    assert latest_log["status"] == "FAILED"
    assert latest_log["skus_processed"] == 0
    assert latest_log["error_message"] is not None
