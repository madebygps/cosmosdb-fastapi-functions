import os
import pytest
import requests

BASE = os.environ.get("FUNCTIONS_BASE_URL", "http://127.0.0.1:7071")
API_KEY = os.environ.get("FUNCTIONS_TEST_KEY")

pytestmark = pytest.mark.integration


def skip_if_not_local():
    # Guard: don't run integration tests unless explicitly allowed or pointing at emulator
    endpoint = os.environ.get("COSMOSDB_ENDPOINT", "")
    if endpoint and not (
        endpoint.startswith("https://localhost")
        or endpoint.startswith("http://localhost")
        or os.environ.get("RUN_INTEGRATION", "") == "1"
    ):
        pytest.skip(
            "Integration tests are gated to local emulator or RUN_INTEGRATION=1"
        )


def test_health():
    skip_if_not_local()
    headers = {"x-functions-key": API_KEY} if API_KEY else {}
    r = requests.get(f"{BASE}/api/health", headers=headers)
    assert r.status_code in (200, 404)


def test_create_and_delete_cycle():
    skip_if_not_local()
    if not API_KEY:
        pytest.skip("FUNCTIONS_TEST_KEY not set for integration tests")
    headers = {"x-functions-key": API_KEY}

    payload = {
        "name": "ITest",
        "description": "integration test",
        "category": "Gadgets",
        "price": 1.23,
        "sku": "ITEST-1",
        "quantity": 1,
    }
    r = requests.post(f"{BASE}/products/", json=payload, headers=headers)
    assert r.status_code == 201
    data = r.json()
    product_id = data["id"]

    # fetch
    r2 = requests.get(
        f"{BASE}/products/{product_id}", params={"category": "Gadgets"}, headers=headers
    )
    assert r2.status_code == 200

    # delete
    r3 = requests.delete(
        f"{BASE}/products/{product_id}", params={"category": "Gadgets"}, headers=headers
    )
    assert r3.status_code == 204
