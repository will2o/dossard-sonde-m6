import pytest


@pytest.fixture
def ranked_event(client, make_competition, make_event, make_athlete, make_registration):
    """Fabrique : une épreuve close, un athlète confirmé et un résultat par performance."""

    def _make(unit: str, performances: list[float]) -> dict:
        competition = make_competition(status="open")
        event = make_event(competition["id"], unit=unit)
        registrations = [
            make_registration(event["id"], make_athlete(f"Athlete{i}")["id"])
            for i in range(len(performances))
        ]
        client.patch(f"/competitions/{competition['id']}", json={"status": "closed"})
        for registration, performance in zip(registrations, performances, strict=True):
            response = client.put(
                f"/registrations/{registration['id']}/result", json={"performance": performance}
            )
            assert response.status_code == 200
        return event

    return _make


def test_ranking_orders_times_ascending(client, ranked_event):
    event = ranked_event("time_s", [12.4, 11.9, 12.1])

    response = client.get(f"/events/{event['id']}/ranking")

    assert response.status_code == 200
    ranking = response.json()
    assert [(e["rank"], e["performance"]) for e in ranking] == [(1, 11.9), (2, 12.1), (3, 12.4)]


def test_ranking_orders_distances_descending(client, ranked_event):
    event = ranked_event("distance_m", [6.2, 6.85, 5.9])

    response = client.get(f"/events/{event['id']}/ranking")

    assert response.status_code == 200
    ranking = response.json()
    assert [(e["rank"], e["performance"]) for e in ranking] == [(1, 6.85), (2, 6.2), (3, 5.9)]


def test_ranking_returns_empty_list_without_results(client, make_competition, make_event):
    event = make_event(make_competition()["id"])

    response = client.get(f"/events/{event['id']}/ranking")

    assert response.status_code == 200
    assert response.json() == []


def test_ranking_unknown_event_returns_404(client):
    response = client.get("/events/999/ranking")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Épreuve 999 introuvable"}}


def test_ranking_invalid_event_id_returns_422(client):
    response = client.get("/events/abc/ranking")

    assert response.status_code == 422


def test_export_csv_unknown_competition_returns_404(client):
    response = client.get("/competitions/999/results.csv")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Compétition 999 introuvable"}
    }
