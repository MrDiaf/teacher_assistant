import json

from app.core.config import Settings
from app.platform.ai import WORKSPACE_RETENTION_POLICY, AiModelRegistry
from app.platform.diagnostics import parse_diagnostic_explanation, redact


def test_platform_ai_entry_preserves_model_selection_and_workspace_policy() -> None:
    registry = AiModelRegistry(
        Settings(
            codex_model="gpt-5.6-terra",
            ai_allowed_models="gpt-5.6-sol,gpt-5.6-terra",
        )
    )

    assert registry.resolve(None) == "gpt-5.6-terra"
    assert [model.id for model in registry.response().models] == [
        "gpt-5.6-sol",
        "gpt-5.6-terra",
    ]
    assert WORKSPACE_RETENTION_POLICY == "delete_immediately_after_job"


def test_platform_diagnostic_entry_retains_bounded_safe_values() -> None:
    assert redact({"password": "private", "message": "safe"}) == {
        "password": "[REDACTED]",
        "message": "safe",
    }

    explanation = parse_diagnostic_explanation(
        json.dumps(
            {
                "plain_explanation": "The input could not be processed.",
                "likely_cause": "The date was invalid.",
                "input_fixes": ["Use a real calendar date."],
                "application_improvements": [],
                "retry_is_safe": True,
            }
        )
    )
    assert explanation.retry_is_safe is True
