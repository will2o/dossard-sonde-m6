# Changelog

## Non publié

- Ajout de la pagination `?limit=` (1-100, défaut 50) et `?offset=` (≥ 0, défaut 0) à `GET /athletes`,
  appliquée après le filtre `club` ; hors bornes : 422.
- Ajout de `POST /athletes/import` : import de l'export CSV de la fédération (`created`, `skipped`,
  `errors` par ligne ; 400 `invalid_csv` si le fichier est illisible).
- Suppression de `scripts/legacy/import_licencies.py`, remplacé par `POST /athletes/import`.
- Ajout de `GET /athletes/{athlete_id}` : détail d'un athlète (404 `not_found` si inconnu).
