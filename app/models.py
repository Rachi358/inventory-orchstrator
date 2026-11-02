
from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(
        String(50), primary_key=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    warehouse_location: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    base_price_usd: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )


class ReconciliationAuditLog(Base):
    __tablename__ = "reconciliation_audit_logs"

    __table_args__ = (
        CheckConstraint(
            "status IN ('SUCCESS', 'RETRY_FALLBACK', 'FAILED')",
            name="check_reconciliation_status",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    skus_processed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
