"""Hook PreToolUse : bloque rm -rf, git push --force et DROP TABLE / DROP VIEW.

Lit le JSON de Claude Code sur stdin. Exit 2 + message sur stderr : l'appel est bloqué
et le message est renvoyé à Claude. Exit 0 : l'appel continue.
"""

from __future__ import annotations

import json
import re
import shlex
import sys

OUTILS_SHELL = {"Bash", "PowerShell"}
DROP = re.compile(r"\bdrop\s+(table|view)\b", re.IGNORECASE)
SEPARATEURS = re.compile(r"&&|\|\||[;&|()\n]")


def options(mots: list[str]) -> tuple[set[str], set[str]]:
    """Lettres des options courtes et options longues, jusqu'à `--`."""
    courtes: set[str] = set()
    longues: set[str] = set()
    for mot in mots:
        if mot == "--":
            break
        if mot.startswith("--"):
            longues.add(mot.split("=")[0])
        elif mot.startswith("-"):
            courtes.update(mot[1:])
    return courtes, longues


def raison(commande: str) -> str | None:
    if DROP.search(commande):
        return "DROP TABLE / DROP VIEW interdit"
    for morceau in SEPARATEURS.split(commande):
        try:
            mots = shlex.split(morceau)
        except ValueError:
            mots = morceau.split()
        for i, mot in enumerate(mots):
            nom = re.split(r"[\\/]", mot)[-1]
            courtes, longues = options(mots[i + 1 :])
            recursif = bool(courtes & {"r", "R"}) or "--recursive" in longues
            force = "f" in courtes or bool(longues & {"--force", "--force-with-lease"})
            if nom == "rm" and recursif and force:
                return "rm -rf interdit"
            if nom == "git" and "push" in mots[i + 1 :] and force:
                return "git push --force interdit"
            if " " in mot:  # commande entre guillemets : bash -c "rm -rf …"
                imbrique = raison(mot)
                if imbrique:
                    return imbrique
    return None


def main() -> None:
    entree = json.load(sys.stdin)
    if entree.get("tool_name") not in OUTILS_SHELL:
        sys.exit(0)
    motif = raison(str(entree.get("tool_input", {}).get("command", "")))
    if motif:
        print(f"Bloqué par le hook garde.py : {motif}.", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
