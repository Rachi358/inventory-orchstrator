from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    """Dependency injection provider for database sessions."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Create database tables if they don't exist."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)