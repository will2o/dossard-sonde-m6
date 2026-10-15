from __future__ import annotations

import sqlite3

from app.schemas import RankingEntry, ResultUnit


def rank_results(rows: list[sqlite3.Row], unit: ResultUnit) -> list[RankingEntry]:
    """Classe les performances : temps croissants, distances et points décroissants.

    Les ex aequo partagent le même rang et le rang suivant saute d'autant (1, 2, 2, 4).
    """
    best_first = sorted(rows, key=lambda row: row["performance"], reverse=unit != ResultUnit.TIME_S)
    entries: list[RankingEntry] = []
    rank = 0
    for index, row in enumerate(best_first):
        if index == 0 or row["performance"] != best_first[index - 1]["performance"]:
            rank = index + 1
        entries.append(
            RankingEntry(
                rank=rank,
                bib=row["bib"],
                athlete_id=row["athlete_id"],
                last_name=row["last_name"],
                first_name=row["first_name"],
                club=row["club"],
                performance=row["performance"],
            )
        )
    return entries
