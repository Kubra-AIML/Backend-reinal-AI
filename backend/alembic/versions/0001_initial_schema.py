"""initial schema: cases, model versions, reviews, audit events

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("classifier", sa.String(100), nullable=False),
        sa.Column("quality_gate", sa.String(100), nullable=False),
        sa.Column("preprocess_spec", sa.String(100), nullable=False),
        sa.Column("engine", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("classifier", "quality_gate", "preprocess_spec", "engine", name="uq_model_version"),
    )

    op.create_table(
        "cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_ref", sa.String(32), nullable=False),
        sa.Column("image_sha256", sa.String(64), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("engine", sa.String(16), nullable=False),
        sa.Column("model_version_id", sa.String(36), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cases_case_ref", "cases", ["case_ref"], unique=True)
    op.create_index("ix_cases_image_sha256", "cases", ["image_sha256"])
    op.create_index("ix_cases_idempotency_key", "cases", ["idempotency_key"], unique=True)

    op.create_table(
        "reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("reviewer", sa.String(100), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("corrected_grade", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "corrected_grade IS NULL OR (corrected_grade >= 0 AND corrected_grade <= 4)",
            name="ck_reviews_grade",
        ),
    )
    op.create_index("ix_reviews_case_id", "reviews", ["case_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=True),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_case_id", "audit_events", ["case_id"])

    # Database-level append-only protection (SQLite triggers).
    op.execute(
        "CREATE TRIGGER audit_events_no_update BEFORE UPDATE ON audit_events "
        "BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;"
    )
    op.execute(
        "CREATE TRIGGER audit_events_no_delete BEFORE DELETE ON audit_events "
        "BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;"
    )
    op.execute(
        "CREATE TRIGGER reviews_no_update BEFORE UPDATE ON reviews "
        "BEGIN SELECT RAISE(ABORT, 'reviews is append-only'); END;"
    )
    op.execute(
        "CREATE TRIGGER reviews_no_delete BEFORE DELETE ON reviews "
        "BEGIN SELECT RAISE(ABORT, 'reviews is append-only'); END;"
    )
    op.execute(
        "CREATE TRIGGER cases_result_immutable BEFORE UPDATE OF result_json ON cases "
        "BEGIN SELECT RAISE(ABORT, 'original prediction cannot be overwritten'); END;"
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("reviews")
    op.drop_table("cases")
    op.drop_table("model_versions")