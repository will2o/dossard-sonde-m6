# Dossard

API FastAPI de gestion de compétitions sportives, base SQLite (`data/dossard.db`, une base temporaire par test).

## Commandes

- Tests : `pytest` — doivent être verts avant tout commit
- Lint + format, obligatoires après toute modification Python : `ruff check . && ruff format .`
- Données d'exemple : `python scripts/seed.py --reset`
- Serveur : `uvicorn app.main:app --reload`

## Règles

- Toute erreur métier passe par une exception de `app/errors.py` (`NotFoundError`, `ConflictError`…).
  Ne jamais lever `HTTPException` directement : le handler global produit le format
  `{"error": {"code": "...", "message": "..."}}`.
- Routes dans `app/routers/`, accès aux données dans `app/repositories/`, schémas dans `app/schemas.py`.
- Toute route ajoutée ou modifiée est reportée dans `docs/api.md` (tableau des routes)
  et en tête de `CHANGELOG.md`, section « Non publié » (créer le fichier s'il n'existe pas).
- Ne pas ajouter de dépendance dans `pyproject.toml` sans demander.
- `scripts/legacy/` est du code historique : lecture autorisée, aucune modification ni suppression sans demande explicite.
- Ne jamais lire ni afficher `.env` : il contient des secrets.

## Tests

- Un fichier de test par router (`tests/test_athletes.py`, `tests/test_competitions.py`…).
- Réutiliser les fixtures de `tests/conftest.py` : `client`, `make_competition`, `make_event`,
  `make_athlete`, `make_registration`. Aucun test ne lit `data/dossard.db`.
- Un test par comportement, nommé `test_<action>_<résultat attendu>`.
- Toujours tester les cas d'erreur (404, 409, 422) ; pour les erreurs métier (404, 409),
  vérifier le format d'erreur du projet (les 422 gardent le format FastAPI).

## Style

- `from __future__ import annotations` en tête de chaque module, annotations de types partout.
- Messages d'erreur et commits en français ; code et identifiants en anglais.
