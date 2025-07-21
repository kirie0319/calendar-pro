import pytest
from unittest.mock import patch, MagicMock, Mock
from fastapi import HTTPException
from datetime import datetime, timedelta
import pytz

from app.service.meeting_service import meeting_service
from app.core.entities import MeetingSlot

# タイムゾーン設定
JST = pytz.timezone('Asia/Tokyo')

@pytest.mark.unit
class TestMeetingService:
    """MeetingServiceのテスト"""
    
    def test_validate_search_parameters_success(self):
        """検索パラメータ検証成功テスト"""
        member_emails = ["user1@example.com", "user2@example.com"]
        start_date = "2024-01-15"
        end_date = "2024-01-16"
        start_time = "09:00"
        end_time = "17:00"
        duration_minutes = 60
        
        # 例外が発生しないことを確認
        result = meeting_service.validate_search_parameters(
            member_emails, start_date, end_date, start_time, end_time, duration_minutes
        )
        
        assert result is True
    
    def test_validate_search_parameters_no_members(self):
        """検索パラメータ検証（メンバーなし）テスト"""
        with pytest.raises(HTTPException) as exc_info:
            meeting_service.validate_search_parameters(
                [], "2024-01-15", "2024-01-16", "09:00", "17:00", 60
            )
        
        assert exc_info.value.status_code == 400
        assert "参加者を選択してください" in str(exc_info.value.detail)
    
    def test_validate_search_parameters_too_many_members(self):
        """検索パラメータ検証（メンバー数超過）テスト"""
        member_emails = [f"user{i}@example.com" for i in range(25)]  # 25名
        
        with pytest.raises(HTTPException) as exc_info:
            meeting_service.validate_search_parameters(
                member_emails, "2024-01-15", "2024-01-16", "09:00", "17:00", 60
            )
        
        assert exc_info.value.status_code == 400
        assert "参加者は20名以下にしてください" in str(exc_info.value.detail)
    
    def test_validate_search_parameters_invalid_date_format(self):
        """検索パラメータ検証（無効な日付形式）テスト"""
        member_emails = ["user1@example.com"]
        
        with pytest.raises(HTTPException) as exc_info:
            meeting_service.validate_search_parameters(
                member_emails, "2024/01/15", "2024-01-16", "09:00", "17:00", 60
            )
        
        assert exc_info.value.status_code == 400
        assert "日付形式が正しくありません" in str(exc_info.value.detail)
    
    def test_validate_search_parameters_end_before_start(self):
        """検索パラメータ検証（終了日が開始日より前）テスト"""
        member_emails = ["user1@example.com"]
        
        with pytest.raises(HTTPException) as exc_info:
            meeting_service.validate_search_parameters(
                member_emails, "2024-01-16", "2024-01-15", "09:00", "17:00", 60
            )
        
        assert exc_info.value.status_code == 400
        assert "開始日は終了日より前にしてください" in str(exc_info.value.detail)
    
    def test_validate_search_parameters_period_too_long(self):
        """検索パラメータ検証（期間が長すぎる）テスト"""
        member_emails = ["user1@example.com"]
        start_date = "2024-01-01"
        end_date = "2024-04-15"  # 3ヶ月以上
        
        with pytest.raises(HTTPException) as exc_info:
            meeting_service.validate_search_parameters(
                member_emails, start_date, end_date, "09:00", "17:00", 60
            )
        
        assert exc_info.value.status_code == 400
        assert "検索期間は3ヶ月以内にしてください" in str(exc_info.value.detail)
    
    def test_validate_search_parameters_invalid_time_format(self):
        """検索パラメータ検証（無効な時間形式）テスト"""
        member_emails = ["user1@example.com"]
        
        # "25:00" は明確に無効な時間形式
        with pytest.raises(HTTPException) as exc_info:
            meeting_service.validate_search_parameters(
                member_emails, "2024-01-15", "2024-01-16", "25:00", "17:00", 60
            )
        
        assert exc_info.value.status_code == 400
    
    def test_validate_search_parameters_time_range_invalid(self):
        """検索パラメータ検証（時間範囲が無効）テスト"""
        member_emails = ["user1@example.com"]
        
        with pytest.raises(HTTPException) as exc_info:
            meeting_service.validate_search_parameters(
                member_emails, "2024-01-15", "2024-01-16", "17:00", "09:00", 60
            )
        
        assert exc_info.value.status_code == 400
        assert "開始時間は終了時間より前にしてください" in str(exc_info.value.detail)
    
    def test_validate_search_parameters_duration_invalid(self):
        """検索パラメータ検証（無効な継続時間）テスト"""
        member_emails = ["user1@example.com"]
        
        with pytest.raises(HTTPException) as exc_info:
            meeting_service.validate_search_parameters(
                member_emails, "2024-01-15", "2024-01-16", "09:00", "17:00", 10
            )
        
        assert exc_info.value.status_code == 400
        assert "ミーティング時間は15分〜8時間の範囲で指定してください" in str(exc_info.value.detail)
    
    def test_validate_search_parameters_duration_too_long_for_timeframe(self):
        """検索パラメータ検証（時間枠に対して継続時間が長すぎる）テスト"""
        member_emails = ["user1@example.com"]
        
        with pytest.raises(HTTPException) as exc_info:
            meeting_service.validate_search_parameters(
                member_emails, "2024-01-15", "2024-01-16", "09:00", "10:00", 120  # 2時間のミーティングを1時間枠で
            )
        
        assert exc_info.value.status_code == 400
        assert "指定時間帯がミーティング時間より短すぎます" in str(exc_info.value.detail)
    
    @patch('meeting_scheduler.meeting_scheduler.find_available_times')
    def test_find_available_meeting_times_success(self, mock_find_times, test_db_session):
        """ミーティング時間検索成功テスト"""
        # モックの戻り値を設定
        mock_find_times.return_value = {
            'available_slots': [
                {
                    'date': '2024-01-15',
                    'start_time': '10:00',
                    'end_time': '11:00',
                    'start_datetime': '2024-01-15T10:00:00+09:00',
                    'end_datetime': '2024-01-15T11:00:00+09:00',
                    'duration_minutes': 60
                }
            ],
            'member_schedules': {
                'user1@example.com': [],
                'user2@example.com': []
            },
            'search_period': {
                'start': '2024-01-15',
                'end': '2024-01-16'
            }
        }
        
        result = meeting_service.find_available_meeting_times(
            test_db_session,
            ["user1@example.com", "user2@example.com"],
            "2024-01-15",
            "2024-01-16",
            "09:00",
            "17:00",
            60
        )
        
        assert 'available_slots' in result
        assert 'member_schedules' in result
        assert 'search_params' in result
        assert 'total_slots_found' in result
        assert len(result['available_slots']) == 1
        assert result['total_slots_found'] == 1
    
    @patch('meeting_scheduler.meeting_scheduler.find_available_times')
    def test_find_available_meeting_times_scheduler_error(self, mock_find_times, test_db_session):
        """ミーティング時間検索（スケジューラーエラー）テスト"""
        # スケジューラーでエラーを発生させる
        mock_find_times.side_effect = Exception("Scheduler error")
        
        with pytest.raises(HTTPException) as exc_info:
            meeting_service.find_available_meeting_times(
                test_db_session,
                ["user1@example.com"],
                "2024-01-15",
                "2024-01-16",
                "09:00",
                "17:00",
                60
            )
        
        assert exc_info.value.status_code == 500
        assert "ミーティング検索中にエラーが発生しました" in str(exc_info.value.detail)
    
    def test_get_member_schedule_summary_no_conflicts(self):
        """メンバー予定サマリー取得（競合なし）テスト"""
        # naive datetimeを使用（実装に合わせて）
        member_schedules = {
            'user1@example.com': [
                {
                    'start_datetime': '2024-01-15 08:00:00',
                    'end_datetime': '2024-01-15 09:00:00',
                    'title': 'Early Meeting',
                    'start_time': '08:00',
                    'end_time': '09:00'
                }
            ]
        }
        
        summary = meeting_service.get_member_schedule_summary(
            member_schedules,
            "2024-01-15",
            "10:00",
            60
        )
        
        assert 'user1@example.com' in summary
        assert summary['user1@example.com']['has_conflict'] is False
        assert summary['user1@example.com']['status'] == 'available'
        assert len(summary['user1@example.com']['conflicting_events']) == 0
    
    def test_get_member_schedule_summary_with_conflicts(self):
        """メンバー予定サマリー取得（競合あり）テスト"""
        # naive datetimeを使用して競合をテスト
        member_schedules = {
            'user1@example.com': [
                {
                    'start_datetime': '2024-01-15 10:30:00',
                    'end_datetime': '2024-01-15 11:30:00',
                    'title': 'Conflicting Meeting',
                    'start_time': '10:30',
                    'end_time': '11:30'
                }
            ]
        }
        
        summary = meeting_service.get_member_schedule_summary(
            member_schedules,
            "2024-01-15",
            "10:00",
            60
        )
        
        assert 'user1@example.com' in summary
        assert summary['user1@example.com']['has_conflict'] is True
        assert summary['user1@example.com']['status'] == 'busy'
        assert len(summary['user1@example.com']['conflicting_events']) == 1
    
    def test_format_meeting_slots(self):
        """ミーティングスロットフォーマットテスト"""
        available_slots = [
            {
                'date': '2024-01-15',
                'start_time': '10:00',
                'end_time': '11:00',
                'start_datetime': '2024-01-15T10:00:00+09:00',
                'end_datetime': '2024-01-15T11:00:00+09:00',
                'duration_minutes': 60,
                'available_members': ['user1@example.com'],
                'busy_members': []
            }
        ]
        
        meeting_slots = meeting_service.format_meeting_slots(available_slots)
        
        assert len(meeting_slots) == 1
        assert isinstance(meeting_slots[0], MeetingSlot)
        assert meeting_slots[0].date == '2024-01-15'
        assert meeting_slots[0].start_time == '10:00'
        assert meeting_slots[0].duration_minutes == 60
    
    def test_format_meeting_slots_invalid_data(self):
        """ミーティングスロットフォーマット（無効データ）テスト"""
        available_slots = [
            {
                'date': '2024-01-15',
                'start_time': '10:00',
                # end_timeが欠落
                'start_datetime': '2024-01-15T10:00:00+09:00',
                'end_datetime': '2024-01-15T11:00:00+09:00'
            }
        ]
        
        meeting_slots = meeting_service.format_meeting_slots(available_slots)
        
        assert len(meeting_slots) == 0  # 無効なデータはスキップされる

@pytest.mark.unit
class TestMeetingServiceParameterValidation:
    """MeetingServiceパラメータ検証の詳細テスト"""
    
    def test_validate_edge_case_minimum_duration(self):
        """最小継続時間のエッジケーステスト"""
        member_emails = ["user1@example.com"]
        
        # 15分（最小値）は成功
        result = meeting_service.validate_search_parameters(
            member_emails, "2024-01-15", "2024-01-16", "09:00", "17:00", 15
        )
        assert result is True
        
        # 14分は失敗
        with pytest.raises(HTTPException):
            meeting_service.validate_search_parameters(
                member_emails, "2024-01-15", "2024-01-16", "09:00", "17:00", 14
            )
    
    def test_validate_edge_case_maximum_duration(self):
        """最大継続時間のエッジケーステスト"""
        member_emails = ["user1@example.com"]
        
        # 480分（8時間、最大値）は成功
        result = meeting_service.validate_search_parameters(
            member_emails, "2024-01-15", "2024-01-16", "09:00", "17:00", 480
        )
        assert result is True
        
        # 481分は失敗
        with pytest.raises(HTTPException):
            meeting_service.validate_search_parameters(
                member_emails, "2024-01-15", "2024-01-16", "09:00", "17:00", 481
            )
    
    def test_validate_edge_case_maximum_members(self):
        """最大メンバー数のエッジケーステスト"""
        # 20名（最大値）は成功
        member_emails = [f"user{i}@example.com" for i in range(20)]
        result = meeting_service.validate_search_parameters(
            member_emails, "2024-01-15", "2024-01-16", "09:00", "17:00", 60
        )
        assert result is True
        
        # 21名は失敗
        member_emails = [f"user{i}@example.com" for i in range(21)]
        with pytest.raises(HTTPException):
            meeting_service.validate_search_parameters(
                member_emails, "2024-01-15", "2024-01-16", "09:00", "17:00", 60
            )
    
    def test_validate_edge_case_time_boundaries(self):
        """時間境界値のエッジケーステスト"""
        member_emails = ["user1@example.com"]
        
        # 00:00-23:59は成功
        result = meeting_service.validate_search_parameters(
            member_emails, "2024-01-15", "2024-01-16", "00:00", "23:59", 60
        )
        assert result is True
        
        # 無効な時間（24:00）は失敗
        with pytest.raises(HTTPException):
            meeting_service.validate_search_parameters(
                member_emails, "2024-01-15", "2024-01-16", "24:00", "23:59", 60
            ) 

    def test_create_meeting_event_success(self):
        """ミーティングイベント作成成功テスト"""
        # モックの認証情報
        mock_credentials = {
            'token': 'mock_token',
            'refresh_token': 'mock_refresh_token',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'mock_client_id',
            'client_secret': 'mock_client_secret',
            'scopes': ['https://www.googleapis.com/auth/calendar']
        }
        
        # テスト用の時刻
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        attendees = ['test1@example.com', 'test2@example.com']
        
        # Google Calendar APIのモック
        mock_event_response = {
            'id': 'test_event_123',
            'htmlLink': 'https://calendar.google.com/event?eid=test_event_123',
            'summary': 'テストミーティング'
        }
        
        with patch('app.service.meeting_service.build') as mock_build:
            mock_service = Mock()
            mock_events = Mock()
            mock_insert = Mock()
            
            # モックチェーンを設定
            mock_build.return_value = mock_service
            mock_service.events.return_value = mock_events
            mock_events.insert.return_value = mock_insert
            mock_insert.execute.return_value = mock_event_response
            
            # ミーティング作成を実行
            result = meeting_service.create_meeting_event(
                credentials=mock_credentials,
                title='テストミーティング',
                start_datetime=start_time,
                end_datetime=end_time,
                attendee_emails=attendees,
                description='テスト説明'
            )
            
            # 結果検証
            assert result['event_id'] == 'test_event_123'
            assert result['status'] == 'created'
            assert result['title'] == 'テストミーティング'
            assert result['attendees'] == attendees
            
            # API呼び出し検証
            mock_events.insert.assert_called_once()
            call_args = mock_events.insert.call_args
            assert call_args[1]['calendarId'] == 'primary'
            assert call_args[1]['sendNotifications'] == True
            
            # イベントボディ検証
            event_body = call_args[1]['body']
            assert event_body['summary'] == 'テストミーティング'
            assert event_body['description'] == 'テスト説明'
            assert len(event_body['attendees']) == 2
            assert event_body['attendees'][0]['email'] == 'test1@example.com'

    def test_create_meeting_event_api_error(self):
        """Google Calendar API エラーテスト"""
        mock_credentials = {
            'token': 'mock_token',
            'refresh_token': 'mock_refresh_token',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'mock_client_id',
            'client_secret': 'mock_client_secret',
            'scopes': ['https://www.googleapis.com/auth/calendar']
        }
        
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        with patch('app.service.meeting_service.build') as mock_build:
            # Google Calendar APIエラーをシミュレート
            mock_build.side_effect = Exception("API access denied")
            
            # HTTPExceptionが発生することを確認
            with pytest.raises(HTTPException) as excinfo:
                meeting_service.create_meeting_event(
                    credentials=mock_credentials,
                    title='テストミーティング',
                    start_datetime=start_time,
                    end_datetime=end_time,
                    attendee_emails=['test@example.com']
                )
            
            assert excinfo.value.status_code == 500
            assert "ミーティングの作成に失敗しました" in str(excinfo.value.detail) 