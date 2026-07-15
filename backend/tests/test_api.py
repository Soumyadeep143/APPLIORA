import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["APPLIORA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _register(name: str, password: str = "hunter22"):
    return client.post("/api/auth/register", json={"name": name, "password": password})


def _login(name: str, password: str = "hunter22"):
    return client.post("/api/auth/login", json={"name": name, "password": password})


SAMPLE_USER_ID = _register("Soumyadeep").json()["id"]

SAMPLE_JOB = {
    "url": "https://careers.microsoft.com/us/en/job/12345",
    "title": "Senior Software Engineer",
    "company": "Microsoft",
    "description": "Build cloud services.",
    "deadline": "2026-08-31",
    "location": "Hyderabad, India",
    "user_id": SAMPLE_USER_ID,
}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_then_login():
    _register("Priya")
    response = _login("priya")  # case-insensitive name match
    assert response.status_code == 200
    assert response.json()["name"] == "Priya"


def test_register_rejects_duplicate_name():
    _register("Chandra")
    response = _register("chandra")  # case-insensitive collision
    assert response.status_code == 409


def test_register_rejects_short_password():
    response = _register("Shorty", "abc")
    assert response.status_code == 422


def test_login_rejects_wrong_password():
    _register("Devika")
    response = _login("Devika", "not-the-password")
    assert response.status_code == 401


def test_login_rejects_unknown_name():
    response = _login("NobodyRegisteredThisName")
    assert response.status_code == 401


def test_register_rejects_blank_name():
    response = _register("   ")
    assert response.status_code == 422


def test_password_hash_never_returned():
    response = _register("Faisal")
    assert "password_hash" not in response.json()
    assert "password" not in response.json()


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


def test_create_job_rejects_unknown_user_id():
    response = client.post("/api/jobs", json={**SAMPLE_JOB, "user_id": 999999})
    assert response.status_code == 400


def test_extract_rejects_bad_url():
    response = client.post("/api/extract", json={"url": "ftp://example.com/x"})
    assert response.status_code == 422


def test_extract_accepts_pasted_text():
    response = client.post(
        "/api/extract",
        json={"text": "Role: Data Analyst at Zomato\nApply by: 1 September 2026"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Data Analyst"
    assert body["company"] == "Zomato"
    assert body["fetch_ok"] is True


def test_extract_requires_url_or_text():
    response = client.post("/api/extract", json={})
    assert response.status_code == 422
