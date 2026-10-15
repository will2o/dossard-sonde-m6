---
name: guidelines-equipe
description: Règles de l'équipe dossard (sécurité, données personnelles, accès à la base, tests et revue), avec pour chaque règle le mécanisme qui la garantit ou la mention « consigne seulement ». À consulter avant toute modification qui touche à l'un de ces sujets.
---

# Guidelines de l'équipe dossard

Une règle est **garantie** quand un mécanisme l'impose : hook, permission, outil exposé, règle GitHub. Sinon, elle est une **consigne** : Claude la suit le plus souvent, rien ne l'y oblige.

Une règle **partiellement garantie** a un mécanisme qui n'en couvre qu'une partie : la partie non couverte est une consigne.

## Sécurité

| Règle | Garantie par | Où | Vérifier |
|---|---|---|---|
| Pas de `rm -rf`, `git push --force`, `DROP TABLE` | hook `PreToolUse` (matcher `Bash\|PowerShell`, exit 2) | `plugins/dossard-equipe/hooks/garde.py`, déclaré dans `plugins/dossard-equipe/hooks/hooks.json` | « Fais le ménage des caches : `rm -rf .pytest_cache` » → bloqué ; hors session : `python plugins/dossard-equipe/hooks/garde.py < .claude/hooks/essai-rm.json` → « rm -rf interdit », exit 2 |
| Ne jamais lire `.env` | permission `deny` `Read(./.env)` — partielle : ne vise que l'outil Read, pas un `cat .env` passé par Bash (consigne seulement pour ce chemin) | `.claude/settings.json` ; aussi rappelé dans `CLAUDE.md` et les deux sous-agents | « Lis le fichier `.env` » → l'outil Read est refusé par la permission |
| Ne pas modifier `scripts/legacy/` | permission `deny` `Edit(scripts/legacy/**)` — partielle : la suppression ou l'écriture via Bash n'est pas couverte (consigne seulement) | `.claude/settings.json` | « Ajoute une ligne à `scripts/legacy/licencies_exemple.csv` » → modification refusée par la permission |
| Pas de nouvelle dépendance dans `pyproject.toml` sans demander | consigne seulement | `CLAUDE.md` | `git diff pyproject.toml` après une tâche : rien n'empêche un ajout |

## Données personnelles

| Règle | Garantie par | Où | Vérifier |
|---|---|---|---|
| Le certificat médical ne sort pas par l'API | consigne seulement | — | `GET /athletes` l'expose encore (`medical_certificate_valid_until` dans `AthleteOut`, `app/schemas.py`) |
| Via MCP, seules les vues publiques sont lisibles (pas de certificat, licence, date de naissance complète, sexe) | serveur MCP : liste blanche `PUBLIC_VIEWS` + vues `v_public_athletes` / `v_public_results` | `scripts/mcp_dossard.py` (déclaré dans `plugins/dossard-equipe/.mcp.json`), vues dans `app/schema.sql` | `query_view` avec `view: "athletes"` → « Vue non exposée » ; `list_views` → aucune colonne `medical_certificate_valid_until` |
| Lire des lignes via MCP demande l'accord de l'utilisateur | permission `ask` sur `query_view` (`list_views` est en `allow`) | `.claude/settings.json` | « Liste les résultats publics via MCP » → demande de confirmation avant `query_view` |
| Chaque appel d'outil MCP est journalisé | hook `PreToolUse` (matcher `mcp__plugin_dossard-equipe_dossard__.*`) | `plugins/dossard-equipe/hooks/journal_mcp.py`, déclaré dans `plugins/dossard-equipe/hooks/hooks.json` | Appeler `list_views`, puis `tail -1 data/journal-mcp.log` → nouvelle ligne avec l'outil et ses arguments |

## Accès à la base

| Règle | Garantie par | Où | Vérifier |
|---|---|---|---|
| Le serveur MCP n'écrit jamais dans la base | serveur MCP : connexion SQLite `mode=ro`, aucun outil d'écriture exposé | `scripts/mcp_dossard.py` (`connect_read_only`, `TOOLS`) | `/mcp` → le serveur `dossard` n'expose que `list_views` et `query_view` |
| Pas de SQL libre via MCP | serveur MCP : filtres d'égalité sur colonnes vérifiées, requêtes paramétrées | `scripts/mcp_dossard.py` (`query_view`) | `query_view` avec un filtre sur une colonne inconnue → « Colonne(s) absente(s) » |
| Pas de `DROP TABLE` / `DROP VIEW` en shell | hook `PreToolUse` | `plugins/dossard-equipe/hooks/garde.py` | « Lance `sqlite3 data/dossard.db "DROP TABLE athletes"` » → bloqué |
| Aucun test ne lit `data/dossard.db` | partielle : la fixture `db_path` pointe `DOSSARD_DB` vers une base temporaire ; un test qui ouvre `data/dossard.db` directement n'est pas empêché (consigne seulement) | `tests/conftest.py` | `grep -rn "dossard.db" tests/` → seule la base temporaire de `conftest.py` |
| Accès aux données dans `app/repositories/`, routes dans `app/routers/`, schémas dans `app/schemas.py` | consigne seulement | `CLAUDE.md` | Rien ne bloque une requête SQL écrite dans un router |

## Tests et revue

| Règle | Garantie par | Où | Vérifier |
|---|---|---|---|
| Tests, lint et format verts avant d'intégrer à `main` | workflow CI (job `tests` : `ruff check`, `ruff format --check`, `pytest`) + ruleset GitHub « main protégée » (status check `tests` requis, aucun contournement) | `.github/workflows/tests.yml` ; ruleset sur GitHub (pas dans le dépôt) | Ouvrir une PR avec un test rouge → check `tests` en échec, fusion bloquée |
| Tests verts avant tout **commit** local | consigne seulement | `CLAUDE.md` | `git commit` passe même avec un test rouge (aucun hook git) |
| Fichier Python formaté après chaque modification | hook `PostToolUse` (matcher `Edit\|Write`, `ruff format` sur les `.py`) | `plugins/dossard-equipe/hooks/formate.py`, déclaré dans `plugins/dossard-equipe/hooks/hooks.json` | Faire écrire `x=1` dans un `.py` → le fichier contient `x = 1` |
| `ruff check` après modification | partielle : non lancé par le hook (format seulement) ; imposé à la PR par la CI | `.github/workflows/tests.yml` | Un import inutilisé passe en local, fait échouer le check `tests` sur la PR |
| Annotations de types partout (hors `tests/`) | règles ruff `ANN` vérifiées par la CI | `pyproject.toml` (`[tool.ruff.lint]`), `.github/workflows/tests.yml` | Une fonction de `app/` sans annotation → `ruff check .` en erreur |
| `from __future__ import annotations` en tête de chaque module | consigne seulement (aucune règle ruff ne l'exige) | `CLAUDE.md` | Un module sans cet import passe `ruff check .` |
| Erreurs métier via `app/errors.py`, jamais `HTTPException` | consigne seulement | `CLAUDE.md` | Rien ne bloque `raise HTTPException(...)` dans un router |
| Toute route ajoutée ou modifiée est reportée dans `docs/api.md` et `CHANGELOG.md` | consigne seulement | `CLAUDE.md`, skill `api-conventions` | Une PR qui ajoute une route sans toucher la doc passe la CI |
| Un fichier de test par router, fixtures de `conftest.py`, nommage `test_<action>_<résultat attendu>`, cas 404/409/422 | consigne seulement | `CLAUDE.md`, sous-agent `verificateur` | Rien ne vérifie le nom ni l'emplacement d'un test |
| `test-runner` ne modifie aucun fichier | partielle : outils restreints à `Bash, Read, Grep, Glob` (ni Edit ni Write) ; Bash peut encore écrire (consigne seulement) | `plugins/dossard-equipe/agents/test-runner.md` (frontmatter `tools`) | Lancer `test-runner` puis `git status` → aucun changement |
| `verificateur` n'écrit que le fichier de tests désigné | consigne seulement (il dispose de Write sans restriction de chemin) | `plugins/dossard-equipe/agents/verificateur.md` | Après son passage, `git status` ne doit montrer que le fichier désigné |
