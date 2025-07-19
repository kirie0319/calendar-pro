from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from datetime import datetime, timedelta
from typing import List, Dict

from app.infrastructure.models import CalendarEvent, User

class CalendarRepository:
    def sync_user_calendar_events(self, session: Session, user_id: int, events_data: list) -> int:
        """ユーザーのカレンダーイベントを同期（既存削除→新規追加）"""
        try:
            # 既存のイベントを削除
            session.execute(delete(CalendarEvent).where(CalendarEvent.user_id == user_id))
            
            # 新しいイベントを追加
            events_added = 0
            for event_data in events_data:
                calendar_event = CalendarEvent(
                    user_id=user_id,
                    google_event_id=event_data['google_event_id'],
                    start_datetime=event_data['start_datetime'],
                    end_datetime=event_data['end_datetime'],
                    title=event_data.get('title', '予定あり'),
                    is_all_day=event_data.get('is_all_day', False)
                )
                session.add(calendar_event)
                events_added += 1
            
            # ユーザーの最終同期時刻を更新
            user = session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
            if user:
                user.calendar_last_synced = datetime.now()
            
            session.commit()
            
            print(f"✅ ユーザー {user_id} のカレンダーを同期しました: {events_added}件のイベント")
            return events_added
            
        except Exception as e:
            session.rollback()
            print(f"❌ カレンダー同期エラー (ユーザー {user_id}): {e}")
            return 0
    
    def get_user_calendar_events(self, session: Session, user_id: int, start_date: datetime, end_date: datetime) -> List[Dict]:
        """指定期間のユーザーカレンダーイベントを取得"""
        result = session.execute(
            select(CalendarEvent).where(
                CalendarEvent.user_id == user_id,
                CalendarEvent.start_datetime >= start_date,
                CalendarEvent.start_datetime <= end_date
            ).order_by(CalendarEvent.start_datetime)
        )
        
        events = result.scalars().all()
        
        return [
            {
                'google_event_id': event.google_event_id,
                'start_datetime': event.start_datetime,
                'end_datetime': event.end_datetime,
                'title': event.title,
                'is_all_day': event.is_all_day
            }
            for event in events
        ]
    
    def get_user_calendar_events_for_period(self, session: Session, user_id: int, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """指定期間のユーザーカレンダーイベントを取得（オブジェクト形式）"""
        result = session.execute(
            select(CalendarEvent).where(
                CalendarEvent.user_id == user_id,
                CalendarEvent.start_datetime >= start_date,
                CalendarEvent.start_datetime <= end_date
            ).order_by(CalendarEvent.start_datetime)
        )
        
        return result.scalars().all()
    
    def get_multiple_users_calendar_events(self, session: Session, user_emails: List[str], start_date: datetime, end_date: datetime) -> Dict[str, List[Dict]]:
        """複数ユーザーのカレンダーイベントを一括取得"""
        result = session.execute(
            select(User, CalendarEvent).join(
                CalendarEvent, User.id == CalendarEvent.user_id
            ).where(
                User.email.in_(user_emails),
                CalendarEvent.start_datetime >= start_date,
                CalendarEvent.start_datetime <= end_date
            ).order_by(CalendarEvent.start_datetime)
        )
        
        events_by_email = {email: [] for email in user_emails}
        
        for user, event in result.fetchall():
            events_by_email[user.email].append({
                'google_event_id': event.google_event_id,
                'start_datetime': event.start_datetime,
                'end_datetime': event.end_datetime,
                'title': event.title,
                'is_all_day': event.is_all_day
            })
        
        return events_by_email
    
    def check_calendar_sync_needed(self, session: Session, user_id: int, hours_threshold: int = 24) -> bool:
        """カレンダー同期が必要かチェック（最終同期から指定時間経過で必要）"""
        user = session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        
        if not user or not user.calendar_last_synced:
            return True  # 未同期の場合は同期が必要
        
        time_diff = datetime.now() - user.calendar_last_synced
        return time_diff > timedelta(hours=hours_threshold)

# グローバルインスタンス
calendar_repository = CalendarRepository() 