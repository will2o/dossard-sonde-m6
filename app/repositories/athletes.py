from __future__ import annotations

import csv
import io
import sqlite3
from datetime import date, datetime

from pydantic import ValidationError

from app.categories import age_category
from app.errors import ApiError, ConflictError
from app.repositories.common import fetch_or_404
from app.schemas import AthleteCreate, AthleteImportResult, AthleteOut, ImportLineError

# Colonne de l'export CSV de la fédération -> champ de AthleteCreate.
CSV_COLUMNS = {
    "nom": "last_name",
    "prenom": "first_name",
    "date_naissance": "birth_date",
    "sexe": "sex",
    "club": "club",
    "licence": "license_number",
    "certificat_valide_jusqu": "medical_certificate_valid_until",
}
FIELD_TO_COLUMN = {field: column for column, field in CSV_COLUMNS.items()}
DATE_COLUMNS = ("date_naissance", "certificat_valide_jusqu")


def _to_athlete(row: sqlite3.Row) -> AthleteOut:
    birth_date = date.fromisoformat(row["birth_date"])
    certificate = row["medical_certificate_valid_until"]
    return AthleteOut(
        id=row["id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        birth_date=birth_date,
        sex=row["sex"],
        club=row["club"],
        license_number=row["license_number"],
        medical_certificate_valid_until=date.fromisoformat(certificate) if certificate else None,
        category=age_category(birth_date),
    )


def list_athletes(conn: sqlite3.Connection, club: str | None = None) -> list[AthleteOut]:
    sql = "SELECT * FROM athletes"
    params: tuple[str, ...] = ()
    if club is not None:
        sql += " WHERE club = ?"
        params = (club,)
    sql += " ORDER BY last_name, first_name, id"
    return [_to_athlete(row) for row in conn.execute(sql, params)]


def get_athlete(conn: sqlite3.Connection, athlete_id: int) -> AthleteOut:
    row = fetch_or_404(
        conn,
        "SELECT * FROM athletes WHERE id = ?",
        (athlete_id,),
        f"Athlète {athlete_id} introuvable",
    )
    return _to_athlete(row)


def create_athlete(conn: sqlite3.Connection, data: AthleteCreate) -> AthleteOut:
    existing = conn.execute(
        "SELECT id FROM athletes WHERE license_number = ?", (data.license_number,)
    ).fetchone()
    if existing is not None:
        raise ConflictError(f"Licence {data.license_number} déjà enregistrée")

    certificate = data.medical_certificate_valid_until
    cursor = conn.execute(
        "INSERT INTO athletes (first_name, last_name, birth_date, sex, club, license_number,"
        " medical_certificate_valid_until) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            data.first_name,
            data.last_name,
            data.birth_date.isoformat(),
            data.sex.value,
            data.club,
            data.license_number,
            certificate.isoformat() if certificate else None,
        ),
    )
    row = conn.execute("SELECT * FROM athletes WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _to_athlete(row)


def import_athletes(conn: sqlite3.Connection, content: str) -> AthleteImportResult:
    """Importe l'export CSV de la fédération (séparateur « ; », dates jj/mm/aaaa).

    Une licence déjà enregistrée compte dans `skipped` ; une ligne invalide est reportée dans
    `errors` avec son numéro (en-tête = ligne 1) sans interrompre l'import.
    """
    reader = csv.DictReader(io.StringIO(content), delimiter=";")
    missing = [column for column in CSV_COLUMNS if column not in (reader.fieldnames or [])]
    if missing:
        raise ApiError(
            f"Colonnes manquantes dans l'en-tête CSV : {', '.join(missing)}", "invalid_csv"
        )

    created = skipped = 0
    errors: list[ImportLineError] = []
    for row in reader:
        try:
            data = _parse_csv_row(row)
        except ValueError as exc:
            errors.append(ImportLineError(line=reader.line_num, message=str(exc)))
            continue
        try:
            create_athlete(conn, data)
        except ConflictError:
            skipped += 1
        else:
            created += 1
    return AthleteImportResult(created=created, skipped=skipped, errors=errors)


def _parse_csv_row(row: dict[str | None, str | None]) -> AthleteCreate:
    if None in row or any(row[column] is None for column in CSV_COLUMNS):
        raise ValueError(f"nombre de colonnes incorrect (attendu {len(CSV_COLUMNS)})")
    values = {column: (row[column] or "").strip() for column in CSV_COLUMNS}

    fields: dict[str, str | date | None] = {}
    for column, field in CSV_COLUMNS.items():
        value = values[column]
        fields[field] = _parse_fr_date(column, value) if column in DATE_COLUMNS else value or None
    try:
        return AthleteCreate.model_validate(fields)
    except ValidationError as exc:
        columns = dict.fromkeys(FIELD_TO_COLUMN[str(error["loc"][0])] for error in exc.errors())
        messages = [
            f"{column} invalide : {values[column]!r}" if values[column] else f"{column} manquant"
            for column in columns
        ]
        raise ValueError(" ; ".join(messages)) from exc


def _parse_fr_date(column: str, value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError(f"{column} invalide : {value!r} (format attendu jj/mm/aaaa)") from None
