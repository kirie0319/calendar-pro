from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .core.config import settings
from .api import auth, groups, meetings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時
    print("🚀 Clean Architecture FastAPI アプリケーション起動中...")
    print(f"📊 登録されたルート数: {len(app.routes)}")
    print("✅ アプリケーション起動完了")
    yield
    # 終了時
    print("🛑 アプリケーション終了中...")
    print("✅ 正常終了")


# FastAPIアプリケーション作成
app = FastAPI(
    title="Calendar Project - Clean Architecture",
    description="Google Calendar OAuth FastAPI with Clean Architecture",
    version="1.0.0",
    lifespan=lifespan
)

# CORS設定（最低限）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # フロントエンド開発用
        "http://localhost:8000",  # バックエンド開発用
        "http://127.0.0.1:8000",  # バックエンド開発用（IP指定）
    ],
    allow_credentials=True,  # OAuth認証でCookieを使用するため必須
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# セッションミドルウェア設定
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=86400,  # 24時間
    same_site='lax',  # OAuth リダイレクトで必要
    https_only=True  # localhost での開発用
)

# ルーター登録
app.include_router(auth.router, tags=["認証"])
app.include_router(groups.router, tags=["グループ"])
app.include_router(meetings.router, tags=["ミーティング"])

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
