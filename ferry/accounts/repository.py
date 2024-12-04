import random
from functools import lru_cache
from typing import Any, Literal, TypedDict


class EmojiDefinition(TypedDict):
    emoji: str
    discord: str


FRONT_OF_TRAIN = [
    EmojiDefinition(emoji="🚅", discord=":bullettrain_front:"),
    EmojiDefinition(emoji="🚄", discord=":bullettrain_side:"),
    EmojiDefinition(emoji="🚂", discord=":steam_locomotive:"),
    EmojiDefinition(emoji="🚈", discord=":light_rail:"),
]
TRAIN_PARTS = [
    EmojiDefinition(emoji="🚋", discord=":train:"),
    EmojiDefinition(emoji="🚃", discord=":railway_car:"),
]


@lru_cache
def ferrify(count: int, seed: Any | None = None, *, fmt: Literal["emoji", "discord"] = "emoji") -> str:
    if count == 0:
        return ""

    ra = random.Random(x=seed)  # noqa: S311
    train = [ra.choice(FRONT_OF_TRAIN)] + ra.choices(TRAIN_PARTS, k=count - 1)
    return "".join(part[fmt] for part in train)
