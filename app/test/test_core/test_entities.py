import pytest
from datetime import datetime, timedelta

from app.core.entities import User, Group, GroupMember, GroupRole, MeetingSlot

@pytest.mark.unit
class TestUserEntity:
    """Userエンティティのテスト"""
    
    def test_user_creation(self):
        """ユーザー作成テスト"""
        user = User(
            id=1,
            google_user_id="test123",
            email="test@example.com",
            name="Test User",
            created_at=datetime.now(),
            calendar_last_synced=None
        )
        
        assert user.id == 1
        assert user.google_user_id == "test123"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.calendar_last_synced is None
    
    def test_user_has_synced_calendar_false(self):
        """カレンダー未同期の場合のテスト"""
        user = User(
            id=1,
            google_user_id="test123",
            email="test@example.com",
            name="Test User",
            created_at=datetime.now(),
            calendar_last_synced=None
        )
        
        assert not user.has_synced_calendar()
    
    def test_user_has_synced_calendar_true(self):
        """カレンダー同期済みの場合のテスト"""
        user = User(
            id=1,
            google_user_id="test123",
            email="test@example.com",
            name="Test User",
            created_at=datetime.now(),
            calendar_last_synced=datetime.now()
        )
        
        assert user.has_synced_calendar()

@pytest.mark.unit
class TestGroupEntity:
    """Groupエンティティのテスト"""
    
    def test_group_creation(self):
        """グループ作成テスト"""
        group = Group(
            id=1,
            name="Test Group",
            description="Test Description",
            invite_code="TESTCODE",
            created_by=1,
            created_at=datetime.now(),
            is_active=True
        )
        
        assert group.id == 1
        assert group.name == "Test Group"
        assert group.description == "Test Description"
        assert group.invite_code == "TESTCODE"
        assert group.created_by == 1
        assert group.is_active is True
    
    def test_group_is_active_true(self):
        """アクティブグループのテスト"""
        group = Group(
            id=1,
            name="Test Group",
            description="Test Description",
            invite_code="TESTCODE",
            created_by=1,
            created_at=datetime.now(),
            is_active=True
        )
        
        assert group.is_active_group()
    
    def test_group_is_active_false(self):
        """非アクティブグループのテスト"""
        group = Group(
            id=1,
            name="Test Group",
            description="Test Description",
            invite_code="TESTCODE",
            created_by=1,
            created_at=datetime.now(),
            is_active=False
        )
        
        assert not group.is_active_group()

@pytest.mark.unit
class TestGroupMemberEntity:
    """GroupMemberエンティティのテスト"""
    
    def test_group_member_creation_admin(self):
        """管理者メンバー作成テスト"""
        member = GroupMember(
            id=1,
            group_id=1,
            user_id=1,
            role=GroupRole.ADMIN,
            joined_at=datetime.now()
        )
        
        assert member.id == 1
        assert member.group_id == 1
        assert member.user_id == 1
        assert member.role == GroupRole.ADMIN
        assert member.is_admin()
        assert not member.is_member()
    
    def test_group_member_creation_member(self):
        """一般メンバー作成テスト"""
        member = GroupMember(
            id=1,
            group_id=1,
            user_id=1,
            role=GroupRole.MEMBER,
            joined_at=datetime.now()
        )
        
        assert member.role == GroupRole.MEMBER
        assert not member.is_admin()
        assert member.is_member()
    
    def test_group_role_enum_values(self):
        """GroupRole enumの値テスト"""
        assert GroupRole.ADMIN.value == "admin"
        assert GroupRole.MEMBER.value == "member"

@pytest.mark.unit
class TestMeetingSlotEntity:
    """MeetingSlotエンティティのテスト"""
    
    def test_meeting_slot_creation(self):
        """ミーティングスロット作成テスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        slot = MeetingSlot(
            date="2024-01-15",
            start_time="10:00",
            end_time="11:00",
            start_datetime=start_time,
            end_datetime=end_time,
            duration_minutes=60,
            available_members=["user1@example.com", "user2@example.com"],
            busy_members=[]
        )
        
        assert slot.date == "2024-01-15"
        assert slot.start_time == "10:00"
        assert slot.end_time == "11:00"
        assert slot.duration_minutes == 60
        assert len(slot.available_members) == 2
        assert len(slot.busy_members) == 0
    
    def test_meeting_slot_duration_calculation(self):
        """ミーティングスロットの継続時間計算テスト"""
        start_time = datetime(2024, 1, 15, 10, 0)
        end_time = datetime(2024, 1, 15, 11, 30)
        
        slot = MeetingSlot(
            date="2024-01-15",
            start_time="10:00",
            end_time="11:30",
            start_datetime=start_time,
            end_datetime=end_time,
            duration_minutes=90,
            available_members=["user1@example.com"],
            busy_members=[]
        )
        
        calculated_duration = slot.get_duration_minutes()
        assert calculated_duration == 90
    
    def test_meeting_slot_all_available(self):
        """全員が空いているスロットのテスト"""
        slot = MeetingSlot(
            date="2024-01-15",
            start_time="10:00",
            end_time="11:00",
            start_datetime=datetime.now(),
            end_datetime=datetime.now() + timedelta(hours=1),
            duration_minutes=60,
            available_members=["user1@example.com", "user2@example.com"],
            busy_members=[]
        )
        
        assert slot.is_all_available()
        assert not slot.has_conflicts()
    
    def test_meeting_slot_with_conflicts(self):
        """競合があるスロットのテスト"""
        slot = MeetingSlot(
            date="2024-01-15",
            start_time="10:00",
            end_time="11:00",
            start_datetime=datetime.now(),
            end_datetime=datetime.now() + timedelta(hours=1),
            duration_minutes=60,
            available_members=["user1@example.com"],
            busy_members=["user2@example.com"]
        )
        
        assert not slot.is_all_available()
        assert slot.has_conflicts()

@pytest.mark.unit
class TestGroupRoleEnum:
    """GroupRole enumのテスト"""
    
    def test_group_role_string_conversion(self):
        """文字列変換テスト"""
        assert str(GroupRole.ADMIN) == "admin"
        assert str(GroupRole.MEMBER) == "member"
    
    def test_group_role_comparison(self):
        """enum比較テスト"""
        admin1 = GroupRole.ADMIN
        admin2 = GroupRole.ADMIN
        member = GroupRole.MEMBER
        
        assert admin1 == admin2
        assert admin1 != member
        assert member != admin1 