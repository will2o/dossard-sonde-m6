from datetime import date
from pathlib import Path

SAMPLE_CSV = Path(__file__).parents[1] / "scripts" / "legacy" / "licencies_exemple.csv"


def test_create_athlete_returns_201_with_category(client):
    birth_date = date(date.today().year - 30, 3, 2)

    response = client.post(
        "/athletes",
        json={
            "first_name": "Inès",
            "last_name": "Morel",
            "birth_date": birth_date.isoformat(),
            "sex": "F",
            "license_number": "DOS-000042",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["category"] == "SENIOR"
    assert body["club"] is None


def test_create_athlete_rejects_duplicate_license(client, make_athlete):
    athlete = make_athlete()

    response = client.post(
        "/athletes",
        json={
            "first_name": "Hugo",
            "last_name": "Lemaire",
            "birth_date": "1995-05-20",
            "sex": "M",
            "license_number": athlete["license_number"],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_list_athletes_filters_by_club(client, make_athlete):
    make_athlete("Durand", club="AC Rivebelle")
    make_athlete("Petit", club="Stade Nordval")

    response = client.get("/athletes", params={"club": "AC Rivebelle"})

    assert response.status_code == 200
    assert [a["last_name"] for a in response.json()] == ["Durand"]


def test_get_athlete_returns_athlete(client, make_athlete):
    athlete = make_athlete("Durand", club="AC Rivebelle")

    response = client.get(f"/athletes/{athlete['id']}")

    assert response.status_code == 200
    assert response.json() == athlete


def test_get_unknown_athlete_returns_404(client):
    response = client.get("/athletes/999")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Athlète 999 introuvable"},
    }


def test_get_athlete_with_invalid_id_returns_422(client):
    response = client.get("/athletes/abc")

    assert response.status_code == 422


def _post_csv(client, content: bytes):
    return client.post("/athletes/import", content=content, headers={"Content-Type": "text/csv"})


def test_import_athletes_creates_skips_and_reports_errors(client):
    response = _post_csv(client, SAMPLE_CSV.read_bytes())

    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 17
    assert body["skipped"] == 1
    assert [error["line"] for error in body["errors"]] == [15, 16]
    assert "date_naissance" in body["errors"][0]["message"]
    assert "licence" in body["errors"][1]["message"]
    assert len(client.get("/athletes").json()) == 17


def test_reimport_athletes_skips_existing_licenses(client):
    _post_csv(client, SAMPLE_CSV.read_bytes())

    response = _post_csv(client, SAMPLE_CSV.read_bytes())

    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 0
    assert body["skipped"] == 18
    assert [error["line"] for error in body["errors"]] == [15, 16]
    assert len(client.get("/athletes").json()) == 17


def test_import_athletes_with_missing_columns_returns_400(client):
    response = _post_csv(client, b"nom;prenom\nValette;Margaux\n")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_csv"
    assert "date_naissance" in response.json()["error"]["message"]


def test_import_athletes_with_non_utf8_body_returns_400(client):
    response = _post_csv(client, SAMPLE_CSV.read_text(encoding="utf-8").encode("latin-1"))

    assert response.status_code == 400
    assert response.json() == {
        "error": {"code": "invalid_csv", "message": "Le fichier CSV doit être encodé en UTF-8"},
    }


def _names(response) -> list[str]:
    return [a["last_name"] for a in response.json()]


def test_list_athletes_defaults_to_limit_50(client, make_athlete):
    for i in range(52):
        make_athlete(f"Nom{i:02d}")

    response = client.get("/athletes")

    assert response.status_code == 200
    assert len(response.json()) == 50
    assert _names(response)[0] == "Nom00"


def test_list_athletes_applies_limit_and_offset(client, make_athlete):
    for name in ["Alpha", "Bravo", "Charlie", "Delta"]:
        make_athlete(name)

    response = client.get("/athletes", params={"limit": 2, "offset": 1})

    assert response.status_code == 200
    assert _names(response) == ["Bravo", "Charlie"]


def test_list_athletes_offset_beyond_total_returns_empty_list(client, make_athlete):
    make_athlete("Alpha")

    response = client.get("/athletes", params={"offset": 5})

    assert response.status_code == 200
    assert response.json() == []


def test_list_athletes_accepts_limit_bounds(client, make_athlete):
    make_athlete("Alpha")
    make_athlete("Bravo")

    assert len(client.get("/athletes", params={"limit": 1}).json()) == 1
    assert len(client.get("/athletes", params={"limit": 100}).json()) == 2


def test_list_athletes_paginates_after_club_filter(client, make_athlete):
    make_athlete("Alpha", club="AC Rivebelle")
    make_athlete("Bravo", club="Stade Nordval")
    make_athlete("Charlie", club="AC Rivebelle")
    make_athlete("Delta", club="AC Rivebelle")

    response = client.get("/athletes", params={"club": "AC Rivebelle", "limit": 2, "offset": 1})

    assert response.status_code == 200
    assert _names(response) == ["Charlie", "Delta"]


def test_list_athletes_rejects_out_of_range_pagination(client):
    for params in [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "abc"}]:
        response = client.get("/athletes", params=params)

        assert response.status_code == 422, params
