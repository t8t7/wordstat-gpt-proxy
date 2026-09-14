import pytest

from app.modules.wordstat.application.use_cases import GetWordstatTop
from app.modules.wordstat.domain.entities import PhraseStat, WordstatTop


class StubGateway:
    def __init__(self) -> None:
        self.received_phrase: str | None = None

    async def get_top(self, phrase: str) -> WordstatTop:
        self.received_phrase = phrase
        return WordstatTop(phrase, 10, (PhraseStat(phrase, 10),), ())


@pytest.mark.asyncio
async def test_use_case_trims_phrase() -> None:
    gateway = StubGateway()
    result = await GetWordstatTop(gateway).execute("  купить базу клиентов  ")

    assert gateway.received_phrase == "купить базу клиентов"
    assert result.total_count == 10

