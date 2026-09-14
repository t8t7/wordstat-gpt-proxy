from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PhraseStat:
    phrase: str
    count: int


@dataclass(frozen=True, slots=True)
class WordstatTop:
    query: str
    total_count: int
    results: tuple[PhraseStat, ...]
    associations: tuple[PhraseStat, ...]

