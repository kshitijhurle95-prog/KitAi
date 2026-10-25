"""SQLAlchemy models and database initialization."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency for obtaining async DB session."""
    async with async_session() as session:
        yield session


async def create_tables():
    """Create all tables defined in models."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Import models so they are registered with Base metadata
from app.models.user import User  # noqa
from app.models.conversation import Conversation, Message  # noqa
from app.models.experience import Experience  # noqa
from app.models.flashcard import Flashcard, QuizResult  # noqa
