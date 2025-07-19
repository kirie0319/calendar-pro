from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional

from app.infrastructure.models import User

class UserRepository:
    def get_or_create_user(self, session: Session, google_user_id: str, email: str, name: str) -> User:
        """ユーザーを取得または作成"""
        # 既存ユーザーを検索
        result = session.execute(select(User).where(User.google_user_id == google_user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            # 新規ユーザー作成
            user = User(
                google_user_id=google_user_id,
                email=email,
                name=name
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"✅ 新規ユーザーを作成しました: {email}")
        
        return user
    
    def get_user_by_id(self, session: Session, user_id: int) -> Optional[User]:
        """IDでユーザーを取得"""
        result = session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    def get_user_by_email(self, session: Session, email: str) -> Optional[User]:
        """メールアドレスでユーザーを取得"""
        result = session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    def get_user_by_google_id(self, session: Session, google_user_id: str) -> Optional[User]:
        """Google User IDでユーザーを取得"""
        result = session.execute(select(User).where(User.google_user_id == google_user_id))
        return result.scalar_one_or_none()
    
    def update_user_calendar_sync(self, session: Session, user_id: int) -> bool:
        """ユーザーのカレンダー同期時刻を更新"""
        from datetime import datetime
        
        try:
            user = self.get_user_by_id(session, user_id)
            if user:
                user.calendar_last_synced = datetime.now()
                session.commit()
                return True
            return False
        except Exception as e:
            print(f"❌ カレンダー同期時刻更新エラー: {e}")
            session.rollback()
            return False

# グローバルインスタンス
user_repository = UserRepository() 