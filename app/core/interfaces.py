from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from .entities import User, Group, GroupMember, CalendarEvent, MeetingSlot

class UserRepository(ABC):
    """ユーザーリポジトリインターフェース"""
    
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        """IDでユーザーを取得"""
        pass
    
    @abstractmethod
    def get_by_google_id(self, google_user_id: str) -> Optional[User]:
        """Google IDでユーザーを取得"""
        pass
    
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """メールアドレスでユーザーを取得"""
        pass
    
    @abstractmethod
    def create(self, user: User) -> User:
        """ユーザーを作成"""
        pass
    
    @abstractmethod
    def update(self, user: User) -> User:
        """ユーザーを更新"""
        pass

class GroupRepository(ABC):
    """グループリポジトリインターフェース"""
    
    @abstractmethod
    def get_by_id(self, group_id: int) -> Optional[Group]:
        """IDでグループを取得"""
        pass
    
    @abstractmethod
    def get_by_invite_code(self, invite_code: str) -> Optional[Group]:
        """招待コードでグループを取得"""
        pass
    
    @abstractmethod
    def get_user_groups(self, user_id: int) -> List[Group]:
        """ユーザーが所属するグループを取得"""
        pass
    
    @abstractmethod
    def create(self, group: Group) -> Group:
        """グループを作成"""
        pass
    
    @abstractmethod
    def update(self, group: Group) -> Group:
        """グループを更新"""
        pass

class GroupMemberRepository(ABC):
    """グループメンバーリポジトリインターフェース"""
    
    @abstractmethod
    def get_by_group_and_user(self, group_id: int, user_id: int) -> Optional[GroupMember]:
        """グループとユーザーでメンバーシップを取得"""
        pass
    
    @abstractmethod
    def get_group_members(self, group_id: int) -> List[GroupMember]:
        """グループのメンバー一覧を取得"""
        pass
    
    @abstractmethod
    def add_member(self, membership: GroupMember) -> GroupMember:
        """メンバーを追加"""
        pass
    
    @abstractmethod
    def remove_member(self, group_id: int, user_id: int) -> bool:
        """メンバーを削除"""
        pass

class CalendarEventRepository(ABC):
    """カレンダーイベントリポジトリインターフェース"""
    
    @abstractmethod
    def get_user_events(self, user_id: int, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """ユーザーの指定期間のイベントを取得"""
        pass
    
    @abstractmethod
    def get_multiple_users_events(self, user_emails: List[str], start_date: datetime, end_date: datetime) -> dict:
        """複数ユーザーのイベントを一括取得"""
        pass
    
    @abstractmethod
    def sync_user_events(self, user_id: int, events: List[CalendarEvent]) -> int:
        """ユーザーのイベントを同期（既存削除→新規追加）"""
        pass
    
    @abstractmethod
    def clear_user_events(self, user_id: int) -> bool:
        """ユーザーのイベントを全削除"""
        pass

class GoogleCalendarService(ABC):
    """Google Calendarサービスインターフェース"""
    
    @abstractmethod
    def get_user_info(self, credentials: dict) -> dict:
        """ユーザー情報を取得"""
        pass
    
    @abstractmethod
    def get_calendar_events(self, credentials: dict, start_date: datetime, end_date: datetime) -> List[dict]:
        """カレンダーイベントを取得"""
        pass
    
    @abstractmethod
    def create_oauth_flow(self, redirect_uri: str) -> tuple:
        """OAuth認証フローを作成 -> (authorization_url, state)"""
        pass
    
    @abstractmethod
    def complete_oauth_flow(self, authorization_response: str, state: str) -> dict:
        """OAuth認証を完了 -> credentials"""
        pass 