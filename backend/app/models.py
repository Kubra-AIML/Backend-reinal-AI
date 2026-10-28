import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class AppendOnlyError(Exception):
    """Raised when code tries to change or delete a record that must never change."""


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("classifier", "quality_gate", "preprocess_spec", "engine", name="uq_model_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    classifier: Mapped[str] = mapped_column(String(100))
    quality_gate: Mapped[str] = mapped_column(String(100))
    preprocess_spec: Mapped[str] = mapped_column(String(100))
    engine: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_ref: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    image_sha256: Mapped[str] = mapped_column(String(64), index=True)
    content_type: Mapped[str] = mapped_column(String(50))
    size_bytes: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), unique=True, index=True, nullable=True)
    engine: Mapped[str] = mapped_column(String(16))
    model_version_id: Mapped[str] = mapped_column(ForeignKey("model_versions.id"))
    # The ORIGINAL analysis result (the AnalysisResult JSON). Never overwritten.
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reviews: Mapped[list["Review"]] = relationship(back_populates="case", order_by="Review.created_at")


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("corrected_grade IS NULL OR (corrected_grade >= 0 AND corrected_grade <= 4)", name="ck_reviews_grade"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    reviewer: Mapped[str] = mapped_column(String(100))
    decision: Mapped[str] = mapped_column(String(32))
    corrected_grade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["Case"] = relationship(back_populates="reviews")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    case_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    actor: Mapped[str] = mapped_column(String(100), default="system")
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---- Application-level append-only protection (the database triggers are the second layer) ----

def _block_change(mapper, connection, target):
    raise AppendOnlyError(f"{type(target).__name__} records are append-only and cannot be changed or deleted")


for _model in (AuditEvent, Review):
    event.listen(_model, "before_update", _block_change)
    event.listen(_model, "before_delete", _block_change)


@event.listens_for(Case, "before_update")
def _protect_original_result(mapper, connection, target):
    if inspect(target).attrs.result_json.history.has_changes():
        raise AppendOnlyError("The original prediction cannot be overwritten; add a review record instead")