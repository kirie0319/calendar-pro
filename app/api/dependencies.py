from fastapi import Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
from pathlib import Path

from app.infrastructure.database import get_db
from app.core.entities import User
from app.service.auth_service import auth_service

# テンプレート設定（絶対パスで指定）
template_dir = Path(__file__).parent.parent.parent / "templates"
if not template_dir.exists():
    # app/presentation/templates も試す
    template_dir = Path(__file__).parent.parent / "presentation" / "templates"

templates = Jinja2Templates(directory=str(template_dir))

def get_database_session() -> Session:
    """データベースセッションを取得"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_database_session)) -> User:
    """現在認証されているユーザーを取得"""
    return auth_service.get_current_user(request, db)

def get_current_user_optional(request: Request, db: Session = Depends(get_database_session)) -> User:
    """現在認証されているユーザーを取得（認証が必要ない場合）"""
    try:
        return auth_service.get_current_user(request, db)
    except HTTPException:
        return None

def get_templates() -> Jinja2Templates:
    """Jinja2テンプレートを取得"""
    return templates

def get_user_credentials(request: Request) -> dict:
    """ユーザーの認証情報を取得"""
    return request.session.get('credentials', {})
