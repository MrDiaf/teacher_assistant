from __future__ import annotations

from app.ai.schemas import AiModelListResponse, AiModelOption
from app.core.config import Settings, get_settings
from app.core.errors import InvalidAiModelError

MODEL_LABELS = {
    "gpt-5.6-sol": "GPT-5.6 Sol · flagship",
    "gpt-5.6-terra": "GPT-5.6 Terra · balanced",
    "gpt-5.6-luna": "GPT-5.6 Luna · efficient",
}


class AiModelRegistry:
    """Resolve model IDs only from the installation's server-side allowlist."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.allowed_models = self._parse_allowed_models(self.settings.ai_allowed_models)
        if self.settings.codex_model not in self.allowed_models:
            raise RuntimeError("CODEX_MODEL must also be present in AI_ALLOWED_MODELS.")

    @staticmethod
    def _parse_allowed_models(raw_models: str) -> tuple[str, ...]:
        models = tuple(
            dict.fromkeys(model.strip() for model in raw_models.split(",") if model.strip())
        )
        if not models:
            raise RuntimeError("AI_ALLOWED_MODELS must contain at least one model.")
        return models

    @property
    def default_model(self) -> str:
        return self.settings.codex_model

    def resolve(self, requested_model: str | None) -> str:
        model = (requested_model or self.default_model).strip()
        if model not in self.allowed_models:
            raise InvalidAiModelError(self.allowed_models)
        return model

    def response(self) -> AiModelListResponse:
        return AiModelListResponse(
            default_model=self.default_model,
            models=[
                AiModelOption(id=model, label=MODEL_LABELS.get(model, model))
                for model in self.allowed_models
            ],
        )
