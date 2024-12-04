import random
from functools import lru_cache
from typing import Any

FRONT_OF_TRAIN = ["🚅", "🚄", "🚂", "🚈"]
TRAIN_PARTS = ["🚋", "🚃"]


@lru_cache
def ferrify(count: int, seed: Any | None = None) -> str:
    if count == 0:
        return ""

    ra = random.Random(x=seed)  # noqa: S311
    train = [ra.choice(FRONT_OF_TRAIN)] + ra.choices(TRAIN_PARTS, k=count - 1)
    return "".join(train)
