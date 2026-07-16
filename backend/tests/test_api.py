import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["DEVCAREER_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.setdefault("ADMIN_NAMES", "AdminUser")
os.environ.setdefault("SUPERADMIN_NAMES", "SuperAdminUser")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _username_for(name: str) -> str:
    """PRD.md Task 6.7: register/login now take a separate `username` from
    the display `name`. Existing tests only ever dealt with one string per
    account, so every call site here still just passes a `name` — this
    derives a matching username the same simple way for both _register and
    _login, so passing the same `name` to each still refers to the same
    account without touching the 35+ existing call sites."""
    return re.sub(r"[^A-Za-z0-9._-]", "", name).lower()


def _register(name: str, password: str = "hunter22", referral_code: str = ""):
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


def _login(name: str, password: str = "hunter22"):
    return client.post(
        "/api/auth/login", json={"username": _username_for(name), "password": password}
    )


def _delete_job(job_id, admin_user_id):
    return client.delete(f"/api/jobs/{job_id}", params={"admin_user_id": admin_user_id})


SAMPLE_USER_ID = _register("Soumyadeep").json()["id"]
ADMIN_USER_ID = _register("AdminUser").json()["id"]
SUPERADMIN_USER_ID = _register("SuperAdminUser").json()["id"]

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


def test_register_rejects_duplicate_username_different_display_name():
    """PRD.md Task 6.7: username is the unique login handle, independent of
    the (also-unique, for now — see database.create_user's docstring)
    display name. Two accounts sharing the same derived username but with
    different `name` values must still collide on username."""
    response1 = client.post(
        "/api/auth/register",
        json={
            "username": "sharedhandle",
            "name": "First Person",
            "email": "first@example.com",
            "password": "hunter22",
        },
    )
    assert response1.status_code == 201
    response2 = client.post(
        "/api/auth/register",
        json={
            "username": "SharedHandle",  # case-insensitive collision
            "name": "Second Person",
            "email": "second@example.com",
            "password": "hunter22",
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
            "password": "hunter22",
        },
    )
    response = client.post(
        "/api/auth/register",
        json={
            "username": "emailtaker",
            "name": "Email Taker",
            "email": "shared@example.com",
            "password": "hunter22",
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
            "password": "hunter22",
        },
    )
    assert client.post(
        "/api/auth/login",
        json={"username": "A Totally Different Display Name", "password": "hunter22"},
    ).status_code == 401
    assert client.post(
        "/api/auth/login", json={"username": "distincthandle", "password": "hunter22"}
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


def test_admin_can_promote_another_user():
    target = _register("PromoteMe" + os.urandom(3).hex()).json()
    response = client.patch(
        f"/api/admin/users/{target['id']}/admin",
        json={"is_admin": True},
        params={"admin_user_id": ADMIN_USER_ID},
    )
    assert response.status_code == 200
    assert response.json()["is_admin"] is True
    # Confirm it actually persisted, not just echoed back.
    assert _login(target["name"]).json()["is_admin"] is True


def test_non_admin_cannot_promote():
    target = _register("StaysRegular" + os.urandom(3).hex()).json()
    response = client.patch(
        f"/api/admin/users/{target['id']}/admin",
        json={"is_admin": True},
        params={"admin_user_id": SAMPLE_USER_ID},
    )
    assert response.status_code == 403


def test_promote_unknown_user_404():
    response = client.patch(
        "/api/admin/users/999999/admin",
        json={"is_admin": True},
        params={"admin_user_id": ADMIN_USER_ID},
    )
    assert response.status_code == 404


def test_admin_names_env_promotes_existing_account_at_login(monkeypatch):
    plain_name = "FutureAdmin" + os.urandom(3).hex()
    _register(plain_name)
    assert _login(plain_name).json()["is_admin"] is False

    monkeypatch.setenv("ADMIN_NAMES", f"AdminUser,{plain_name}")
    assert _login(plain_name).json()["is_admin"] is True


# ---------------------------------------------------------------------------
# Superadmin: remove user accounts (PRD.md Task 6.9)
# ---------------------------------------------------------------------------


def test_login_response_reports_superadmin_as_admin_too():
    body = _login("SuperAdminUser").json()
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
