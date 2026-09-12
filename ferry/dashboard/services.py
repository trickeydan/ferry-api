from collections import defaultdict
from typing import Any

from ferry.court.models import Ratification


def get_annual_score_chart_data() -> dict[str, list[Any]]:
    scores: defaultdict[tuple[int, str], int] = defaultdict(int)
    years: set[int] = set()

    ratifications = Ratification.objects.values(
        "accusation__created_at",
        "accusation__suspect__display_name",
    )
    for ratification in ratifications:
        created_at = ratification["accusation__created_at"]
        year = created_at.year if created_at.month >= 9 else created_at.year - 1
        display_name = ratification["accusation__suspect__display_name"]
        scores[(year, display_name)] += 1
        years.add(year)

    labels = sorted(years)
    people = sorted({display_name for _, display_name in scores})
    return {
        "labels": [f"{year}/{str(year + 1)[-2:]}" for year in labels],
        "datasets": [
            {
                "label": display_name,
                "data": [scores[(year, display_name)] for year in labels],
            }
            for display_name in people
        ],
    }
