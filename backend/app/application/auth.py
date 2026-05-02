from datetime import datetime, timedelta, UTC
from jose import jwt, JWTError
import bcrypt
from app.config import settings
from app.infrastructure.repositories import UserRepository
from app.infrastructure.models import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expire}, settings.secret_key, settings.algorithm)


def decode_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.secret_key, [settings.algorithm])
        return int(payload["sub"])
    except JWTError:
        return None


async def authenticate(email: str, password: str, repo: UserRepository) -> User | None:
    user = await repo.get_by_email(email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
