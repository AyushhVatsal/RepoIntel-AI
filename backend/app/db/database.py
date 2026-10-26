import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

if sys.platform == "win32":
    for candidate in [
        r"C:\Program Files\PostgreSQL\18\bin",
        r"C:\Program Files\PostgreSQL\17\bin",
        r"C:\Program Files\PostgreSQL\16\bin",
    ]:
        if os.path.isdir(candidate):
            try:
                os.add_dll_directory(candidate)
            except Exception:
                pass
            os.environ["PATH"] = candidate + ";" + os.environ.get("PATH", "")
            break

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass

engine = create_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    bind=engine,
)