import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["DEVCAREER_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
# app.main reads these at import time to seed the one hardcoded bootstrap
# superadmin account — set explicitly here (not relied on from a real
# backend/.env) so the test suite doesn't depend on what happens to be in
# the developer's local .env file.
os.environ.setdefault("MASTER_SUPERADMIN_USERNAME", "SMASTER")
os.environ.setdefault("MASTER_SUPERADMIN_PASSWORD", "Soumya@2050")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

# It's the only way to reach superadmin at all now (see
# test_registering_with_admin_like_name_does_not_grant_admin below for the
# mechanism this replaced).
MASTER_SUPERADMIN_USERNAME = os.environ["MASTER_SUPERADMIN_USERNAME"]
MASTER_SUPERADMIN_PASSWORD = os.environ["MASTER_SUPERADMIN_PASSWORD"]


def _username_for(name: str) -> str:
    """PRD.md Task 6.7: register/login now take a separate `username` from
    the display `name`. Existing tests only ever dealt with one string per
    account, so every call site here still just passes a `name` — this
    derives a matching username the same simple way for both _register and
    _login, so passing the same `name` to each still refers to the same
    account without touching the 35+ existing call sites."""
    return re.sub(r"[^A-Za-z0-9._-]", "", name).lower()


def _register(name: str, password: str = "Hunter1!", referral_code: str = ""):
    username = _username_for(name)
    return client.post(
        "/api/auth/register",
        json={
            "username": username,
            "name": name,
            "email": f"{username or 'blank'}@example.com",
            "password": password,
            "referral_code": referral_code,
        },
    )


def _login(name: str, password: str = "Hunter1!"):
    return client.post(
        "/api/auth/login", json={"username": _username_for(name), "password": password}
    )


def _delete_job(job_id, admin_user_id):
    return client.delete(f"/api/jobs/{job_id}", params={"admin_user_id": admin_user_id})


SAMPLE_USER_ID = _register("Soumyadeep").json()["id"]

SUPERADMIN_USER_ID = client.post(
    "/api/auth/login",
    json={"username": MASTER_SUPERADMIN_USERNAME, "password": MASTER_SUPERADMIN_PASSWORD},
).json()["id"]

_admin_seed = _register("AdminUser").json()
client.patch(
    f"/api/admin/users/{_admin_seed['id']}/admin",
    json={"is_admin": True},
    params={"superadmin_user_id": SUPERADMIN_USER_ID},
)
ADMIN_USER_ID = _admin_seed["id"]

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


def test_register_rejects_duplicate_username_case_insensitive():
    """`_register` derives username from name (see _username_for above), so
    "Chandra" and "chandra" collide on the same derived username — this is
    a username collision, not a display-name one (see
    test_register_allows_duplicate_display_name for that case)."""
    _register("Chandra")
    response = _register("chandra")  # case-insensitive collision
    assert response.status_code == 409


def test_register_rejects_short_password():
    response = _register("Shorty", "abc")
    assert response.status_code == 422


def test_register_rejects_password_with_back_to_back_repeat():
    """2212 repeats '2' back-to-back and should be rejected, even though it
    otherwise mixes letters/digits/specials."""
    response = _register("Repeater", "Ab2212!x")
    assert response.status_code == 422


def test_register_allows_password_with_spaced_out_repeat():
    """2121 repeats '2' and '1' but never back-to-back, so it's allowed."""
    response = _register("Spacer", "Ab2121!x")
    assert response.status_code == 201


def test_register_rejects_password_missing_special_character():
    response = _register("Plain", "Abcdef12")
    assert response.status_code == 422


def test_register_rejects_password_missing_letter():
    response = _register("Numeric", "12903475!")
    assert response.status_code == 422


def test_register_rejects_password_missing_number():
    response = _register("Alpha", "Abcdefg!")
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


def test_register_allows_duplicate_display_name():
    """PRD.md Task 6.10: only `username` is the unique handle — `name` (the
    display name) isn't, so two different accounts can both be "Alex" as
    long as their usernames differ. This used to 409 (a leftover UNIQUE
    COLLATE NOCASE on `users.name` from before username/name were split)."""
    response1 = client.post(
        "/api/auth/register",
        json={
            "username": "alexfirst",
            "name": "Alex",
            "email": "alexfirst@example.com",
            "password": "Hunter1!",
        },
    )
    assert response1.status_code == 201
    response2 = client.post(
        "/api/auth/register",
        json={
            "username": "alexsecond",
            "name": "Alex",
            "email": "alexsecond@example.com",
            "password": "Hunter1!",
        },
    )
    assert response2.status_code == 201
    assert response1.json()["id"] != response2.json()["id"]


def test_register_rejects_duplicate_username_different_display_name():
    """PRD.md Task 6.7: username is the unique login handle, independent of
    the display name. Two accounts sharing the same derived username but
    with different `name` values must still collide on username."""
    response1 = client.post(
        "/api/auth/register",
        json={
            "username": "sharedhandle",
            "name": "First Person",
            "email": "first@example.com",
            "password": "Hunter1!",
        },
    )
    assert response1.status_code == 201
    response2 = client.post(
        "/api/auth/register",
        json={
            "username": "SharedHandle",  # case-insensitive collision
            "name": "Second Person",
            "email": "second@example.com",
            "password": "Hunter1!",
        },
    )
    assert response2.status_code == 409


def test_register_rejects_duplicate_email():
    client.post(
        "/api/auth/register",
        json={
            "username": "emailowner",
            "name": "Email Owner",
            "email": "shared@example.com",
            "password": "Hunter1!",
        },
    )
    response = client.post(
        "/api/auth/register",
        json={
            "username": "emailtaker",
            "name": "Email Taker",
            "email": "shared@example.com",
            "password": "Hunter1!",
        },
    )
    assert response.status_code == 409


def test_login_uses_username_not_display_name():
    """Registering with a display name that differs from the derived
    username, then confirming login only works with the username."""
    client.post(
        "/api/auth/register",
        json={
            "username": "distincthandle",
            "name": "A Totally Different Display Name",
            "email": "distinct@example.com",
            "password": "Hunter1!",
        },
    )
    assert client.post(
        "/api/auth/login",
        json={"username": "A Totally Different Display Name", "password": "Hunter1!"},
    ).status_code == 401
    assert client.post(
        "/api/auth/login", json={"username": "distincthandle", "password": "Hunter1!"}
    ).status_code == 200


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


def test_stats_reflects_a_newly_shared_job_and_new_company():
    """Landing page headline numbers (jobs shared / distinct companies) —
    compared as deltas since other tests share this same database."""
    before = client.get("/api/stats").json()
    client.post(
        "/api/jobs", json={**SAMPLE_JOB, "company": "StatsCo" + os.urandom(3).hex()}
    )
    after = client.get("/api/stats").json()
    assert after["jobs_shared"] == before["jobs_shared"] + 1
    assert after["companies_posted"] == before["companies_posted"] + 1


def test_stats_friend_circles_counts_users_with_a_referral():
    before = client.get("/api/stats").json()
    referrer = _register("StatsReferrer" + os.urandom(3).hex()).json()
    _register("StatsReferred" + os.urandom(3).hex(), referral_code=referrer["referral_code"])
    after = client.get("/api/stats").json()
    assert after["friend_circles"] == before["friend_circles"] + 1


def test_get_and_delete_job():
    created = client.post("/api/jobs", json=SAMPLE_JOB).json()
    job_id = created["id"]

    assert client.get(f"/api/jobs/{job_id}").status_code == 200
    assert _delete_job(job_id, ADMIN_USER_ID).status_code == 204
    assert client.get(f"/api/jobs/{job_id}").status_code == 404
    assert _delete_job(job_id, ADMIN_USER_ID).status_code == 404


def test_delete_job_requires_admin():
    created = client.post("/api/jobs", json=SAMPLE_JOB).json()
    response = _delete_job(created["id"], SAMPLE_USER_ID)  # not an admin
    assert response.status_code == 403
    assert client.get(f"/api/jobs/{created['id']}").status_code == 200  # still there


def _modify_job(job_id, admin_user_id, **overrides):
    body = {**SAMPLE_JOB, **overrides}
    body.pop("user_id", None)
    return client.patch(f"/api/jobs/{job_id}", json=body, params={"admin_user_id": admin_user_id})


def test_admin_can_modify_a_job():
    created = client.post("/api/jobs", json=SAMPLE_JOB).json()
    response = _modify_job(created["id"], ADMIN_USER_ID, title="Corrected Title")
    assert response.status_code == 200
    assert response.json()["title"] == "Corrected Title"
    assert client.get(f"/api/jobs/{created['id']}").json()["title"] == "Corrected Title"


def test_superadmin_can_modify_a_job():
    created = client.post("/api/jobs", json=SAMPLE_JOB).json()
    response = _modify_job(created["id"], SUPERADMIN_USER_ID, title="Also Corrected")
    assert response.status_code == 200
    assert response.json()["title"] == "Also Corrected"


def test_regular_member_cannot_modify_a_job():
    created = client.post("/api/jobs", json=SAMPLE_JOB).json()
    response = _modify_job(created["id"], SAMPLE_USER_ID, title="Sneaky Edit")
    assert response.status_code == 403
    assert client.get(f"/api/jobs/{created['id']}").json()["title"] == SAMPLE_JOB["title"]


def test_modify_unknown_job_404():
    response = _modify_job(999999, ADMIN_USER_ID, title="Ghost")
    assert response.status_code == 404


def test_modify_job_rejects_missing_link_and_email():
    created = client.post("/api/jobs", json=SAMPLE_JOB).json()
    response = _modify_job(created["id"], ADMIN_USER_ID, url="", apply_email="")
    assert response.status_code == 422


def test_create_job_rejects_bad_url():
    response = client.post("/api/jobs", json={**SAMPLE_JOB, "url": "notaurl"})
    assert response.status_code == 422


def test_create_job_accepts_apply_email_with_no_url():
    """Task 2.4: a pasted post with no application link at all, only an
    apply-by-email address, must still be shareable — url and apply_email
    are independently optional."""
    payload = {**SAMPLE_JOB, "url": "", "apply_email": "jobs@acme.com", "apply_email_subject": "Intern"}
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["url"] == ""
    assert body["apply_email"] == "jobs@acme.com"
    assert body["apply_email_subject"] == "Intern"


def test_create_job_accepts_both_url_and_apply_email():
    payload = {**SAMPLE_JOB, "apply_email": "jobs@acme.com"}
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["url"] == SAMPLE_JOB["url"]
    assert body["apply_email"] == "jobs@acme.com"


def test_create_job_rejects_neither_url_nor_apply_email():
    response = client.post("/api/jobs", json={**SAMPLE_JOB, "url": ""})
    assert response.status_code == 422


def test_create_job_rejects_invalid_apply_email():
    response = client.post("/api/jobs", json={**SAMPLE_JOB, "apply_email": "not-an-email"})
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


def _second_user_id():
    return _register("ReactorTwo" + os.urandom(4).hex()).json()["id"]


def test_job_created_with_empty_reactions_and_comment_count():
    created = client.post("/api/jobs", json=SAMPLE_JOB).json()
    assert created["reactions"] == []
    assert created["comment_count"] == 0


def test_react_then_unreact_toggles():
    job_id = client.post("/api/jobs", json=SAMPLE_JOB).json()["id"]

    added = client.post(
        f"/api/jobs/{job_id}/reactions", json={"user_id": SAMPLE_USER_ID, "emoji": "👍"}
    )
    assert added.status_code == 200
    assert added.json() == [
        {"emoji": "👍", "user_id": SAMPLE_USER_ID, "user_name": "Soumyadeep"}
    ]

    removed = client.post(
        f"/api/jobs/{job_id}/reactions", json={"user_id": SAMPLE_USER_ID, "emoji": "👍"}
    )
    assert removed.status_code == 200
    assert removed.json() == []


def test_reaction_appears_on_job_get_and_list():
    job_id = client.post("/api/jobs", json=SAMPLE_JOB).json()["id"]
    client.post(f"/api/jobs/{job_id}/reactions", json={"user_id": SAMPLE_USER_ID, "emoji": "🔥"})

    fetched = client.get(f"/api/jobs/{job_id}").json()
    assert fetched["reactions"] == [
        {"emoji": "🔥", "user_id": SAMPLE_USER_ID, "user_name": "Soumyadeep"}
    ]

    listed = next(job for job in client.get("/api/jobs").json() if job["id"] == job_id)
    assert listed["reactions"] == fetched["reactions"]


def test_react_rejects_unsupported_emoji():
    job_id = client.post("/api/jobs", json=SAMPLE_JOB).json()["id"]
    response = client.post(
        f"/api/jobs/{job_id}/reactions", json={"user_id": SAMPLE_USER_ID, "emoji": "🐙"}
    )
    assert response.status_code == 422


def test_react_rejects_unknown_job():
    response = client.post(
        "/api/jobs/999999/reactions", json={"user_id": SAMPLE_USER_ID, "emoji": "👍"}
    )
    assert response.status_code == 404


def test_react_rejects_unknown_user():
    job_id = client.post("/api/jobs", json=SAMPLE_JOB).json()["id"]
    response = client.post(f"/api/jobs/{job_id}/reactions", json={"user_id": 999999, "emoji": "👍"})
    assert response.status_code == 400


def test_two_users_can_react_with_same_emoji_independently():
    job_id = client.post("/api/jobs", json=SAMPLE_JOB).json()["id"]
    other_id = _second_user_id()

    client.post(f"/api/jobs/{job_id}/reactions", json={"user_id": SAMPLE_USER_ID, "emoji": "🎉"})
    reactions = client.post(
        f"/api/jobs/{job_id}/reactions", json={"user_id": other_id, "emoji": "🎉"}
    ).json()
    assert len(reactions) == 2
    assert {r["user_id"] for r in reactions} == {SAMPLE_USER_ID, other_id}


def test_post_list_and_delete_comment():
    job_id = client.post("/api/jobs", json=SAMPLE_JOB).json()["id"]

    posted = client.post(
        f"/api/jobs/{job_id}/comments", json={"user_id": SAMPLE_USER_ID, "body": "Applying tonight!"}
    )
    assert posted.status_code == 201
    comment = posted.json()
    assert comment["body"] == "Applying tonight!"
    assert comment["user_name"] == "Soumyadeep"

    listed = client.get(f"/api/jobs/{job_id}/comments").json()
    assert len(listed) == 1
    assert listed[0]["id"] == comment["id"]

    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["comment_count"] == 1

    deleted = client.delete(f"/api/jobs/{job_id}/comments/{comment['id']}?user_id={SAMPLE_USER_ID}")
    assert deleted.status_code == 204
    assert client.get(f"/api/jobs/{job_id}/comments").json() == []


def test_comment_rejects_empty_body():
    job_id = client.post("/api/jobs", json=SAMPLE_JOB).json()["id"]
    response = client.post(
        f"/api/jobs/{job_id}/comments", json={"user_id": SAMPLE_USER_ID, "body": "   "}
    )
    assert response.status_code == 422


def test_comment_delete_rejects_non_author():
    job_id = client.post("/api/jobs", json=SAMPLE_JOB).json()["id"]
    other_id = _second_user_id()
    comment_id = client.post(
        f"/api/jobs/{job_id}/comments", json={"user_id": SAMPLE_USER_ID, "body": "mine"}
    ).json()["id"]

    response = client.delete(f"/api/jobs/{job_id}/comments/{comment_id}?user_id={other_id}")
    assert response.status_code == 403
    assert len(client.get(f"/api/jobs/{job_id}/comments").json()) == 1


def test_comment_delete_unknown_comment_404():
    job_id = client.post("/api/jobs", json=SAMPLE_JOB).json()["id"]
    response = client.delete(f"/api/jobs/{job_id}/comments/999999?user_id={SAMPLE_USER_ID}")
    assert response.status_code == 404


def test_deleting_job_cleans_up_reactions_and_comments():
    job_id = client.post("/api/jobs", json=SAMPLE_JOB).json()["id"]
    client.post(f"/api/jobs/{job_id}/reactions", json={"user_id": SAMPLE_USER_ID, "emoji": "👍"})
    client.post(f"/api/jobs/{job_id}/comments", json={"user_id": SAMPLE_USER_ID, "body": "hi"})

    assert _delete_job(job_id, ADMIN_USER_ID).status_code == 204
    assert client.get(f"/api/jobs/{job_id}/comments").status_code == 404


def test_register_response_has_email_and_opted_out_of_reminders_by_default():
    # PRD.md Task 6.7: email became a required registration field (it used
    # to be blank until Task 4.1's separate opt-in endpoint set one) — but
    # having an email on file still doesn't imply opted into reminders.
    body = _register("FreshSignup" + os.urandom(3).hex()).json()
    assert body["email"]
    assert body["reminders_opt_in"] is False


def test_update_notifications_sets_email_and_opt_in():
    user_id = _register("Notify" + os.urandom(3).hex()).json()["id"]
    response = client.patch(
        f"/api/users/{user_id}/notifications", json={"email": "notify@example.com", "opt_in": True}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "notify@example.com"
    assert body["reminders_opt_in"] is True
    assert "password_hash" not in body


def test_update_notifications_rejects_invalid_email():
    user_id = _register("BadEmail" + os.urandom(3).hex()).json()["id"]
    response = client.patch(
        f"/api/users/{user_id}/notifications", json={"email": "not-an-email", "opt_in": False}
    )
    assert response.status_code == 422


def test_update_notifications_rejects_opt_in_without_email():
    user_id = _register("NoEmail" + os.urandom(3).hex()).json()["id"]
    response = client.patch(f"/api/users/{user_id}/notifications", json={"email": "", "opt_in": True})
    assert response.status_code == 422


def test_update_notifications_can_clear_email_and_opt_out():
    user_id = _register("ClearMe" + os.urandom(3).hex()).json()["id"]
    client.patch(
        f"/api/users/{user_id}/notifications", json={"email": "temp@example.com", "opt_in": True}
    )
    response = client.patch(f"/api/users/{user_id}/notifications", json={"email": "", "opt_in": False})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == ""
    assert body["reminders_opt_in"] is False


def test_update_notifications_unknown_user_404():
    response = client.patch(
        "/api/users/999999/notifications", json={"email": "x@example.com", "opt_in": True}
    )
    assert response.status_code == 404


def test_update_profile_sets_social_links():
    user_id = _register("SocialSetter" + os.urandom(3).hex()).json()["id"]
    response = client.patch(
        f"/api/users/{user_id}/profile",
        json={
            "linkedin_url": "https://www.linkedin.com/in/someone",
            "github_url": "https://github.com/someone",
            "x_url": "https://x.com/someone",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["linkedin_url"] == "https://www.linkedin.com/in/someone"
    assert body["github_url"] == "https://github.com/someone"
    assert body["x_url"] == "https://x.com/someone"


def test_update_profile_allows_blank_to_clear():
    user_id = _register("SocialClearer" + os.urandom(3).hex()).json()["id"]
    client.patch(
        f"/api/users/{user_id}/profile",
        json={"linkedin_url": "https://www.linkedin.com/in/someone", "github_url": "", "x_url": ""},
    )
    response = client.patch(
        f"/api/users/{user_id}/profile",
        json={"linkedin_url": "", "github_url": "", "x_url": ""},
    )
    assert response.status_code == 200
    assert response.json()["linkedin_url"] == ""


def test_update_profile_rejects_invalid_url():
    user_id = _register("SocialBad" + os.urandom(3).hex()).json()["id"]
    response = client.patch(
        f"/api/users/{user_id}/profile",
        json={"linkedin_url": "not-a-url", "github_url": "", "x_url": ""},
    )
    assert response.status_code == 422


def test_update_profile_unknown_user_404():
    response = client.patch(
        "/api/users/999999/profile",
        json={"linkedin_url": "", "github_url": "", "x_url": ""},
    )
    assert response.status_code == 404


def test_update_profile_sets_only_one_field_leaves_rest_blank():
    """Every field is independently optional — sending only linkedin_url
    (omitting bio/skills/target_role/github_url/x_url entirely) must save
    that one field and leave the rest at their blank default, not error."""
    user_id = _register("PartialProfile" + os.urandom(3).hex()).json()["id"]
    response = client.patch(
        f"/api/users/{user_id}/profile",
        json={"linkedin_url": "https://www.linkedin.com/in/partial"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["linkedin_url"] == "https://www.linkedin.com/in/partial"
    assert body["github_url"] == ""
    assert body["bio"] == ""


def test_update_profile_sets_bio_skills_and_target_role():
    user_id = _register("BioSetter" + os.urandom(3).hex()).json()["id"]
    response = client.patch(
        f"/api/users/{user_id}/profile",
        json={"bio": "Backend engineer who loves Python.", "skills": "Python, FastAPI, SQL", "target_role": "Backend Engineer"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["bio"] == "Backend engineer who loves Python."
    assert body["skills"] == "Python, FastAPI, SQL"
    assert body["target_role"] == "Backend Engineer"

    # Modifiable after the first save, not locked in.
    updated = client.patch(
        f"/api/users/{user_id}/profile",
        json={"bio": "Updated bio.", "skills": "Python, FastAPI, SQL, Docker", "target_role": "Senior Backend Engineer"},
    ).json()
    assert updated["bio"] == "Updated bio."
    assert updated["target_role"] == "Senior Backend Engineer"


def test_get_user_profile_returns_public_fields():
    user_id = _register("ProfileViewed" + os.urandom(3).hex()).json()["id"]
    client.patch(
        f"/api/users/{user_id}/profile",
        json={
            "linkedin_url": "https://www.linkedin.com/in/someone",
            "bio": "Hi there.",
            "skills": "Go, Kubernetes",
            "target_role": "SRE",
        },
    )
    response = client.get(f"/api/users/{user_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user_id
    assert body["linkedin_url"] == "https://www.linkedin.com/in/someone"
    assert body["bio"] == "Hi there."
    assert body["skills"] == "Go, Kubernetes"
    assert body["target_role"] == "SRE"
    assert "email" not in body
    assert "reminders_opt_in" not in body


def test_get_user_profile_unknown_user_404():
    response = client.get("/api/users/999999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Referrals, rank points, admin (PRD.md Task 6.1/6.2)
# ---------------------------------------------------------------------------


def test_register_returns_a_referral_code():
    body = _register("HasCode" + os.urandom(3).hex()).json()
    assert body["referral_code"]
    assert body["rank_points"] == 0
    assert body["is_admin"] is False


def test_referral_signup_awards_points_to_referrer():
    referrer = _register("Referrer" + os.urandom(3).hex()).json()
    _register("Referred" + os.urandom(3).hex(), referral_code=referrer["referral_code"])
    refreshed = _login(referrer["name"]).json()
    assert refreshed["rank_points"] == 20


def test_unknown_referral_code_still_registers_successfully():
    response = _register("TypoCode" + os.urandom(3).hex(), referral_code="NOTAREALCODE")
    assert response.status_code == 201
    assert response.json()["rank_points"] == 0


def test_sharing_a_job_awards_points_to_sharer():
    sharer = _register("Sharer" + os.urandom(3).hex()).json()
    client.post("/api/jobs", json={**SAMPLE_JOB, "user_id": sharer["id"]})
    refreshed = _login(sharer["name"]).json()
    assert refreshed["rank_points"] == 5


def test_leaderboard_sorted_by_points_descending():
    response = client.get("/api/leaderboard")
    assert response.status_code == 200
    points = [row["rank_points"] for row in response.json()]
    assert points == sorted(points, reverse=True)


def test_admin_can_list_users():
    response = client.get("/api/admin/users", params={"admin_user_id": ADMIN_USER_ID})
    assert response.status_code == 200
    body = response.json()
    assert any(u["id"] == SAMPLE_USER_ID for u in body)
    assert "password_hash" not in body[0]


def test_non_admin_cannot_list_users():
    response = client.get("/api/admin/users", params={"admin_user_id": SAMPLE_USER_ID})
    assert response.status_code == 403


def test_superadmin_can_promote_another_user():
    target = _register("PromoteMe" + os.urandom(3).hex()).json()
    response = client.patch(
        f"/api/admin/users/{target['id']}/admin",
        json={"is_admin": True},
        params={"superadmin_user_id": SUPERADMIN_USER_ID},
    )
    assert response.status_code == 200
    assert response.json()["is_admin"] is True
    # Confirm it actually persisted, not just echoed back.
    assert _login(target["name"]).json()["is_admin"] is True


def test_regular_admin_cannot_promote():
    """PRD.md Task 6.10: promoting is superadmin-only now — a *regular*
    admin (not just an ordinary member) is also turned away."""
    target = _register("StaysRegular" + os.urandom(3).hex()).json()
    response = client.patch(
        f"/api/admin/users/{target['id']}/admin",
        json={"is_admin": True},
        params={"superadmin_user_id": ADMIN_USER_ID},
    )
    assert response.status_code == 403


def test_non_admin_cannot_promote():
    target = _register("StaysRegular2" + os.urandom(3).hex()).json()
    response = client.patch(
        f"/api/admin/users/{target['id']}/admin",
        json={"is_admin": True},
        params={"superadmin_user_id": SAMPLE_USER_ID},
    )
    assert response.status_code == 403


def test_promote_unknown_user_404():
    response = client.patch(
        "/api/admin/users/999999/admin",
        json={"is_admin": True},
        params={"superadmin_user_id": SUPERADMIN_USER_ID},
    )
    assert response.status_code == 404


def test_registering_with_admin_like_name_does_not_grant_admin():
    """The old ADMIN_NAMES/SUPERADMIN_NAMES env-var mechanism matched a
    registering/logging-in account's *display name* against a list — but
    `name` was never unique (test_register_allows_duplicate_display_name),
    so anyone could register an account named "AdminUser" or
    "SuperAdminUser" and get auto-promoted. That mechanism is gone: admin
    is only ever granted by an existing superadmin (the promote endpoint
    below), and superadmin only ever exists as the one hardcoded master
    account."""
    body = _register("AdminUser" + os.urandom(3).hex()).json()
    assert body["is_admin"] is False
    assert body["is_superadmin"] is False

    body2 = _register("SuperAdminUser" + os.urandom(3).hex()).json()
    assert body2["is_admin"] is False
    assert body2["is_superadmin"] is False


def test_master_superadmin_can_log_in():
    response = client.post(
        "/api/auth/login",
        json={"username": MASTER_SUPERADMIN_USERNAME, "password": MASTER_SUPERADMIN_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_superadmin"] is True
    assert body["is_admin"] is True


def test_master_superadmin_username_is_reserved():
    """The master account is seeded at startup, so a fresh registration
    attempt under the same username collides like any other taken
    username — there's no separate carve-out that would let someone
    register their own "SMASTER" account."""
    response = client.post(
        "/api/auth/register",
        json={
            "username": MASTER_SUPERADMIN_USERNAME,
            "name": "Impersonator",
            "email": "impersonator@example.com",
            "password": "Ab2121!x",
        },
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Superadmin: remove user accounts (PRD.md Task 6.9)
# ---------------------------------------------------------------------------


def test_login_response_reports_superadmin_as_admin_too():
    body = client.post(
        "/api/auth/login",
        json={"username": MASTER_SUPERADMIN_USERNAME, "password": MASTER_SUPERADMIN_PASSWORD},
    ).json()
    assert body["is_superadmin"] is True
    assert body["is_admin"] is True  # superadmin implies admin, not a separate flag to also set


def test_superadmin_can_remove_a_user():
    target = _register("RemoveMe" + os.urandom(3).hex()).json()
    response = client.delete(
        f"/api/superadmin/users/{target['id']}", params={"superadmin_user_id": SUPERADMIN_USER_ID}
    )
    assert response.status_code == 204
    assert _login(target["name"]).status_code == 401  # account is actually gone


def test_admin_cannot_remove_a_user():
    """Regular admin (Task 6.2) is a lower tier than superadmin (Task 6.9)
    — job moderation only, not account removal."""
    target = _register("StaysRemoved" + os.urandom(3).hex()).json()
    response = client.delete(
        f"/api/superadmin/users/{target['id']}", params={"superadmin_user_id": ADMIN_USER_ID}
    )
    assert response.status_code == 403
    assert _login(target["name"]).status_code == 200  # still there


def test_superadmin_cannot_remove_own_account():
    response = client.delete(
        f"/api/superadmin/users/{SUPERADMIN_USER_ID}",
        params={"superadmin_user_id": SUPERADMIN_USER_ID},
    )
    assert response.status_code == 400


def test_removing_a_user_orphans_their_jobs_instead_of_deleting_them():
    target = _register("JobSharer" + os.urandom(3).hex()).json()
    job = client.post("/api/jobs", json={**SAMPLE_JOB, "user_id": target["id"]}).json()

    client.delete(
        f"/api/superadmin/users/{target['id']}", params={"superadmin_user_id": SUPERADMIN_USER_ID}
    )

    still_there = client.get(f"/api/jobs/{job['id']}")
    assert still_there.status_code == 200
    assert still_there.json()["shared_by_user_id"] is None
