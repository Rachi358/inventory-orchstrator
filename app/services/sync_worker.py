
import asyncio
import logging

from sqlalchemy import select, update
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.database import AsyncSessionLocal
from app.models import Product, ReconciliationAuditLog
from app.services.utils import log_event


logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 0.5


class UnknownSKUError(Exception):
    """Raised when a manifest contains an SKU absent from the catalog."""


def is_sqlite_lock_error(exc: OperationalError) -> bool:
    """Check whether the SQLite error is caused by database locking."""
    error_message = str(exc).lower()

    return (
        "database is locked" in error_message
        or "database is busy" in error_message
        or "sqlite_busy" in error_message
        or "sqlite_locked" in error_message
    )


async def _record_audit(
    status: str,
    skus_processed: int,
    error_message: str | None,
):
    """Persist an audit record using an independent session."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                session.add(
                    ReconciliationAuditLog(
                        status="SUCCESS",
                        skus_processed=skus_processed,
                        error_message=None,
                    )
                )

    except Exception:
        logger.exception("Failed to persist reconciliation audit log")


async def process_reconciliation(items: list[dict]):
    """
    Process inventory updates in a background session.

    All stock updates and the SUCCESS audit log are committed
    in one transaction. SQLite lock errors trigger retries.
    Unknown SKUs fail the entire transaction.
    """

    for attempt in range(1, MAX_RETRIES + 1):

        skus_processed = 0

        try:
            async with AsyncSessionLocal() as session:

                async with session.begin():

                    skus = [item["sku"] for item in items]

                    result = await session.execute(
                        select(Product).where(Product.sku.in_(skus))
                    )

                    products = {
                        product.sku: product
                        for product in result.scalars().all()
                    }

                    unknown_skus = [
                        sku for sku in skus
                        if sku not in products
                    ]

                    if unknown_skus:
                        raise UnknownSKUError(
                            f"Unknown SKU(s) in manifest: {unknown_skus}"
                        )

                    for item in items:

                        await session.execute(
                            update(Product)
                            .where(Product.sku == item["sku"])
                            .values(
                                stock_quantity=item["stock_quantity"]
                            )
                        )

                    skus_processed = len(items)

                    # SUCCESS audit is part of the same transaction.
                    session.add(
                        ReconciliationAuditLog(
                            status="SUCCESS",
                            skus_processed=skus_processed,
                            error_message=None,
                        )
                    )

            # Transaction committed successfully.
            log_event(
                "reconciliation_completed",
                attempt=attempt,
                skus_processed=skus_processed,
                status="SUCCESS",
            )

            return

        except UnknownSKUError as exc:

            await _record_audit(
                status="FAILED",
                skus_processed=0,
                error_message=str(exc),
            )

            log_event(
                "reconciliation_failed_unknown_sku",
                status="FAILED",
                error=str(exc),
            )

            return

        except OperationalError as exc:

            if is_sqlite_lock_error(exc):

                if attempt < MAX_RETRIES:

                    log_event(
                        "reconciliation_retry",
                        attempt=attempt,
                        max_retries=MAX_RETRIES,
                        error=str(exc),
                    )

                    await asyncio.sleep(RETRY_DELAY * attempt)
                    continue

                await _record_audit(
                    status="RETRY_FALLBACK",
                    skus_processed=0,
                    error_message=(
                        f"SQLite lock retries exhausted after "
                        f"{MAX_RETRIES} attempts: {exc}"
                    ),
                )

                log_event(
                    "reconciliation_retry_exhausted",
                    attempts=MAX_RETRIES,
                    status="RETRY_FALLBACK",
                    error=str(exc),
                )

                return

            await _record_audit(
                status="FAILED",
                skus_processed=0,
                error_message=str(exc),
            )

            log_event(
                "reconciliation_operational_error",
                status="FAILED",
                error=str(exc),
            )

            return

        except SQLAlchemyError as exc:

            await _record_audit(
                status="FAILED",
                skus_processed=0,
                error_message=str(exc),
            )

            log_event(
                "reconciliation_database_error",
                status="FAILED",
                error=str(exc),
            )

            return

        except Exception as exc:

            await _record_audit(
                status="FAILED",
                skus_processed=0,
                error_message=str(exc),
            )

            log_event(
                "reconciliation_unexpected_error",
                status="FAILED",
                error=str(exc),
            )

            return
