from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

# App database — read-write, stores conversations, messages, pipeline state
app_engine = create_async_engine(settings.DATABASE_APP_URL, echo=False)
AppSession = async_sessionmaker(app_engine, expire_on_commit=False)

# Target database — read-only, the SaaS dataset the agent queries
target_engine = create_async_engine(settings.DATABASE_TARGET_URL, echo=False)
TargetSession = async_sessionmaker(target_engine, expire_on_commit=False)
