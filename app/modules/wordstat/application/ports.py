from typing import Protocol

from app.modules.wordstat.domain.entities import WordstatTop


class WordstatGateway(Protocol):
    async def get_top(self, phrase: str) -> WordstatTop: ...

