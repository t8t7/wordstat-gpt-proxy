from app.modules.wordstat.application.ports import WordstatGateway
from app.modules.wordstat.domain.entities import WordstatTop


class GetWordstatTop:
    def __init__(self, gateway: WordstatGateway) -> None:
        self._gateway = gateway

    async def execute(self, phrase: str) -> WordstatTop:
        return await self._gateway.get_top(phrase.strip())

