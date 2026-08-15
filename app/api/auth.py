"""认证 API — 注册 / 登录 / 当前用户。"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import clear_auth_cookie, create_token, get_current_user, hash_password, set_auth_cookie, verify_password
from app.core.limiter import limiter
from app.db import get_db
from app.models import User

router = APIRouter()


class RegisterIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, description="用户名，3-30 字符")
    password: str = Field(..., min_length=6, max_length=64, description="密码，至少 6 位")


class LoginIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=30)
    password: str = Field(..., min_length=1, max_length=64)


@router.post("/register")
async def register(data: RegisterIn, response: Response, db: Session = Depends(get_db)):
    """注册新用户，返回 JWT token。"""
    username = data.username.strip()
    if not username:
        raise HTTPException(status_code=422, detail="用户名不能为空")
    exists = db.query(User).filter(User.username == username).first()
    if exists:
        raise HTTPException(status_code=409, detail="用户名已存在，请直接登录")
    user = User(username=username, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user.id)
    set_auth_cookie(response, token)
    return {"success": True, "token": token, "user": user.to_dict()}


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, response: Response, data: LoginIn, db: Session = Depends(get_db)):
    """登录，返回 JWT token。"""
    user = db.query(User).filter(User.username == data.username.strip()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_token(user.id)
    set_auth_cookie(response, token)
    return {"success": True, "token": token, "user": user.to_dict()}


@router.post("/logout")
async def logout(response: Response):
    """清除登录 Cookie。"""
    clear_auth_cookie(response)
    return {"success": True}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    """当前登录用户信息。"""
    return {"user": user.to_dict()}
