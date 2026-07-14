"""Appliora API — share job links with friends, with auto-fetched details."""

from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

load_dotenv()  # backend/.env — GROQ_API_KEY / TAVILY_API_KEY for ai_extractor.py

from . import database
from .extractor import extract_job_metadata

app = FastAPI(
    title="Appliora API",
    description="Share job links with friends — titles, companies, "
    "descriptions and deadlines are fetched automatically.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

database.init_db()


class ExtractRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2000)

    @field_validator("url")
    @classmethod
    def must_be_http_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Please provide a valid http(s) job link.")
        return value


class JobCreate(BaseModel):
    url: str = Field(..., min_length=8, max_length=2000)
    title: str = Field(..., min_length=1, max_length=300)
    company: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=6000)
    deadline: str = Field(default="", max_length=60)
    location: str = Field(default="", max_length=200)
    source: str = Field(default="", max_length=200)
    shared_by: str = Field(default="Anonymous", max_length=80)

    @field_validator("url")
    @classmethod
    def must_be_http_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Please provide a valid http(s) job link.")
        return value

    @field_validator("shared_by")
    @classmethod
    def default_name(cls, value: str) -> str:
        return value.strip() or "Anonymous"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "appliora"}


@app.post("/api/extract")
def extract(request: ExtractRequest) -> dict:
    """Fetch a job link and return whatever details could be detected.

    Nothing is saved — the frontend shows an editable preview first.
    """
    return extract_job_metadata(request.url)


@app.get("/api/jobs")
def get_jobs(search: str = Query(default="", max_length=200)) -> list[dict]:
    return database.list_jobs(search.strip())


@app.post("/api/jobs", status_code=201)
def create_job(job: JobCreate) -> dict:
    payload = job.model_dump()
    if not payload["source"]:
        payload["source"] = urlparse(payload["url"]).netloc
    return database.insert_job(payload)


@app.get("/api/jobs/{job_id}")
def get_single_job(job_id: int) -> dict:
    job = database.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.delete("/api/jobs/{job_id}", status_code=204)
def remove_job(job_id: int) -> None:
    if not database.delete_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
