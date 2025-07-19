import pytest
from unittest.mock import patch
from fastapi import HTTPException

from app.service.group_service import group_service
from app.core.entities import GroupRole

@pytest.mark.unit
class TestGroupService:
    """GroupServiceのテスト"""
    
    def test_create_group_success(self, test_db_session, test_user):
        """グループ作成成功テスト"""
        group = group_service.create_group(
            test_db_session,
            "Test Group",
            "Test Description",
            test_user.id
        )
        
        assert group.name == "Test Group"
        assert group.description == "Test Description"
        assert group.created_by == test_user.id
        assert group.is_active is True
        assert len(group.invite_code) == 12
    
    def test_create_group_repository_error(self, test_db_session, test_user):
        """グループ作成時のリポジトリエラーテスト"""
        with patch('app.service.group_service.group_repository.create_group') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            with pytest.raises(HTTPException) as exc_info:
                group_service.create_group(
                    test_db_session,
                    "Test Group",
                    "Test Description",
                    test_user.id
                )
            
            assert exc_info.value.status_code == 500
            assert "グループの作成に失敗しました" in str(exc_info.value.detail)
    
    def test_get_group_by_id_found(self, test_db_session, test_group):
        """グループID検索成功テスト"""
        group = group_service.get_group_by_id(test_db_session, test_group.id)
        
        assert group is not None
        assert group.id == test_group.id
        assert group.name == test_group.name
    
    def test_get_group_by_id_not_found(self, test_db_session):
        """グループID検索失敗テスト"""
        group = group_service.get_group_by_id(test_db_session, 99999)
        
        assert group is None
    
    def test_get_group_by_invite_code_found(self, test_db_session, test_group):
        """招待コード検索成功テスト"""
        group = group_service.get_group_by_invite_code(test_db_session, test_group.invite_code)
        
        assert group is not None
        assert group.id == test_group.id
        assert group.invite_code == test_group.invite_code
    
    def test_get_user_groups(self, test_db_session, test_user, test_group):
        """ユーザーグループ一覧取得テスト"""
        groups = group_service.get_user_groups(test_db_session, test_user.id)
        
        assert len(groups) == 1
        assert groups[0]['id'] == test_group.id
        assert groups[0]['name'] == test_group.name
        assert groups[0]['role'] == "admin"
    
    def test_get_user_groups_repository_error(self, test_db_session, test_user):
        """ユーザーグループ取得エラーテスト"""
        with patch('app.service.group_service.group_repository.get_user_groups') as mock_get:
            mock_get.side_effect = Exception("Database error")
            
            groups = group_service.get_user_groups(test_db_session, test_user.id)
            
            assert groups == []  # エラー時は空リストを返す
    
    def test_get_group_members(self, test_db_session, test_user, test_group):
        """グループメンバー一覧取得テスト"""
        members = group_service.get_group_members(test_db_session, test_group.id)
        
        assert len(members) == 1
        assert members[0]['name'] == test_user.name
        assert members[0]['email'] == test_user.email
        assert members[0]['role'] == "admin"
    
    def test_get_user_membership_found(self, test_db_session, test_user, test_group):
        """ユーザーメンバーシップ取得成功テスト"""
        membership = group_service.get_user_membership(test_db_session, test_group.id, test_user.id)
        
        assert membership is not None
        assert membership.group_id == test_group.id
        assert membership.user_id == test_user.id
        assert membership.role == GroupRole.ADMIN
        assert membership.is_admin()
    
    def test_get_user_membership_not_found(self, test_db_session, test_group):
        """ユーザーメンバーシップ取得失敗テスト"""
        membership = group_service.get_user_membership(test_db_session, test_group.id, 99999)
        
        assert membership is None
    
    def test_join_group_success(self, test_db_session, test_group):
        """グループ参加成功テスト"""
        # 新しいユーザーID（実際には存在しないが、リポジトリレベルでは成功と仮定）
        new_user_id = 999
        
        with patch('app.service.group_service.group_repository.add_user_to_group') as mock_add:
            mock_add.return_value = True
            
            success = group_service.join_group(test_db_session, test_group.id, new_user_id, "member")
            
            assert success is True
            mock_add.assert_called_once_with(test_db_session, test_group.id, new_user_id, "member")
    
    def test_join_group_already_member(self, test_db_session, test_user, test_group):
        """グループ参加（既存メンバー）テスト"""
        success = group_service.join_group(test_db_session, test_group.id, test_user.id, "member")
        
        assert success is False  # 既にメンバーなので失敗
    
    def test_join_group_repository_error(self, test_db_session, test_group):
        """グループ参加時のリポジトリエラーテスト"""
        new_user_id = 999
        
        with patch('app.service.group_service.group_repository.add_user_to_group') as mock_add:
            mock_add.side_effect = Exception("Database error")
            
            success = group_service.join_group(test_db_session, test_group.id, new_user_id, "member")
            
            assert success is False
    
    def test_join_group_by_invite_code_success(self, test_db_session, test_group):
        """招待コードでのグループ参加成功テスト"""
        new_user_id = 999
        
        with patch('app.service.group_service.group_repository.add_user_to_group') as mock_add:
            mock_add.return_value = True
            
            group = group_service.join_group_by_invite_code(
                test_db_session, test_group.invite_code, new_user_id
            )
            
            assert group is not None
            assert group.id == test_group.id
    
    def test_join_group_by_invite_code_invalid_code(self, test_db_session):
        """無効な招待コードでのグループ参加テスト"""
        with pytest.raises(HTTPException) as exc_info:
            group_service.join_group_by_invite_code(
                test_db_session, "INVALID", 999
            )
        
        assert exc_info.value.status_code == 404
        assert "無効な招待コードです" in str(exc_info.value.detail)
    
    def test_check_user_access_has_access(self, test_db_session, test_user, test_group):
        """ユーザーアクセス権限チェック（権限あり）テスト"""
        has_access = group_service.check_user_access(test_db_session, test_group.id, test_user.id)
        
        assert has_access is True
    
    def test_check_user_access_no_access(self, test_db_session, test_group):
        """ユーザーアクセス権限チェック（権限なし）テスト"""
        has_access = group_service.check_user_access(test_db_session, test_group.id, 99999)
        
        assert has_access is False
    
    def test_is_group_admin_true(self, test_db_session, test_user, test_group):
        """グループ管理者チェック（管理者）テスト"""
        is_admin = group_service.is_group_admin(test_db_session, test_group.id, test_user.id)
        
        assert is_admin is True
    
    def test_is_group_admin_false(self, test_db_session, test_group):
        """グループ管理者チェック（非管理者）テスト"""
        is_admin = group_service.is_group_admin(test_db_session, test_group.id, 99999)
        
        assert is_admin is False
    
    def test_get_group_with_access_check_success(self, test_db_session, test_user, test_group):
        """アクセス権限チェック付きグループ取得成功テスト"""
        group = group_service.get_group_with_access_check(
            test_db_session, test_group.id, test_user.id
        )
        
        assert group is not None
        assert group.id == test_group.id
    
    def test_get_group_with_access_check_group_not_found(self, test_db_session, test_user):
        """アクセス権限チェック付きグループ取得（グループ不存在）テスト"""
        with pytest.raises(HTTPException) as exc_info:
            group_service.get_group_with_access_check(
                test_db_session, 99999, test_user.id
            )
        
        assert exc_info.value.status_code == 404
        assert "グループが見つかりません" in str(exc_info.value.detail)
    
    def test_get_group_with_access_check_no_access(self, test_db_session, test_group):
        """アクセス権限チェック付きグループ取得（権限なし）テスト"""
        with pytest.raises(HTTPException) as exc_info:
            group_service.get_group_with_access_check(
                test_db_session, test_group.id, 99999
            )
        
        assert exc_info.value.status_code == 403
        assert "このグループのメンバーではありません" in str(exc_info.value.detail)
    
    def test_get_group_detail_for_user_success(self, test_db_session, test_user, test_group):
        """ユーザー向けグループ詳細取得成功テスト"""
        detail = group_service.get_group_detail_for_user(
            test_db_session, test_group.id, test_user.id
        )
        
        assert 'group' in detail
        assert 'members' in detail
        assert 'membership' in detail
        assert 'invite_url' in detail
        assert 'member_count' in detail
        
        assert detail['group'].id == test_group.id
        assert detail['member_count'] == 1
        assert test_group.invite_code in detail['invite_url']
    
    def test_get_group_detail_for_user_no_access(self, test_db_session, test_group):
        """ユーザー向けグループ詳細取得（権限なし）テスト"""
        with pytest.raises(HTTPException) as exc_info:
            group_service.get_group_detail_for_user(
                test_db_session, test_group.id, 99999
            )
        
        assert exc_info.value.status_code == 403 