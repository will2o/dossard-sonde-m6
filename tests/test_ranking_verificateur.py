from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def ranked_event(
    client: TestClient,
    make_competition: Callable[..., dict],
    make_event: Callable[..., dict],
    make_athlete: Callable[..., dict],
    make_registration: Callable[..., dict],
) -> Callable[[str, list[float]], dict]:
    """Fabrique : une épreuve close avec un athlète confirmé et un résultat par performance."""

    def _make(unit: str, performances: list[float]) -> dict:
        competition = make_competition(status="open")
        event = make_event(competition["id"], unit=unit)
        registrations = [
            make_registration(event["id"], make_athlete(f"Athlete{i}")["id"])
            for i in range(len(performances))
        ]
        response = client.patch(f"/competitions/{competition['id']}", json={"status": "closed"})
        assert response.status_code == 200
        for registration, performance in zip(registrations, performances, strict=True):
            response = client.put(
                f"/registrations/{registration['id']}/result", json={"performance": performance}
            )
            assert response.status_code == 200
        return event

    return _make


def _ranks(client: TestClient, event: dict) -> list[int]:
    response = client.get(f"/events/{event['id']}/ranking")
    assert response.status_code == 200
    return [entry["rank"] for entry in response.json()]


def test_ranking_tie_for_first_place_skips_to_third(
    client: TestClient, ranked_event: Callable[[str, list[float]], dict]
) -> None:
    event = ranked_event("time_s", [11.9, 11.9, 12.5])

    assert _ranks(client, event) == [1, 1, 3]


def test_ranking_tie_for_last_place_shares_rank(
    client: TestClient, ranked_event: Callable[[str, list[float]], dict]
) -> None:
    event = ranked_event("time_s", [11.0, 12.0, 13.0, 13.0])

    assert _ranks(client, event) == [1, 2, 3, 3]


def test_ranking_triple_tie_skips_two_places(
    client: TestClient, ranked_event: Callable[[str, list[float]], dict]
) -> None:
    event = ranked_event("time_s", [11.0, 12.0, 12.0, 12.0, 13.0])

    assert _ranks(client, event) == [1, 2, 2, 2, 5]


def test_ranking_all_equal_performances_all_rank_first(
    client: TestClient, ranked_event: Callable[[str, list[float]], dict]
) -> None:
    event = ranked_event("time_s", [12.0, 12.0, 12.0])

    assert _ranks(client, event) == [1, 1, 1]


def test_ranking_two_separate_ties_each_skip_places(
    client: TestClient, ranked_event: Callable[[str, list[float]], dict]
) -> None:
    event = ranked_event("time_s", [11.0, 11.0, 12.0, 12.0, 13.0])

    assert _ranks(client, event) == [1, 1, 3, 3, 5]


def test_ranking_single_result_has_rank_one(
    client: TestClient, ranked_event: Callable[[str, list[float]], dict]
) -> None:
    event = ranked_event("time_s", [12.0])

    assert _ranks(client, event) == [1]


def test_ranking_tied_distances_share_rank_and_skip_next(
    client: TestClient, ranked_event: Callable[[str, list[float]], dict]
) -> None:
    event = ranked_event("distance_m", [6.85, 6.2, 6.85, 5.9])

    response = client.get(f"/events/{event['id']}/ranking")

    assert response.status_code == 200
    ranking = response.json()
    assert [(e["rank"], e["performance"]) for e in ranking] == [
        (1, 6.85),
        (1, 6.85),
        (3, 6.2),
        (4, 5.9),
    ]


def test_ranking_tied_points_share_rank_and_skip_next(
    client: TestClient, ranked_event: Callable[[str, list[float]], dict]
) -> None:
    event = ranked_event("points", [800, 950, 800, 700])

    assert _ranks(client, event) == [1, 2, 2, 4]


def test_ranking_nearly_equal_times_are_not_tied(
    client: TestClient, ranked_event: Callable[[str, list[float]], dict]
) -> None:
    event = ranked_event("time_s", [12.01, 12.0])

    assert _ranks(client, event) == [1, 2]


def test_ranking_unknown_event_returns_404_with_error_format(client: TestClient) -> None:
    response = client.get("/events/999/ranking")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Épreuve 999 introuvable"}}


def test_ranking_invalid_event_id_returns_422(client: TestClient) -> None:
    response = client.get("/events/abc/ranking")

    assert response.status_code == 422
    assert "detail" in response.json()
