from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request

from app.core.errors import AppError
from app.core.rate_limit import enforce_rate_limit
from app.core.security import require_proxy_authorization
from app.modules.wordstat.application.use_cases import GetWordstatTop
from app.modules.wordstat.presentation.schemas import PhraseStatResponse, WordstatTopResponse


router = APIRouter(tags=["wordstat"])


def get_wordstat_use_case(request: Request) -> GetWordstatTop:
    return cast(GetWordstatTop, request.app.state.get_wordstat_top)


@router.get(
    "/top",
    operation_id="getWordstatTop",
    summary="Get top Yandex Wordstat queries",
    description="Returns popular and associated Yandex queries for the last 30 days.",
    response_model=WordstatTopResponse,
    dependencies=[
        Depends(enforce_rate_limit),
        Depends(require_proxy_authorization),
    ],
)
async def get_top(
    q: Annotated[str, Query(min_length=1, max_length=400)],
    use_case: GetWordstatTop = Depends(get_wordstat_use_case),
) -> WordstatTopResponse:
    if not q.strip():
        raise AppError(422, "validation_error", "Invalid request parameters")
    result = await use_case.execute(q)
    return WordstatTopResponse(
        query=result.query,
        totalCount=result.total_count,
        results=[PhraseStatResponse.model_validate(item) for item in result.results],
        associations=[
            PhraseStatResponse.model_validate(item) for item in result.associations
        ],
    )
