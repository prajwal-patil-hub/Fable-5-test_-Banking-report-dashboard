"""SQLAlchemy models — the single physical store behind every output surface.

Design notes:
- KpiValue is the atomic fact of the warehouse. It always carries lineage
  (document, page, extraction method, confidence, source text) so every number
  on a dashboard, PDF, deck, or workbook is traceable to its origin.
- One row per (bank, fiscal_year, kpi_code): the warehouse stores the resolved
  truth, not competing candidates. Candidate resolution happens upstream in the
  document-intelligence pipeline.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Bank(Base):
    __tablename__ = "banks"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    documents: Mapped[list["Document"]] = relationship(back_populates="bank")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.id"))
    title: Mapped[str] = mapped_column(String(255))
    doc_type: Mapped[str] = mapped_column(String(50))  # annual_report, basel, esg, ...
    fiscal_year: Mapped[str] = mapped_column(String(10))
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pages: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="processed")  # processed | ocr_required | failed
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    bank: Mapped[Bank] = relationship(back_populates="documents")


class KpiValue(Base):
    __tablename__ = "kpi_values"
    __table_args__ = (UniqueConstraint("bank_id", "fiscal_year", "kpi_code", name="uq_kpi_fact"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.id"), index=True)
    fiscal_year: Mapped[str] = mapped_column(String(10), index=True)
    kpi_code: Mapped[str] = mapped_column(String(50), index=True)
    value: Mapped[float] = mapped_column(Float)

    # Lineage
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(20), default="manual")  # rule_based|table|llm|manual|derived
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    validation_status: Mapped[str] = mapped_column(String(15), default="unvalidated")

    document: Mapped[Document | None] = relationship()


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.id"), index=True)
    fiscal_year: Mapped[str] = mapped_column(String(10), index=True)
    rule_code: Mapped[str] = mapped_column(String(60))
    rule_name: Mapped[str] = mapped_column(String(160))
    severity: Mapped[str] = mapped_column(String(10))  # error | warning | info
    status: Mapped[str] = mapped_column(String(10))  # passed | failed
    message: Mapped[str] = mapped_column(Text)
    kpi_codes: Mapped[str] = mapped_column(String(255), default="")  # comma-separated


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[str] = mapped_column(Text, default="")
