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


SPARKLINE_WIDTH = 240
SPARKLINE_HEIGHT = 64
SPARKLINE_PADDING = 4
SPARKLINE_COLORS = ("primary", "success", "warning")  # Bootstrap theme colours, so both themes work.


def get_score_sparkline_data(display_names: list[str]) -> dict[str, Any] | None:
    """Per-academic-year totals for the given people, laid out as SVG coordinates.

    Returns None when there are fewer than two academic years, as there is no trend to draw.
    """
    chart_data = get_annual_score_chart_data()
    labels = chart_data["labels"]
    if len(labels) < 2:
        return None

    datasets_by_name = {dataset["label"]: dataset["data"] for dataset in chart_data["datasets"]}
    selected = [(name, datasets_by_name[name]) for name in display_names if name in datasets_by_name]
    if not selected:
        return None

    # One shared scale, so lines can be compared with each other.
    max_value = max(max(data) for _, data in selected) or 1
    plot_width = SPARKLINE_WIDTH - 2 * SPARKLINE_PADDING
    plot_height = SPARKLINE_HEIGHT - 2 * SPARKLINE_PADDING

    def point(index: int, value: int) -> tuple[float, float]:
        x = SPARKLINE_PADDING + plot_width * index / (len(labels) - 1)
        y = SPARKLINE_PADDING + plot_height * (1 - value / max_value)
        return round(x, 1), round(y, 1)

    series = []
    for index, (name, data) in enumerate(selected):
        points = [point(position, value) for position, value in enumerate(data)]
        series.append(
            {
                "label": name,
                "color": SPARKLINE_COLORS[index % len(SPARKLINE_COLORS)],
                "points": " ".join(f"{x},{y}" for x, y in points),
                "end_x": points[-1][0],
                "end_y": points[-1][1],
                "latest": data[-1],
            }
        )

    return {
        "width": SPARKLINE_WIDTH,
        "height": SPARKLINE_HEIGHT,
        "first_label": labels[0],
        "last_label": labels[-1],
        "series": series,
    }
