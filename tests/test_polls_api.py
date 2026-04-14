from __future__ import annotations

from time import sleep
from uuid import UUID

X_USER_ID_HEADER = "X-User-Id"


def auth_headers(user_id: str = "user-1") -> dict[str, str]:
    """строит заголовки авторизации"""

    return {X_USER_ID_HEADER: user_id}


def create_poll(client, close_after_seconds=None, **overrides):
    payload = {
        "question": "Какой язык выбрать?",
        "options": ["Python", "Go"],
    }
    if close_after_seconds is not None:
        payload["close_after_seconds"] = close_after_seconds
    payload.update(overrides)
    return client.post("/api/v1/polls", json=payload)


def test_create_poll_success(client):
    response = create_poll(client)

    assert response.status_code == 201
    data = response.json()
    assert UUID(data["id"])
    assert data["question"] == "Какой язык выбрать?"
    assert data["status"] == "open"
    assert [option["option_id"] for option in data["options"]] == [1, 2]


def test_create_poll_with_empty_question_returns_validation_error(
    client,
):
    response = create_poll(client, question="   ")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_poll_with_less_than_two_options_returns_validation_error(
    client,
):
    response = create_poll(client, options=["Python"])

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_poll_with_empty_option_returns_validation_error(
    client,
):
    response = create_poll(client, options=["Python", "   "])

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_list_polls_returns_summary(client):
    poll_response = create_poll(client)
    poll = poll_response.json()
    option_id = poll["options"][0]["option_id"]

    client.post(
        f"/api/v1/polls/{poll['id']}/votes",
        json={"option_id": option_id},
        headers=auth_headers(),
    )

    response = client.get("/api/v1/polls")
    data = response.json()

    assert response.status_code == 200
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == poll["id"]
    assert data["items"][0]["options_count"] == 2
    assert data["items"][0]["total_votes"] == 1
    assert data["items"][0]["status"] == "open"
    assert data["items"][0]["created_at"].endswith("+03:00")


def test_vote_requires_user_header(client):
    poll_response = create_poll(client)
    poll = poll_response.json()
    option_id = poll["options"][0]["option_id"]

    response = client.post(
        f"/api/v1/polls/{poll['id']}/votes",
        json={"option_id": option_id},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_vote_with_empty_user_header_returns_401(client):
    poll_response = create_poll(client)
    poll = poll_response.json()
    option_id = poll["options"][0]["option_id"]

    response = client.post(
        f"/api/v1/polls/{poll['id']}/votes",
        json={"option_id": option_id},
        headers=auth_headers("   "),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_vote_success_and_results(client):
    poll_response = create_poll(client)
    poll = poll_response.json()
    option_id = poll["options"][0]["option_id"]

    vote_response = client.post(
        f"/api/v1/polls/{poll['id']}/votes",
        json={"option_id": option_id},
        headers=auth_headers(),
    )

    assert vote_response.status_code == 201
    assert vote_response.json()["poll_id"] == poll["id"]
    assert vote_response.json()["option_id"] == option_id

    results_response = client.get(f"/api/v1/polls/{poll['id']}/results")
    results = results_response.json()

    assert results_response.status_code == 200
    assert results["total_votes"] == 1
    assert results["options"][0]["option_id"] == option_id
    assert results["options"][0]["votes_count"] == 1
    assert results["status"] == "open"


def test_duplicate_vote_returns_conflict(client):
    poll_response = create_poll(client)
    poll = poll_response.json()
    option_id = poll["options"][0]["option_id"]

    first_vote = client.post(
        f"/api/v1/polls/{poll['id']}/votes",
        json={"option_id": option_id},
        headers=auth_headers(),
    )
    second_vote = client.post(
        f"/api/v1/polls/{poll['id']}/votes",
        json={"option_id": option_id},
        headers=auth_headers(),
    )

    assert first_vote.status_code == 201
    assert second_vote.status_code == 409
    assert second_vote.json()["error"]["code"] == "duplicate_vote"


def test_vote_for_nonexistent_option_returns_not_found(client):
    poll_response = create_poll(client)
    poll = poll_response.json()

    response = client.post(
        f"/api/v1/polls/{poll['id']}/votes",
        json={"option_id": 99999},
        headers=auth_headers(),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "option_not_found"


def test_manual_close_blocks_new_votes(client):
    poll_response = create_poll(client)
    poll = poll_response.json()
    option_id = poll["options"][0]["option_id"]

    close_response = client.post(f"/api/v1/polls/{poll['id']}/close")
    vote_response = client.post(
        f"/api/v1/polls/{poll['id']}/votes",
        json={"option_id": option_id},
        headers=auth_headers(),
    )

    assert close_response.status_code == 200
    assert close_response.json()["status"] == "closed"
    assert close_response.json()["closed_at"].endswith("+03:00")
    assert vote_response.status_code == 409
    assert vote_response.json()["error"]["code"] == "poll_closed"


def test_auto_close_blocks_new_votes(client):
    poll_response = create_poll(client, close_after_seconds=1)
    poll = poll_response.json()
    option_id = poll["options"][0]["option_id"]

    sleep(1.2)

    vote_response = client.post(
        f"/api/v1/polls/{poll['id']}/votes",
        json={"option_id": option_id},
        headers=auth_headers(),
    )
    results_response = client.get(f"/api/v1/polls/{poll['id']}/results")

    assert vote_response.status_code == 409
    assert vote_response.json()["error"]["code"] == "poll_closed"
    assert results_response.status_code == 200
    assert results_response.json()["status"] == "closed"
    assert results_response.json()["closes_at"].endswith("+03:00")


def test_repeated_close_returns_conflict(client):
    poll_response = create_poll(client)
    poll = poll_response.json()

    first_close = client.post(f"/api/v1/polls/{poll['id']}/close")
    second_close = client.post(f"/api/v1/polls/{poll['id']}/close")

    assert first_close.status_code == 200
    assert second_close.status_code == 409
    assert second_close.json()["error"]["code"] == "poll_already_closed"
