from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum
import uuid

class GroupRole(Enum):
    """グループ内での役割"""
    ADMIN = "admin"
    MEMBER = "member"
    
    def __str__(self):
        return self.value

@dataclass
class User:
    """ユーザーエンティティ"""
    id: Optional[int] = None
    google_user_id: str = ""
    email: str = ""
    name: str = ""
    created_at: Optional[datetime] = None
    calendar_last_synced: Optional[datetime] = None
    
    def is_calendar_synced(self) -> bool:
        """カレンダーが同期済みかチェック"""
        return self.calendar_last_synced is not None
    
    def has_synced_calendar(self) -> bool:
        """カレンダーが同期済みかどうかを判定（テスト用エイリアス）"""
        return self.is_calendar_synced()
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class Group:
    """グループエンティティ"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    invite_code: str = ""
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    is_active: bool = True
    
    def generate_invite_code(self) -> str:
        """新しい招待コードを生成"""
        self.invite_code = str(uuid.uuid4()).replace('-', '')[:12].upper()
        return self.invite_code
    
    def is_active_group(self) -> bool:
        """グループがアクティブかどうかを判定"""
        return self.is_active
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if not self.invite_code:
            self.generate_invite_code()

@dataclass
class GroupMember:
    """グループメンバーエンティティ"""
    id: Optional[int] = None
    group_id: int = 0
    user_id: int = 0
    role: GroupRole = GroupRole.MEMBER
    joined_at: Optional[datetime] = None
    
    def is_admin(self) -> bool:
        """管理者権限を持つかチェック"""
        return self.role == GroupRole.ADMIN
    
    def is_member(self) -> bool:
        """一般メンバーかどうかを判定"""
        return self.role == GroupRole.MEMBER
    
    def __post_init__(self):
        if self.joined_at is None:
            self.joined_at = datetime.now()

@dataclass
class CalendarEvent:
    """カレンダーイベントエンティティ"""
    id: Optional[int] = None
    user_id: int = 0
    google_event_id: str = ""
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    title: str = "無題"
    is_all_day: bool = False
    created_at: Optional[datetime] = None
    
    def duration_minutes(self) -> int:
        """イベントの時間（分）を計算"""
        if self.start_datetime and self.end_datetime:
            delta = self.end_datetime - self.start_datetime
            return int(delta.total_seconds() / 60)
        return 0
    
    def is_overlapping(self, other_start: datetime, other_end: datetime) -> bool:
        """他の時間帯と重複するかチェック"""
        if not self.start_datetime or not self.end_datetime:
            return False
        return (self.start_datetime < other_end and 
                self.end_datetime > other_start)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class MeetingSlot:
    """ミーティング可能時間スロット"""
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    start_datetime: datetime
    end_datetime: datetime
    duration_minutes: int
    available_members: List[str]
    busy_members: List[str]
    
    def availability_rate(self) -> float:
        """空いているメンバーの割合"""
        total = len(self.available_members) + len(self.busy_members)
        if total == 0:
            return 0.0
        return len(self.available_members) / total 
    
    def get_duration_minutes(self) -> int:
        """継続時間（分）を取得"""
        return self.duration_minutes
    
    def is_all_available(self) -> bool:
        """全員が利用可能かどうかを判定"""
        return len(self.busy_members) == 0
    
    def has_conflicts(self) -> bool:
        """競合があるかどうかを判定"""
        return len(self.busy_members) > 0 