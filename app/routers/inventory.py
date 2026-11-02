from app.models import Product, ReconciliationAuditLog
from app.services.utils import log_event
import logging
from fastapi import (
    APIRouter,
    Depends,
    Query,
    BackgroundTasks,
    status,
    HTTPException,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

from app.schemas import (
    ReconciliationRequest,
    ReconciliationResponse,
)
from app.services.sync_worker import process_reconciliation


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("")
async def get_paginated_inventory(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    min_stock: int | None = Query(None, ge=0),
    is_active: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch inventory with pagination and server-side filtering.
    """

    statement = select(Product).where(
        Product.is_active == is_active
    )

    if min_stock is not None:
        statement = statement.where(
            Product.stock_quantity >= min_stock
        )

    statement = (
        statement
        .order_by(Product.sku)
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(statement)
    products = result.scalars().all()

    return {
        "limit": limit,
        "offset": offset,
        "count": len(products),
        "items": [
            {
                "sku": product.sku,
                "name": product.name,
                "stock_quantity": product.stock_quantity,
                "warehouse_location": product.warehouse_location,
                "base_price_usd": product.base_price_usd,
                "is_active": product.is_active,
            }
            for product in products
        ],
    }


@router.get("/products/{sku}")
async def get_product(
    sku: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.sku == sku)
    )

    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return {
        "sku": product.sku,
        "name": product.name,
        "stock_quantity": product.stock_quantity,
        "warehouse_location": product.warehouse_location,
        "base_price_usd": product.base_price_usd,
        "is_active": product.is_active,
    }


@router.post(
    "/reconcile",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ReconciliationResponse,
)
async def trigger_bulk_reconciliation(
    payload: ReconciliationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Accept inventory updates and schedule reconciliation.
    """

    items = [
        item.model_dump()
        for item in payload.items
    ]

    background_tasks.add_task(
        process_reconciliation,
        items,
    )

    log_event(
    "reconciliation_task_accepted",
    items_received=len(items),
    status="PROCESSING",
)

    return ReconciliationResponse(
        message="Reconciliation accepted",
        status="PROCESSING",
        items_received=len(items),
    )



@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReconciliationAuditLog)
        .order_by(ReconciliationAuditLog.id.desc())
        .offset(offset)
        .limit(limit)
    )

    logs = result.scalars().all()

    return {
        "limit": limit,
        "offset": offset,
        "count": len(logs),
        "items": [
            {
                "id": log.id,
                "timestamp": log.timestamp,
                "status": log.status,
                "skus_processed": log.skus_processed,
                "error_message": log.error_message,
            }
            for log in logs
        ],
    }
