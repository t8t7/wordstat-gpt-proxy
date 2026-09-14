import os
from fastapi.testclient import TestClient

os.environ.setdefault("YANDEX_API_KEY", "test-yandex-key")
os.environ.setdefault("YANDEX_FOLDER_ID", "test-folder")
os.environ.setdefault("PROXY_API_KEY", "p" * 32)

from app.core.rate_limit import enforce_rate_limit
from app.main import create_app
from app.modules.wordstat.application.use_cases import GetWordstatTop
from app.modules.wordstat.domain.entities import PhraseStat, WordstatTop
from app.modules.wordstat.presentation.router import get_wordstat_use_case


class StubUseCase(GetWordstatTop):
    def __init__(self) -> None:
        pass

    async def execute(self, phrase: str) -> WordstatTop:
        return WordstatTop(
            phrase,
            42,
            (PhraseStat("купить базу клиентов москва", 42),),
            (PhraseStat("база лидов", 11),),
        )


async def skip_rate_limit() -> None:
    return None


def make_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[enforce_rate_limit] = skip_rate_limit
    app.dependency_overrides[get_wordstat_use_case] = lambda: StubUseCase()
    return TestClient(app)


def test_top_requires_bearer_token() -> None:
    with make_client() as client:
        response = client.get("/top", params={"q": "test"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_top_returns_clean_json() -> None:
    with make_client() as client:
        response = client.get(
            "/top",
            params={"q": "купить базу клиентов"},
            headers={"Authorization": f"Bearer {'p' * 32}"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "query": "купить базу клиентов",
        "totalCount": 42,
        "results": [{"phrase": "купить базу клиентов москва", "count": 42}],
        "associations": [{"phrase": "база лидов", "count": 11}],
    }


def test_top_rejects_empty_query() -> None:
    with make_client() as client:
        response = client.get(
            "/top",
            params={"q": ""},
            headers={"Authorization": f"Bearer {'p' * 32}"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_top_rejects_whitespace_only_query() -> None:
    with make_client() as client:
        response = client.get(
            "/top",
            params={"q": "   "},
            headers={"Authorization": f"Bearer {'p' * 32}"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_openapi_contract_is_ready_for_gpt_action() -> None:
    with make_client() as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    operation = schema["paths"]["/top"]["get"]
    assert operation["operationId"] == "getWordstatTop"
    assert operation["security"] == [{"HTTPBearer": []}]
    assert schema["servers"] == [{"url": "https://goodpapa12.com/api/wordstat"}]
