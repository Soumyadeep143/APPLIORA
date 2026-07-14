import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["APPLIORA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

SAMPLE_JOB = {
    "url": "https://careers.microsoft.com/us/en/job/12345",
    "title": "Senior Software Engineer",
    "company": "Microsoft",
    "description": "Build cloud services.",
    "deadline": "2026-08-31",
    "location": "Hyderabad, India",
    "shared_by": "Soumyadeep",
}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_and_list_job():
    response = client.post("/api/jobs", json=SAMPLE_JOB)
    assert response.status_code == 201
    created = response.json()
    assert created["title"] == "Senior Software Engineer"
    assert created["company"] == "Microsoft"
    assert created["source"] == "careers.microsoft.com"
    assert created["shared_by"] == "Soumyadeep"

    listing = client.get("/api/jobs").json()
    assert any(job["id"] == created["id"] for job in listing)


def test_search_jobs():
    client.post("/api/jobs", json={**SAMPLE_JOB, "title": "Data Scientist", "company": "Netflix"})
    results = client.get("/api/jobs", params={"search": "Netflix"}).json()
    assert results and all("Netflix" in job["company"] for job in results)


def test_get_and_delete_job():
    created = client.post("/api/jobs", json=SAMPLE_JOB).json()
    job_id = created["id"]

    assert client.get(f"/api/jobs/{job_id}").status_code == 200
    assert client.delete(f"/api/jobs/{job_id}").status_code == 204
    assert client.get(f"/api/jobs/{job_id}").status_code == 404
    assert client.delete(f"/api/jobs/{job_id}").status_code == 404


def test_create_job_rejects_bad_url():
    response = client.post("/api/jobs", json={**SAMPLE_JOB, "url": "notaurl"})
    assert response.status_code == 422


def test_create_job_blank_name_becomes_anonymous():
    response = client.post("/api/jobs", json={**SAMPLE_JOB, "shared_by": "   "})
    assert response.json()["shared_by"] == "Anonymous"


def test_extract_rejects_bad_url():
    response = client.post("/api/extract", json={"url": "ftp://example.com/x"})
    assert response.status_code == 422
