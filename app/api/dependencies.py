from fastapi import Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
from pathlib import Path

from app.infrastructure.database import get_db
from app.core.entities import User
from app.service.auth_service import auth_service
from app.core.config import settings

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
    """ユーザーの認証情報を取得（設定から不足フィールドを補完）"""
    credentials = request.session.get('credentials', {})
    
    if not credentials:
        return None
    
    # 設定から不足しているフィールドを補完
    complete_credentials = {
        'token': credentials.get('token'),
        'refresh_token': credentials.get('refresh_token'),
        'token_uri': credentials.get('token_uri', 'https://oauth2.googleapis.com/token'),
        'client_id': credentials.get('client_id') or settings.GOOGLE_CLIENT_ID,
        'client_secret': credentials.get('client_secret') or settings.GOOGLE_CLIENT_SECRET,
        'scopes': credentials.get('scopes', settings.GOOGLE_SCOPES)
    }
    
    # 必須フィールドの確認
    required_fields = ['token', 'client_id', 'client_secret']
    for field in required_fields:
        if not complete_credentials.get(field):
            print(f"❌ 認証情報に必須フィールド '{field}' が不足しています")
            return None
    
    print(f"✅ 完全な認証情報を取得しました")
    return complete_credentials
