"""Add forwarded-mail integration and private Inbox metadata.

Revision ID: 20260903_0020
Revises: 20260903_0019
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260903_0020"
down_revision: str | None = "20260903_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def upgrade() -> None:
    op.create_table(
        "mail_integration_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("host", sa.String(253), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("tls_mode", sa.String(24), nullable=False),
        sa.Column("mailbox", sa.String(255), nullable=False),
        sa.Column("username", sa.String(320), nullable=False),
        sa.Column("credential_ref", sa.String(36), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        *timestamps(),
        sa.CheckConstraint("tls_mode IN ('implicit_tls', 'starttls')", name="mail_tls_mode"),
        sa.CheckConstraint(
            "status IN ('connected', 'reconnect_required', 'error')", name="integration_status"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind"),
        sa.UniqueConstraint("credential_ref"),
    )
    op.create_table(
        "mail_sync_cursors",
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("uid_validity", sa.BigInteger(), nullable=True),
        sa.Column("last_uid", sa.BigInteger(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("safe_error_code", sa.String(80), nullable=True),
        sa.Column("safe_error", sa.Text(), nullable=True),
        sa.Column("source_warning", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["connection_id"], ["mail_integration_connections.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("connection_id"),
    )
    op.create_index("ix_mail_sync_cursors_next_check_at", "mail_sync_cursors", ["next_check_at"])
    op.create_table(
        "mail_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=True),
        sa.Column("mailbox_identity", sa.String(64), nullable=False),
        sa.Column("remote_uid_validity", sa.BigInteger(), nullable=False),
        sa.Column("remote_uid", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.String(998), nullable=True),
        sa.Column("in_reply_to", sa.String(998), nullable=True),
        sa.Column("thread_references", sa.JSON(), nullable=False),
        sa.Column("subject", sa.String(998), nullable=False),
        sa.Column("source_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("forwarded_unverified", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("remote_uid > 0", name="ck_mail_messages_uid_positive"),
        sa.ForeignKeyConstraint(
            ["connection_id"], ["mail_integration_connections.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mailbox_identity",
            "remote_uid_validity",
            "remote_uid",
            name="uq_mail_messages_remote_identity",
        ),
    )
    op.create_index("ix_mail_messages_connection_id", "mail_messages", ["connection_id"])
    op.create_index("ix_mail_messages_content_hash", "mail_messages", ["content_hash"])
    op.create_index("ix_mail_messages_is_archived", "mail_messages", ["is_archived"])
    op.create_index("ix_mail_messages_is_read", "mail_messages", ["is_read"])
    op.create_index("ix_mail_messages_source_date", "mail_messages", ["source_date"])
    op.create_table(
        "mail_addresses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("display_name", sa.String(320), nullable=True),
        sa.Column("address", sa.String(320), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("kind IN ('from', 'reply_to', 'to', 'cc')", name="mail_address_kind"),
        sa.ForeignKeyConstraint(["message_id"], ["mail_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mail_addresses_message_id", "mail_addresses", ["message_id"])
    op.create_table(
        "mail_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("storage_path", sa.String(96), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("omission_reason", sa.String(240), nullable=True),
        sa.ForeignKeyConstraint(["message_id"], ["mail_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index("ix_mail_attachments_message_id", "mail_attachments", ["message_id"])
    op.create_table(
        "mail_quarantines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("mailbox_identity", sa.String(64), nullable=False),
        sa.Column("remote_uid_validity", sa.BigInteger(), nullable=False),
        sa.Column("remote_uid", sa.BigInteger(), nullable=False),
        sa.Column("safe_error_code", sa.String(80), nullable=False),
        sa.Column("safe_error", sa.String(240), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["connection_id"], ["mail_integration_connections.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mailbox_identity",
            "remote_uid_validity",
            "remote_uid",
            name="uq_mail_quarantine_remote_identity",
        ),
    )
    op.create_table(
        "mail_cleanup_audits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("deleted_message_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("quarantine_token", sa.String(96), nullable=True),
        sa.Column("safe_error", sa.String(240), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mail_cleanup_audits_deleted_message_id", "mail_cleanup_audits", ["deleted_message_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_mail_cleanup_audits_deleted_message_id", table_name="mail_cleanup_audits")
    op.drop_table("mail_cleanup_audits")
    op.drop_table("mail_quarantines")
    op.drop_index("ix_mail_attachments_message_id", table_name="mail_attachments")
    op.drop_table("mail_attachments")
    op.drop_index("ix_mail_addresses_message_id", table_name="mail_addresses")
    op.drop_table("mail_addresses")
    for index in (
        "ix_mail_messages_source_date",
        "ix_mail_messages_is_read",
        "ix_mail_messages_is_archived",
        "ix_mail_messages_content_hash",
        "ix_mail_messages_connection_id",
    ):
        op.drop_index(index, table_name="mail_messages")
    op.drop_table("mail_messages")
    op.drop_index("ix_mail_sync_cursors_next_check_at", table_name="mail_sync_cursors")
    op.drop_table("mail_sync_cursors")
    op.drop_table("mail_integration_connections")
