import pytest
from datetime import datetime, timedelta

from app.infrastructure.repositories.user_repository import user_repository
from app.infrastructure.repositories.group_repository import group_repository
from app.infrastructure.repositories.calendar_repository import calendar_repository
from app.infrastructure.models import User, Group, GroupMember, CalendarEvent

@pytest.mark.unit
class TestUserRepository:
    """UserRepositoryのテスト"""
    
    def test_get_or_create_user_new_user(self, test_db_session, sample_user_data):
        """新規ユーザー作成テスト"""
        user = user_repository.get_or_create_user(
            test_db_session,
            sample_user_data['google_user_id'],
            sample_user_data['email'],
            sample_user_data['name']
        )
        
        assert user.id is not None
        assert user.google_user_id == sample_user_data['google_user_id']
        assert user.email == sample_user_data['email']
        assert user.name == sample_user_data['name']
        assert user.created_at is not None
    
    def test_get_or_create_user_existing_user(self, test_db_session, test_user):
        """既存ユーザー取得テスト"""
        # 同じgoogle_user_idで再度呼び出し
        user = user_repository.get_or_create_user(
            test_db_session,
            test_user.google_user_id,
            test_user.email,
            test_user.name
        )
        
        # 同じユーザーが返されることを確認
        assert user.id == test_user.id
        assert user.google_user_id == test_user.google_user_id
        assert user.email == test_user.email
    
    def test_get_user_by_id_found(self, test_db_session, test_user):
        """ID検索成功テスト"""
        user = user_repository.get_user_by_id(test_db_session, test_user.id)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email
    
    def test_get_user_by_id_not_found(self, test_db_session):
        """ID検索失敗テスト"""
        user = user_repository.get_user_by_id(test_db_session, 99999)
        
        assert user is None
    
    def test_get_user_by_email_found(self, test_db_session, test_user):
        """メール検索成功テスト"""
        user = user_repository.get_user_by_email(test_db_session, test_user.email)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email
    
    def test_get_user_by_email_not_found(self, test_db_session):
        """メール検索失敗テスト"""
        user = user_repository.get_user_by_email(test_db_session, "nonexistent@example.com")
        
        assert user is None
    
    def test_get_user_by_google_id_found(self, test_db_session, test_user):
        """Google ID検索成功テスト"""
        user = user_repository.get_user_by_google_id(test_db_session, test_user.google_user_id)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.google_user_id == test_user.google_user_id
    
    def test_update_user_calendar_sync(self, test_db_session, test_user):
        """カレンダー同期時刻更新テスト"""
        original_sync_time = test_user.calendar_last_synced
        
        success = user_repository.update_user_calendar_sync(test_db_session, test_user.id)
        
        assert success is True
        
        # ユーザーを再取得して更新を確認
        updated_user = user_repository.get_user_by_id(test_db_session, test_user.id)
        assert updated_user.calendar_last_synced is not None
        if original_sync_time:
            assert updated_user.calendar_last_synced > original_sync_time

@pytest.mark.unit
class TestGroupRepository:
    """GroupRepositoryのテスト"""
    
    def test_create_group(self, test_db_session, test_user, sample_group_data):
        """グループ作成テスト"""
        group = group_repository.create_group(
            test_db_session,
            sample_group_data['name'],
            sample_group_data['description'],
            test_user.id
        )
        
        assert group.id is not None
        assert group.name == sample_group_data['name']
        assert group.description == sample_group_data['description']
        assert group.created_by == test_user.id
        assert group.invite_code is not None
        assert len(group.invite_code) == 12  # 招待コードの長さ確認
        assert group.is_active is True
        
        # 作成者が管理者として追加されているか確認
        membership = group_repository.get_user_membership(test_db_session, group.id, test_user.id)
        assert membership is not None
        assert membership.role == "admin"
    
    def test_get_group_by_id_found(self, test_db_session, test_group):
        """ID検索成功テスト"""
        group = group_repository.get_group_by_id(test_db_session, test_group.id)
        
        assert group is not None
        assert group.id == test_group.id
        assert group.name == test_group.name
    
    def test_get_group_by_id_not_found(self, test_db_session):
        """ID検索失敗テスト"""
        group = group_repository.get_group_by_id(test_db_session, 99999)
        
        assert group is None
    
    def test_get_group_by_invite_code_found(self, test_db_session, test_group):
        """招待コード検索成功テスト"""
        group = group_repository.get_group_by_invite_code(test_db_session, test_group.invite_code)
        
        assert group is not None
        assert group.id == test_group.id
        assert group.invite_code == test_group.invite_code
    
    def test_get_group_by_invite_code_not_found(self, test_db_session):
        """招待コード検索失敗テスト"""
        group = group_repository.get_group_by_invite_code(test_db_session, "INVALID")
        
        assert group is None
    
    def test_get_user_groups(self, test_db_session, test_user, test_group):
        """ユーザーグループ一覧取得テスト"""
        groups = group_repository.get_user_groups(test_db_session, test_user.id)
        
        assert len(groups) == 1
        assert groups[0]['id'] == test_group.id
        assert groups[0]['name'] == test_group.name
        assert groups[0]['role'] == "admin"
    
    def test_get_group_members(self, test_db_session, test_user, test_group):
        """グループメンバー一覧取得テスト"""
        members = group_repository.get_group_members(test_db_session, test_group.id)
        
        assert len(members) == 1
        assert members[0]['name'] == test_user.name
        assert members[0]['email'] == test_user.email
        assert members[0]['role'] == "admin"
    
    def test_add_user_to_group_success(self, test_db_session, test_group, sample_user_data):
        """グループメンバー追加成功テスト"""
        # 新しいユーザーを作成
        new_user = user_repository.get_or_create_user(
            test_db_session,
            "new_google_id",
            "new@example.com",
            "New User"
        )
        
        success = group_repository.add_user_to_group(test_db_session, test_group.id, new_user.id, "member")
        
        assert success is True
        
        # メンバーシップが作成されたか確認
        membership = group_repository.get_user_membership(test_db_session, test_group.id, new_user.id)
        assert membership is not None
        assert membership.role == "member"
    
    def test_add_user_to_group_already_member(self, test_db_session, test_user, test_group):
        """既存メンバー追加テスト（失敗）"""
        success = group_repository.add_user_to_group(test_db_session, test_group.id, test_user.id, "member")
        
        assert success is False  # 既にメンバーなので失敗

@pytest.mark.unit
class TestCalendarRepository:
    """CalendarRepositoryのテスト"""
    
    def test_sync_user_calendar_events(self, test_db_session, test_user, sample_calendar_event_data):
        """カレンダーイベント同期テスト"""
        events_data = [
            sample_calendar_event_data.copy(),
            {
                'google_event_id': 'test_event_456',
                'start_datetime': datetime.now() + timedelta(hours=2),
                'end_datetime': datetime.now() + timedelta(hours=3),
                'title': 'Another Meeting',
                'is_all_day': False
            }
        ]
        
        synced_count = calendar_repository.sync_user_calendar_events(
            test_db_session, test_user.id, events_data
        )
        
        assert synced_count == 2
        
        # イベントが正しく保存されたか確認
        start_date = datetime.now() - timedelta(hours=1)
        end_date = datetime.now() + timedelta(hours=4)
        events = calendar_repository.get_user_calendar_events(
            test_db_session, test_user.id, start_date, end_date
        )
        
        assert len(events) == 2
    
    def test_get_user_calendar_events(self, test_db_session, test_user, test_calendar_event):
        """ユーザーカレンダーイベント取得テスト"""
        start_date = test_calendar_event.start_datetime - timedelta(hours=1)
        end_date = test_calendar_event.end_datetime + timedelta(hours=1)
        
        events = calendar_repository.get_user_calendar_events(
            test_db_session, test_user.id, start_date, end_date
        )
        
        assert len(events) == 1
        assert events[0]['google_event_id'] == test_calendar_event.google_event_id
        assert events[0]['title'] == test_calendar_event.title
    
    def test_get_user_calendar_events_empty_result(self, test_db_session, test_user):
        """カレンダーイベント取得（空の結果）テスト"""
        future_start = datetime.now() + timedelta(days=30)
        future_end = future_start + timedelta(days=1)
        
        events = calendar_repository.get_user_calendar_events(
            test_db_session, test_user.id, future_start, future_end
        )
        
        assert len(events) == 0
    
    def test_get_user_calendar_events_for_period(self, test_db_session, test_user, test_calendar_event):
        """期間指定カレンダーイベント取得テスト（オブジェクト形式）"""
        start_date = test_calendar_event.start_datetime - timedelta(hours=1)
        end_date = test_calendar_event.end_datetime + timedelta(hours=1)
        
        events = calendar_repository.get_user_calendar_events_for_period(
            test_db_session, test_user.id, start_date, end_date
        )
        
        assert len(events) == 1
        assert isinstance(events[0], CalendarEvent)
        assert events[0].id == test_calendar_event.id
    
    def test_get_multiple_users_calendar_events(self, test_db_session, test_user, test_calendar_event):
        """複数ユーザーカレンダーイベント取得テスト"""
        start_date = test_calendar_event.start_datetime - timedelta(hours=1)
        end_date = test_calendar_event.end_datetime + timedelta(hours=1)
        
        events_by_email = calendar_repository.get_multiple_users_calendar_events(
            test_db_session, [test_user.email], start_date, end_date
        )
        
        assert test_user.email in events_by_email
        assert len(events_by_email[test_user.email]) == 1
        assert events_by_email[test_user.email][0]['google_event_id'] == test_calendar_event.google_event_id
    
    def test_check_calendar_sync_needed_never_synced(self, test_db_session, test_user):
        """カレンダー同期必要チェック（未同期）テスト"""
        # calendar_last_syncedがNoneの場合
        test_user.calendar_last_synced = None
        test_db_session.commit()
        
        sync_needed = calendar_repository.check_calendar_sync_needed(test_db_session, test_user.id)
        
        assert sync_needed is True
    
    def test_check_calendar_sync_needed_recent_sync(self, test_db_session, test_user):
        """カレンダー同期必要チェック（最近同期済み）テスト"""
        # 1時間前に同期済み
        test_user.calendar_last_synced = datetime.now() - timedelta(hours=1)
        test_db_session.commit()
        
        sync_needed = calendar_repository.check_calendar_sync_needed(test_db_session, test_user.id, 24)
        
        assert sync_needed is False
    
    def test_check_calendar_sync_needed_old_sync(self, test_db_session, test_user):
        """カレンダー同期必要チェック（古い同期）テスト"""
        # 25時間前に同期済み
        test_user.calendar_last_synced = datetime.now() - timedelta(hours=25)
        test_db_session.commit()
        
        sync_needed = calendar_repository.check_calendar_sync_needed(test_db_session, test_user.id, 24)
        
        assert sync_needed is True 