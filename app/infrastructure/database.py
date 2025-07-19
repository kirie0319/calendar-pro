import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from app.infrastructure.models import Base

# 環境変数を読み込み
load_dotenv()

# .envファイルからデータベースURLを取得
DATABASE_URL = os.getenv('DATABASE_URL', "sqlite:///./calendar_app.db")

# PostgreSQLの場合、psycopg3用のURL形式に変換
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)

# 同期エンジンの作成（PostgreSQL/SQLite対応）
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def get_db():
    """データベースセッションを取得"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def init_db():
    """データベースを初期化（テーブル作成）"""
    # 既存のテーブルを削除してから再作成
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    print("✅ データベースが初期化されました") 