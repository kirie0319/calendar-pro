from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.dependencies import get_database_session, get_templates, get_current_user_optional, get_current_user
from app.service.auth_service import auth_service
from app.core.config import settings

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request, 
    templates: Jinja2Templates = Depends(get_templates),
    current_user = Depends(get_current_user_optional)
):
    """メインページ"""
    if current_user:
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(url=f"{frontend_url}/dashboard", status_code=302)
    
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/login")
async def login(request: Request):
    """Google OAuth認証を開始"""
    try:
        print(f"🔍 ログイン開始 - セッション keys: {list(request.session.keys())}")
        
        # 既に認証済みかチェック
        if 'user_id' in request.session and 'credentials' in request.session:
            print(f"✅ 既に認証済みのユーザーです - ダッシュボードにリダイレクト")
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            return RedirectResponse(url=f"{frontend_url}/dashboard", status_code=302)
        
        authorization_url, state = auth_service.get_authorization_url()
        
        print(f"🔍 生成された state: {state}")
        print(f"🔍 Authorization URL: {authorization_url}")
        
        # セッションにstateを保存
        request.session['state'] = state
        
        print(f"🔍 state をセッションに保存しました")
        print(f"🔍 保存後のセッション keys: {list(request.session.keys())}")
        
        return RedirectResponse(url=authorization_url, status_code=302)
    except Exception as e:
        print(f"❌ ログイン開始エラー: {e}")
        raise HTTPException(status_code=500, detail="認証の開始に失敗しました")

@router.get("/auth/callback")
async def callback(request: Request, db: Session = Depends(get_database_session)):
    """OAuth認証のコールバック処理"""
    try:
        # 既に認証済みかチェック
        if 'user_id' in request.session and 'credentials' in request.session:
            print(f"✅ 既に認証済みユーザーのコールバック - ダッシュボードにリダイレクト")
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            return RedirectResponse(url=f"{frontend_url}/dashboard", status_code=302)
        
        # OAuth認証を処理
        result = auth_service.handle_oauth_callback(request, db)
        
        user = result['user']
        credentials = result['credentials']
        sync_success = result['sync_success']
        
        # セッションを更新
        auth_service.update_session(request, user, credentials)
        
        if sync_success:
            print(f"✅ ユーザー {user.id} のカレンダー同期が完了しました")
        else:
            print(f"⚠️ ユーザー {user.id} のカレンダー同期に失敗しましたが、ログインは継続します")
        
        # 使用済みのstateを削除
        request.session.pop('state', None)
        
        # フロントエンドのダッシュボードにリダイレクト
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        redirect_url = f"{frontend_url}/dashboard"
        print(f"🔗 フロントエンドダッシュボードにリダイレクト中: {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except HTTPException as e:
        # HTTPExceptionの場合、特別な処理
        if e.status_code == 409:  # User already authenticated
            print(f"✅ 既に認証済みユーザー - ダッシュボードにリダイレクト")
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            return RedirectResponse(url=f"{frontend_url}/dashboard", status_code=302)
        raise
    except Exception as e:
        # エラーが発生した場合はセッションをクリアして最初から
        auth_service.clear_session(request)
        print(f"❌ 認証コールバックエラー: {e}")
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        error_url = f"{frontend_url}/login?error=auth_failed"
        return RedirectResponse(url=error_url, status_code=302)

@router.get("/logout")
async def logout(request: Request):
    """ログアウト"""
    auth_service.clear_session(request)
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    return RedirectResponse(url=f"{frontend_url}/login", status_code=302)

@router.get("/status")
async def status():
    """API ステータス確認用エンドポイント"""
    return {
        "status": "running",
        "framework": "FastAPI",
        "version": "1.0.0",
        "architecture": "Clean Architecture",
        "features": [
            "Google OAuth 2.0",
            "Google Calendar API",
            "グループ管理",
            "ミーティングスケジューラー",
            "DB保存型カレンダー同期"
        ]
    }

@router.get("/auth/user")
async def get_current_user_info(
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """現在のユーザー情報を取得"""
    try:
        return {
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "name": current_user.name,
                "google_user_id": current_user.google_user_id,
                "calendar_synced": current_user.is_calendar_synced(),
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None
            }
        }
    except Exception as e:
        print(f"❌ ユーザー情報取得エラー: {e}")
        return {
            "authenticated": False,
            "error": "ユーザー情報の取得に失敗しました"
        }

@router.get("/auth/check")
async def check_auth(request: Request):
    """認証状態を確認"""
    try:
        if 'user_id' in request.session and 'credentials' in request.session:
            return {
                "authenticated": True,
                "message": "認証済み"
            }
        else:
            return {
                "authenticated": False,
                "message": "未認証"
            }
    except Exception as e:
        print(f"❌ 認証チェックエラー: {e}")
        return {
            "authenticated": False,
            "error": "認証状態の確認に失敗しました"
        }

@router.get("/debug/info")
async def debug_info():
    """デバッグ情報表示（開発用）"""
    import sys
    
    # メモリ使用量は簡易版で取得
    try:
        import psutil
        memory_info = {
            "memory_usage_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2),
            "cpu_percent": psutil.Process().cpu_percent()
        }
    except ImportError:
        memory_info = {
            "memory_usage_mb": "psutil not installed",
            "cpu_percent": "psutil not installed"
        }
    
    return {
        "process_info": {
            **memory_info,
            "python_version": sys.version.split()[0]
        },
        "session_info": {
            "middleware": "SessionMiddleware",
            "storage": "memory",
            "max_age": "86400 seconds (24 hours)"
        },
        "concurrent_support": {
            "async_framework": "FastAPI",
            "session_isolation": "per_user",
            "oauth_state_isolation": "per_session"
        },
        "architecture": {
            "pattern": "Clean Architecture",
            "layers": ["API", "Service", "Core", "Infrastructure"],
            "dependency_direction": "Inward"
        }
    }
