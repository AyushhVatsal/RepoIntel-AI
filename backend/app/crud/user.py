from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Retrieve a user by ID."""
    statement = select(User).where(User.id == user_id)
    return db.scalar(statement)


def get_user_by_email(db: Session, email: str) -> User | None:
    """Retrieve a user by email."""
    statement = select(User).where(User.email == email)
    return db.scalar(statement)


def create_user(db: Session, user_data: UserCreate) -> User:
    """Create a new user."""

    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    """Authenticate a user by email and password."""

    user = get_user_by_email(db, email)

    if user is None:
        return None

    if not verify_password(
        password,
        user.hashed_password,
    ):
        return None

    return user