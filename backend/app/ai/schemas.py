from pydantic import BaseModel


class AiModelOption(BaseModel):
    id: str
    label: str


class AiModelListResponse(BaseModel):
    default_model: str
    models: list[AiModelOption]
