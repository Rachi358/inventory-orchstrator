
import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal, init_db, engine
from app.models import Product


SAMPLE_PRODUCTS = [
    Product(
        sku="LAPTOP001",
        name="Enterprise Laptop",
        stock_quantity=50,
        warehouse_location="WH-A1",
        base_price_usd=1200.00,
        is_active=True,
    ),
    Product(
        sku="MOUSE001",
        name="Wireless Mouse",
        stock_quantity=120,
        warehouse_location="WH-A2",
        base_price_usd=25.00,
        is_active=True,
    ),
    Product(
        sku="KEYBOARD001",
        name="Mechanical Keyboard",
        stock_quantity=30,
        warehouse_location="WH-B1",
        base_price_usd=75.00,
        is_active=True,
    ),
    Product(
        sku="MONITOR001",
        name="4K Monitor",
        stock_quantity=8,
        warehouse_location="WH-B2",
        base_price_usd=350.00,
        is_active=True,
    ),
    Product(
        sku="OLD001",
        name="Discontinued Product",
        stock_quantity=0,
        warehouse_location="WH-C1",
        base_price_usd=10.00,
        is_active=False,
    ),
]


async def seed_database():
    await init_db()

    async with AsyncSessionLocal() as session:
        async with session.begin():
            for product in SAMPLE_PRODUCTS:
                existing = await session.execute(
                    select(Product).where(
                        Product.sku == product.sku
                    )
                )

                if existing.scalar_one_or_none() is None:
                    session.add(product)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
