"""Thin HTTP client the Streamlit UI uses to talk to Module 1's own FastAPI
backend (app/) — the UI no longer imports services directly in-process."""

import os

import httpx

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
HEADERS = {"X-User-Id": "demo-reviewer", "X-User-Role": "reviewer"}


class ApiError(Exception):
    pass


def extract(files: list[tuple[str, bytes]]) -> dict:
    multipart = [("files", (name, content)) for name, content in files]
    response = httpx.post(f"{API_BASE_URL}/api/vendors/extract", files=multipart, headers=HEADERS, timeout=120)
    response.raise_for_status()
    return response.json()


def save_vendor(profile: dict) -> dict:
    response = httpx.post(f"{API_BASE_URL}/api/vendors", json=profile, headers=HEADERS, timeout=30)
    if response.status_code >= 400:
        raise ApiError(response.json().get("detail", response.text))
    return response.json()


def search_vendors(query: str) -> list[dict]:
    response = httpx.get(f"{API_BASE_URL}/api/vendors", params={"query": query}, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def get_vendor(vendor_id: int) -> dict:
    response = httpx.get(f"{API_BASE_URL}/api/vendors/{vendor_id}", headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()
