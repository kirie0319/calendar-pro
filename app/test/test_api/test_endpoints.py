import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.test.conftest import set_session_data

@pytest.mark.api
class TestAuthEndpoints:
    """認証エンドポイントのテスト"""
    
    def test_index_page_not_authenticated(self, test_client):
        """未認証でのインデックスページテスト"""
        response = test_client.get("/")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_index_page_authenticated_redirect(self, test_client, test_user):
        """認証済みでのインデックスページテスト（リダイレクト）"""
        # 依存性オーバーライドで認証を設定
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        
        setup_authenticated_client(test_client, test_user)
        
        try:
            response = test_client.get("/", follow_redirects=False)
            
            assert response.status_code == 302
            assert "/groups" in response.headers["location"]
        finally:
            clear_authenticated_client(test_client)
    
    @patch('app.service.auth_service.auth_service.get_authorization_url')
    def test_login_endpoint(self, mock_get_auth_url, test_client):
        """ログインエンドポイントテスト"""
        mock_get_auth_url.return_value = ("https://accounts.google.com/oauth2/auth?...", "test_state")
        
        response = test_client.get("/login", follow_redirects=False)
        
        assert response.status_code == 302
        assert "accounts.google.com" in response.headers["location"]
    
    def test_logout_endpoint(self, test_client, test_user):
        """ログアウトエンドポイントテスト"""
        # セッションに認証情報を設定
        session_data = {
            'user_id': test_user.id,
            'user_email': test_user.email
        }
        set_session_data(test_client, session_data)
        
        response = test_client.get("/logout", follow_redirects=False)
        
        assert response.status_code == 302
        assert response.headers["location"] == "/"
    
    def test_status_endpoint(self, test_client):
        """ステータスエンドポイントテスト"""
        response = test_client.get("/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["framework"] == "FastAPI"
        assert data["architecture"] == "Clean Architecture"
        assert "features" in data
    
    def test_debug_info_endpoint(self, test_client):
        """デバッグ情報エンドポイントテスト"""
        response = test_client.get("/debug/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "process_info" in data
        assert "session_info" in data
        assert "concurrent_support" in data
        assert "architecture" in data

@pytest.mark.api
class TestGroupEndpoints:
    """グループエンドポイントのテスト"""
    
    def test_groups_list_unauthorized(self, test_client):
        """未認証でのグループ一覧アクセステスト"""
        response = test_client.get("/groups/")
        
        assert response.status_code == 401
    
    def test_groups_list_authorized(self, test_client, test_user, test_group):
        """認証済みでのグループ一覧テスト"""
        # 依存性オーバーライドで認証を設定
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        
        setup_authenticated_client(test_client, test_user)
        
        try:
            response = test_client.get("/groups/")
            
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
        finally:
            clear_authenticated_client(test_client)
    
    def test_group_create_form_unauthorized(self, test_client):
        """未認証でのグループ作成フォームアクセステスト"""
        response = test_client.get("/groups/create")
        
        assert response.status_code == 401
    
    def test_group_create_form_authorized(self, test_client, test_user):
        """認証済みでのグループ作成フォームテスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        
        setup_authenticated_client(test_client, test_user)
        
        try:
            response = test_client.get("/groups/create")
            
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
        finally:
            clear_authenticated_client(test_client)
    
    def test_group_create_post_success(self, test_client, test_user):
        """グループ作成POST成功テスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        from unittest.mock import patch
        from app.core.entities import Group
        
        setup_authenticated_client(test_client, test_user)
        
        try:
            # グループサービスをモック
            mock_group = Group(id=1, name="New Test Group", description="New test description")
            
            with patch('app.service.group_service.group_service.create_group') as mock_create:
                mock_create.return_value = mock_group
                
                form_data = {
                    "name": "New Test Group",
                    "description": "New test description"
                }
                
                response = test_client.post("/groups/create", data=form_data, follow_redirects=False)
                
                assert response.status_code == 302
                assert "/groups/" in response.headers["location"]
        finally:
            clear_authenticated_client(test_client)
    
    def test_group_create_post_validation_error(self, test_client, test_user):
        """グループ作成POST検証エラーテスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        
        setup_authenticated_client(test_client, test_user)
        
        try:
            form_data = {
                "name": "",  # 空の名前
                "description": "Description"
            }
            
            response = test_client.post("/groups/create", data=form_data)
            
            # FastAPIでは422 Unprocessable Entityが返される
            assert response.status_code == 422
        finally:
            clear_authenticated_client(test_client)
    
    def test_group_detail_unauthorized(self, test_client, test_group):
        """未認証でのグループ詳細アクセステスト"""
        response = test_client.get(f"/groups/{test_group.id}")
        
        assert response.status_code == 401
    
    def test_group_detail_authorized_member(self, test_client, test_user, test_group):
        """認証済みメンバーでのグループ詳細テスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        
        setup_authenticated_client(test_client, test_user)
        
        try:
            response = test_client.get(f"/groups/{test_group.id}")
            
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
        finally:
            clear_authenticated_client(test_client)
    
    def test_group_detail_unauthorized_non_member(self, test_client, test_group):
        """非メンバーでのグループ詳細アクセステスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        from app.core.entities import User
        
        # 別のユーザーで認証（非メンバー）
        other_user = User(id=99999, email="other@example.com", name="Other User")
        setup_authenticated_client(test_client, other_user)
        
        try:
            response = test_client.get(f"/groups/{test_group.id}", follow_redirects=False)
            
            # アクセス権限なしの場合はリダイレクト
            assert response.status_code == 302
            assert "/groups" in response.headers["location"]
        finally:
            clear_authenticated_client(test_client)
    
    def test_group_join_by_invite_code_success(self, test_client, test_user, test_group):
        """招待コードでのグループ参加成功テスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        from app.core.entities import User
        
        # 新しいユーザーで認証
        new_user = User(id=99999, email="newuser@example.com", name="New User")
        setup_authenticated_client(test_client, new_user)
        
        try:
            # モックで成功を設定
            with patch('app.service.group_service.group_service.join_group_by_invite_code') as mock_join:
                mock_join.return_value = test_group
                
                response = test_client.get(f"/groups/join/{test_group.invite_code}", follow_redirects=False)
                
                assert response.status_code == 302
                assert f"/groups/{test_group.id}" in response.headers["location"]
        finally:
            clear_authenticated_client(test_client)
    
    def test_group_join_by_invite_code_invalid(self, test_client, test_user):
        """無効な招待コードでのグループ参加テスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        
        setup_authenticated_client(test_client, test_user)
        
        try:
            response = test_client.get("/groups/join/INVALID", follow_redirects=False)
            
            # 無効な招待コードの場合は404が返される
            assert response.status_code == 404
        finally:
            clear_authenticated_client(test_client)
    
    def test_meeting_scheduler_page_unauthorized(self, test_client, test_group):
        """未認証でのミーティングスケジューラーアクセステスト"""
        response = test_client.get(f"/groups/{test_group.id}/schedule")
        
        assert response.status_code == 401
    
    def test_meeting_scheduler_page_authorized(self, test_client, test_user, test_group):
        """認証済みでのミーティングスケジューラーテスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        
        setup_authenticated_client(test_client, test_user)
        
        try:
            response = test_client.get(f"/groups/{test_group.id}/schedule")
            
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
        finally:
            clear_authenticated_client(test_client)

@pytest.mark.api
class TestMeetingEndpoints:
    """ミーティングエンドポイントのテスト"""
    
    def test_meeting_search_api_unauthorized(self, test_client, test_group):
        """未認証でのミーティング検索APIテスト"""
        form_data = {
            "group_id": test_group.id,
            "selected_members": ["user1@example.com"],
            "start_date": "2024-01-15",
            "end_date": "2024-01-16",
            "start_time": "09:00",
            "end_time": "17:00",
            "duration": 60
        }
        
        response = test_client.post("/api/meeting/search", data=form_data)
        
        assert response.status_code == 401
    
    @patch('app.service.meeting_service.meeting_service.find_available_meeting_times')
    def test_meeting_search_api_success(self, mock_find_times, test_client, test_user, test_group):
        """ミーティング検索API成功テスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        
        setup_authenticated_client(test_client, test_user)
        
        try:
            # モックレスポンス設定
            mock_find_times.return_value = {
                'available_slots': [
                    {
                        'date': '2024-01-15',
                        'start_time': '10:00',
                        'end_time': '11:00',
                        'duration_minutes': 60
                    }
                ],
                'member_schedules': {},
                'search_params': {},
                'total_slots_found': 1
            }
            
            form_data = {
                "group_id": test_group.id,
                "selected_members": [test_user.email],
                "start_date": "2024-01-15",
                "end_date": "2024-01-16",
                "start_time": "09:00",
                "end_time": "17:00",
                "duration": 60
            }
            
            response = test_client.post("/api/meeting/search", data=form_data)
            
            assert response.status_code == 200
            data = response.json()
            assert 'available_slots' in data
            assert 'total_slots_found' in data
            assert data['total_slots_found'] == 1
        finally:
            clear_authenticated_client(test_client)
    
    def test_meeting_search_api_validation_error(self, test_client, test_user, test_group):
        """ミーティング検索API検証エラーテスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        
        setup_authenticated_client(test_client, test_user)
        
        try:
            form_data = {
                "group_id": test_group.id,
                "selected_members": [],  # 空のメンバーリスト
                "start_date": "2024-01-15",
                "end_date": "2024-01-16",
                "start_time": "09:00",
                "end_time": "17:00",
                "duration": 60
            }
            
            response = test_client.post("/api/meeting/search", data=form_data)
            
            # FastAPIでは422 Unprocessable Entityが返される
            assert response.status_code == 422
        finally:
            clear_authenticated_client(test_client)
    
    def test_calendar_page_unauthorized(self, test_client):
        """未認証でのカレンダーページアクセステスト"""
        response = test_client.get("/calendar")
        
        assert response.status_code == 401
    
    def test_calendar_page_authorized(self, test_client, test_user):
        """認証済みでのカレンダーページテスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        from unittest.mock import patch, MagicMock
        from starlette.responses import HTMLResponse
        
        setup_authenticated_client(test_client, test_user)
        
        try:
            # テンプレートレスポンスをモック
            mock_response = HTMLResponse(content="<html><body>Calendar Page</body></html>")
            
            with patch('fastapi.templating.Jinja2Templates.TemplateResponse', return_value=mock_response):
                response = test_client.get("/calendar")
                
                assert response.status_code == 200
                assert "text/html" in response.headers["content-type"]
        finally:
            clear_authenticated_client(test_client)
    
    def test_calendar_events_api_unauthorized(self, test_client):
        """未認証でのカレンダーイベントAPIテスト"""
        response = test_client.get("/api/calendar/events?start=2024-01-01T00:00:00Z&end=2024-01-31T23:59:59Z")
        
        assert response.status_code == 401
    
    def test_calendar_events_api_authorized(self, test_client, test_user, test_calendar_event):
        """認証済みでのカレンダーイベントAPIテスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        
        setup_authenticated_client(test_client, test_user)
        
        try:
            response = test_client.get("/api/calendar/events?start=2024-01-01T00:00:00Z&end=2024-12-31T23:59:59Z")
            
            assert response.status_code == 200
            events = response.json()
            assert isinstance(events, list)
        finally:
            clear_authenticated_client(test_client)
    
    def test_member_schedule_summary_api_unauthorized(self, test_client):
        """未認証でのメンバー予定サマリーAPIテスト"""
        response = test_client.get("/api/member/schedule/user@example.com?date=2024-01-15&start_time=10:00&duration=60")
        
        assert response.status_code == 401
    
    def test_member_schedule_summary_api_authorized(self, test_client, test_user):
        """認証済みでのメンバー予定サマリーAPIテスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        
        setup_authenticated_client(test_client, test_user)
        
        try:
            response = test_client.get(f"/api/member/schedule/{test_user.email}?date=2024-01-15&start_time=10:00&duration=60")
            
            assert response.status_code == 200
            data = response.json()
            assert 'events' in data
            assert 'status' in data
        finally:
            clear_authenticated_client(test_client)

@pytest.mark.integration
class TestEndpointIntegration:
    """エンドポイント統合テスト"""
    
    def test_full_group_workflow(self, test_client, test_user):
        """グループ作成から参加までの完全ワークフローテスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        from app.core.entities import Group
        
        # 認証設定
        setup_authenticated_client(test_client, test_user)
        
        try:
            # 1. グループ作成（モック使用）
            mock_group = Group(id=1, name="Integration Test Group", description="Integration test description")
            
            with patch('app.service.group_service.group_service.create_group') as mock_create:
                mock_create.return_value = mock_group
                
                form_data = {
                    "name": "Integration Test Group",
                    "description": "Integration test description"
                }
                
                response = test_client.post("/groups/create", data=form_data, follow_redirects=False)
                assert response.status_code == 302
                
                # リダイレクト先からグループIDを取得
                location = response.headers["location"]
                group_id = location.split("/")[-1]
                
                # 2. グループ詳細ページにアクセス（モック使用）
                with patch('app.service.group_service.group_service.get_group_detail_for_user') as mock_detail:
                    mock_detail.return_value = {
                        'group': mock_group,
                        'members': [],
                        'membership': None,
                        'invite_url': 'http://test/groups/join/ABC123',
                        'member_count': 0
                    }
                    
                    response = test_client.get(f"/groups/{group_id}")
                    assert response.status_code == 200
                
                # 3. ミーティングスケジューラーページにアクセス（モック使用）
                with patch('app.service.group_service.group_service.get_group_with_access_check') as mock_access:
                    mock_access.return_value = mock_group
                    with patch('app.service.group_service.group_service.get_group_members') as mock_members:
                        mock_members.return_value = []
                        
                        response = test_client.get(f"/groups/{group_id}/schedule")
                        assert response.status_code == 200
        finally:
            clear_authenticated_client(test_client)
    
    def test_error_handling_chain(self, test_client, test_user):
        """エラーハンドリングの連鎖テスト"""
        from app.test.conftest import setup_authenticated_client, clear_authenticated_client
        
        setup_authenticated_client(test_client, test_user)
        
        try:
            # 存在しないグループへのアクセス
            response = test_client.get("/groups/99999", follow_redirects=False)
            assert response.status_code == 302
            assert "/groups" in response.headers["location"]
            
            # 無効な招待コードでの参加試行
            response = test_client.get("/groups/join/INVALID", follow_redirects=False)
            assert response.status_code == 404
        finally:
            clear_authenticated_client(test_client) 