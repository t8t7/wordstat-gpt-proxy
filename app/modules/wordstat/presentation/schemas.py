from pydantic import BaseModel, ConfigDict


class PhraseStatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phrase: str
    count: int


class WordstatTopResponse(BaseModel):
    query: str
    totalCount: int
    results: list[PhraseStatResponse]
    associations: list[PhraseStatResponse]

