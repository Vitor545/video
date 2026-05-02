from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.infrastructure.repositories import UserRepository
from app.application.auth import authenticate, create_token, hash_password, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


class RegisterIn(BaseModel):
    email: EmailStr
    name: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenOut)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate(form.username, form.password, UserRepository(db))
    if not user:
        raise HTTPException(401, "Credenciais inválidas")
    return TokenOut(access_token=create_token(user.id))


@router.post("/register", status_code=201)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    if await repo.get_by_email(data.email):
        raise HTTPException(400, "Email já cadastrado")
    user = await repo.create(data.email, data.name, hash_password(data.password))
    return {"id": user.id, "email": user.email, "name": user.name}


async def get_current_user_id(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
) -> int:
    if not token:
        token = request.cookies.get("token") or request.cookies.get("access_token")
    if not token:
        raise HTTPException(401, "Token ausente")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "Token inválido")
    return user_id


@router.get("/me")
async def me(user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    user = await UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    return {"id": user.id, "email": user.email, "name": user.name}
