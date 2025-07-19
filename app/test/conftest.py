import pytest
import tempfile
import os
from datetime import datetime, timedelta
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.infrastructure.models import Base, User, Group, GroupMember, CalendarEvent
from app.infrastructure.database import get_db
from app.api.dependencies import get_database_session

# テスト用インメモリデータベース設定
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def test_engine():
    """テスト用SQLiteエンジン"""
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False  # テスト時はSQL出力を抑制
    )
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="function")
def test_db_session(test_engine) -> Generator[Session, None, None]:
    """テスト用データベースセッション（各テスト関数ごとに新しいセッション）"""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        # テスト後にデータをクリア
        session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()

@pytest.fixture(scope="function")
def test_client(test_db_session: Session):
    """テスト用FastAPIクライアント"""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass
    
    app.dependency_overrides[get_database_session] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    # 依存関係オーバーライドをクリア
    app.dependency_overrides.clear()

# セッション操作のヘルパー関数
def set_session_data(client: TestClient, session_data: dict):
    """TestClientにセッションデータを設定するヘルパー"""
    import base64
    import json
    from itsdangerous import URLSafeSerializer
    from starlette.middleware.sessions import SessionMiddleware
    
    # アプリケーションと同じSECRET_KEYを使用（テスト用フォールバック付き）
    try:
        from app.core.config import settings
        secret_key = settings.SECRET_KEY or "test_secret_key_for_testing_only"
    except:
        secret_key = "test_secret_key_for_testing_only"
    
    # セッションデータをSessionMiddleware形式でシリアライズ
    serializer = URLSafeSerializer(secret_key)
    session_cookie = serializer.dumps(session_data)
    
    # Cookieとして設定
    client.cookies.set("session", session_cookie)

def setup_authenticated_client(client: TestClient, test_user):
    """認証済みクライアントを設定するヘルパー（依存性オーバーライド版）"""
    from app.api.dependencies import get_current_user, get_current_user_optional
    from app.core.entities import User
    
    def create_test_user():
        # SQLAlchemyオブジェクトから安全に値を取得してUserエンティティに変換
        try:
            # SQLAlchemyオブジェクトの場合、__dict__から直接値を取得（DBアクセスを回避）
            if hasattr(test_user, '__dict__') and hasattr(test_user, '_sa_instance_state'):
                # SQLAlchemyオブジェクトの場合
                obj_dict = test_user.__dict__
                user_data = {
                    'id': obj_dict.get('id', None),
                    'google_user_id': obj_dict.get('google_user_id', ''),
                    'email': obj_dict.get('email', ''),
                    'name': obj_dict.get('name', ''),
                    'created_at': obj_dict.get('created_at', None),
                    'calendar_last_synced': obj_dict.get('calendar_last_synced', None)
                }
            else:
                # 通常のオブジェクトの場合
                user_data = {
                    'id': test_user.id,
                    'google_user_id': test_user.google_user_id,
                    'email': test_user.email,
                    'name': test_user.name,
                    'created_at': test_user.created_at,
                    'calendar_last_synced': test_user.calendar_last_synced
                }
        except Exception:
            # エラーの場合はデフォルト値を使用
            user_data = {
                'id': 1,
                'google_user_id': 'test_google_123',
                'email': 'test@example.com',
                'name': 'Test User',
                'created_at': None,
                'calendar_last_synced': None
            }
        
        return User(**user_data)
    
    def override_get_current_user():
        return create_test_user()
    
    def override_get_current_user_optional():
        return create_test_user()
    
    # 両方の依存性をオーバーライド
    client.app.dependency_overrides[get_current_user] = override_get_current_user
    client.app.dependency_overrides[get_current_user_optional] = override_get_current_user_optional
    
    return client

def clear_authenticated_client(client: TestClient):
    """認証クライアントの設定をクリア"""
    from app.api.dependencies import get_current_user, get_current_user_optional
    client.app.dependency_overrides.pop(get_current_user, None)
    client.app.dependency_overrides.pop(get_current_user_optional, None)

# テストデータフィクスチャ

@pytest.fixture
def sample_user_data():
    """サンプルユーザーデータ"""
    return {
        'google_user_id': 'test_google_123',
        'email': 'test@example.com',
        'name': 'Test User'
    }

@pytest.fixture
def sample_group_data():
    """サンプルグループデータ"""
    return {
        'name': 'Test Group',
        'description': 'Test group description',
        'invite_code': 'TESTCODE123'
    }

@pytest.fixture
def sample_calendar_event_data():
    """サンプルカレンダーイベントデータ"""
    base_time = datetime.now()
    return {
        'google_event_id': 'test_event_123',
        'start_datetime': base_time,
        'end_datetime': base_time + timedelta(hours=1),
        'title': 'Test Meeting',
        'is_all_day': False
    }

@pytest.fixture
def test_user(test_db_session: Session, sample_user_data):
    """テスト用ユーザー作成"""
    user = User(**sample_user_data)
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user

@pytest.fixture
def test_group(test_db_session: Session, test_user, sample_group_data):
    """テスト用グループ作成"""
    group_data = sample_group_data.copy()
    group_data['created_by'] = test_user.id
    
    group = Group(**group_data)
    test_db_session.add(group)
    test_db_session.commit()
    test_db_session.refresh(group)
    
    # 作成者をメンバーとして追加
    membership = GroupMember(
        group_id=group.id,
        user_id=test_user.id,
        role="admin"
    )
    test_db_session.add(membership)
    test_db_session.commit()
    
    return group

@pytest.fixture
def test_calendar_event(test_db_session: Session, test_user, sample_calendar_event_data):
    """テスト用カレンダーイベント作成"""
    event_data = sample_calendar_event_data.copy()
    event_data['user_id'] = test_user.id
    
    event = CalendarEvent(**event_data)
    test_db_session.add(event)
    test_db_session.commit()
    test_db_session.refresh(event)
    return event

# 認証モック用フィクスチャ

@pytest.fixture
def mock_session_data(test_user):
    """モックセッションデータ"""
    return {
        'user_id': test_user.id,
        'user_email': test_user.email,
        'user_name': test_user.name,
        'credentials': {
            'token': 'mock_token',
            'refresh_token': 'mock_refresh_token'
        }
    }

@pytest.fixture
def authenticated_client(test_client: TestClient, mock_session_data):
    """認証済みクライアント"""
    set_session_data(test_client, mock_session_data)
    return test_client

# 環境変数モック

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """テスト用環境変数"""
    test_env = {
        'GOOGLE_CLIENT_ID': 'test_client_id',
        'GOOGLE_CLIENT_SECRET': 'test_client_secret',
        'GOOGLE_REDIRECT_URI': 'http://localhost:8000/auth/callback',
        'SECRET_KEY': 'test_secret_key_for_testing_only',
        'DATABASE_URL': 'sqlite:///:memory:'
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

# テストカテゴリマーカー

def pytest_configure(config):
    """pytest設定"""
    config.addinivalue_line(
        "markers", "unit: 単体テスト"
    )
    config.addinivalue_line(
        "markers", "integration: 統合テスト"
    )
    config.addinivalue_line(
        "markers", "slow: 時間のかかるテスト"
    )
    config.addinivalue_line(
        "markers", "api: APIテスト"
    ) 