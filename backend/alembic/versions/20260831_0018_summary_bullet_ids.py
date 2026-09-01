"""Add backend-owned stable IDs to stored note-summary bullets.

Revision ID: 20260831_0018
Revises: 20260731_0017
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260831_0018"
down_revision: str | None = "20260731_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE note_summaries AS summaries
        SET summary_json = jsonb_set(
            summaries.summary_json::jsonb,
            '{bullets}',
            COALESCE(
                (
                    SELECT jsonb_agg(
                        CASE
                            WHEN bullet.value ? 'id' THEN bullet.value
                            ELSE jsonb_set(
                                bullet.value,
                                '{id}',
                                to_jsonb(gen_random_uuid()::text)
                            )
                        END
                        ORDER BY bullet.ordinality
                    )
                    FROM jsonb_array_elements(
                        summaries.summary_json::jsonb -> 'bullets'
                    ) WITH ORDINALITY AS bullet(value, ordinality)
                ),
                '[]'::jsonb
            )
        )::json
        WHERE summaries.status = 'completed'
          AND jsonb_typeof(summaries.summary_json::jsonb -> 'bullets') = 'array'
          AND EXISTS (
              SELECT 1
              FROM jsonb_array_elements(
                  summaries.summary_json::jsonb -> 'bullets'
              ) AS bullet(value)
              WHERE NOT (bullet.value ? 'id')
          )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE note_summaries AS summaries
        SET summary_json = jsonb_set(
            summaries.summary_json::jsonb,
            '{bullets}',
            COALESCE(
                (
                    SELECT jsonb_agg(
                        bullet.value - 'id'
                        ORDER BY bullet.ordinality
                    )
                    FROM jsonb_array_elements(
                        summaries.summary_json::jsonb -> 'bullets'
                    ) WITH ORDINALITY AS bullet(value, ordinality)
                ),
                '[]'::jsonb
            )
        )::json
        WHERE summaries.status = 'completed'
          AND jsonb_typeof(summaries.summary_json::jsonb -> 'bullets') = 'array'
        """
    )
