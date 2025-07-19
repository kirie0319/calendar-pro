from typing import List, Dict, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, time
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import pytz

from app.core.entities import MeetingSlot
from app.infrastructure.repositories.calendar_repository import calendar_repository

class MeetingService:
    def __init__(self):
        self.timezone = pytz.timezone('Asia/Tokyo')
    
    def find_available_times(
        self,
        db: Session,
        member_emails: List[str],
        start_date: str,
        end_date: str,
        start_time: str,
        end_time: str,
        duration_minutes: int,
        member_credentials: Dict[str, dict] = None
    ) -> Dict:
        """
        指定されたメンバーの空き時間を検索
        
        Args:
            db: データベースセッション
            member_emails: 参加者のメールアドレスリスト
            member_credentials: メンバーのGoogle認証情報
            start_date: 検索開始日 (YYYY-MM-DD)
            end_date: 検索終了日 (YYYY-MM-DD)
            start_time: 希望開始時間 (HH:MM)
            end_time: 希望終了時間 (HH:MM)
            duration_minutes: ミーティング時間（分）
        
        Returns:
            空き時間スロットと各メンバーの予定情報を含む辞書
        """
        
        print(f"🔍 空き時間検索開始:")
        print(f"   参加者: {len(member_emails)}名")
        print(f"   期間: {start_date} 〜 {end_date}")
        print(f"   時間帯: {start_time} 〜 {end_time}")
        print(f"   時間: {duration_minutes}分")
        
        try:
            # データベースから各メンバーの予定を取得
            all_busy_times = self._get_member_busy_times_from_db(
                member_emails,
                start_date,
                end_date,
                db
            )
            
            # 空き時間を計算
            available_slots = self._calculate_available_slots(
                all_busy_times,
                start_date,
                end_date,
                start_time,
                end_time,
                duration_minutes
            )
            
            print(f"✅ 検索完了: {len(available_slots)}件の空き時間を発見")
            
            # メンバーの予定情報を整理
            member_schedules = {}
            for email, busy_times in all_busy_times.items():
                member_schedules[email] = [
                    {
                        'start_datetime': busy['start'].isoformat(),
                        'end_datetime': busy['end'].isoformat(),
                        'start_time': busy['start'].strftime('%H:%M'),
                        'end_time': busy['end'].strftime('%H:%M'),
                        'date': busy['start'].strftime('%Y-%m-%d'),
                        'title': busy['title']
                    }
                    for busy in busy_times
                ]
            
            return {
                'available_slots': available_slots,
                'member_schedules': member_schedules,
                'search_period': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'start_time': start_time,
                    'end_time': end_time
                },
                'total_slots_found': len(available_slots)
            }
            
        except Exception as e:
            print(f"❌ 空き時間検索エラー: {e}")
            raise HTTPException(status_code=500, detail=f"ミーティング検索中にエラーが発生しました: {str(e)}")
    
    def _get_member_busy_times_from_db(
        self,
        member_emails: List[str],
        start_date: str,
        end_date: str,
        db_session: Session
    ) -> Dict[str, List[Dict]]:
        """
        データベースから保存済みのメンバー予定を取得
        """
        try:
            # 日付文字列をdatetimeオブジェクトに変換
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=self.timezone)
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=self.timezone) + timedelta(days=1)
            
            print(f"📊 DB検索期間: {start_datetime} 〜 {end_datetime}")
            
            # データベースから複数ユーザーの予定を一括取得
            events_by_email = calendar_repository.get_multiple_users_calendar_events(
                db_session, 
                member_emails, 
                start_datetime, 
                end_datetime
            )
            
            # MeetingService用の形式に変換
            all_busy_times = {}
            
            for email in member_emails:
                busy_times = []
                db_events = events_by_email.get(email, [])
                
                for event in db_events:
                    # 終日イベントは除外
                    if not event.get('is_all_day', False):
                        start_dt = event['start_datetime']
                        end_dt = event['end_datetime']
                        
                        # タイムゾーンを日本時間に統一
                        if start_dt.tzinfo is None:
                            start_dt = start_dt.replace(tzinfo=self.timezone)
                        if end_dt.tzinfo is None:
                            end_dt = end_dt.replace(tzinfo=self.timezone)
                        
                        busy_times.append({
                            'start': start_dt,
                            'end': end_dt,
                            'title': event.get('title', '予定あり')
                        })
                
                all_busy_times[email] = busy_times
                print(f"   📅 {email}: {len(busy_times)}件の予定をDBから取得")
            
            return all_busy_times
            
        except Exception as e:
            print(f"❌ DB予定取得エラー: {e}")
            # エラーの場合は全員空きとして扱う
            return {email: [] for email in member_emails}
    
    def _calculate_available_slots(
        self,
        all_busy_times: Dict[str, List[Dict]],
        start_date: str,
        end_date: str,
        start_time: str,
        end_time: str,
        duration_minutes: int
    ) -> List[Dict]:
        """
        全メンバーの空き時間を計算
        """
        available_slots = []
        
        # 検索期間の各日をチェック
        current_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        while current_date <= end_date_obj:
            # 土日は除外（オプション）
            if current_date.weekday() < 5:  # 0=月曜, 6=日曜
                daily_slots = self._find_daily_available_slots(
                    all_busy_times,
                    current_date,
                    start_time,
                    end_time,
                    duration_minutes
                )
                available_slots.extend(daily_slots)
            
            current_date += timedelta(days=1)
        
        return available_slots
    
    def _find_daily_available_slots(
        self,
        all_busy_times: Dict[str, List[Dict]],
        date: object,
        start_time: str,
        end_time: str,
        duration_minutes: int
    ) -> List[Dict]:
        """
        指定された日の空き時間スロットを検索
        """
        slots = []
        
        # その日の開始・終了時間を設定
        start_hour, start_minute = map(int, start_time.split(':'))
        end_hour, end_minute = map(int, end_time.split(':'))
        
        day_start = datetime.combine(date, time(start_hour, start_minute))
        day_end = datetime.combine(date, time(end_hour, end_minute))
        
        # ローカライズ
        day_start = self.timezone.localize(day_start)
        day_end = self.timezone.localize(day_end)
        
        # その日の全メンバーの予定をマージ
        all_busy_periods = []
        for email, busy_times in all_busy_times.items():
            for busy in busy_times:
                if busy['start'].date() == date or busy['end'].date() == date:
                    # その日に重複する部分のみを抽出
                    overlap_start = max(busy['start'], day_start)
                    overlap_end = min(busy['end'], day_end)
                    
                    if overlap_start < overlap_end:
                        all_busy_periods.append({
                            'start': overlap_start,
                            'end': overlap_end
                        })
        
        # 重複する予定をマージ
        merged_busy = self._merge_overlapping_periods(all_busy_periods)
        
        # 空き時間を計算
        current_time = day_start
        duration_delta = timedelta(minutes=duration_minutes)
        
        for busy_period in sorted(merged_busy, key=lambda x: x['start']):
            # 予定の前に空き時間があるかチェック
            if current_time + duration_delta <= busy_period['start']:
                # 30分刻みで空き時間スロットを生成
                slot_time = current_time
                while slot_time + duration_delta <= busy_period['start']:
                    slots.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'date_str': date.strftime('%Y年%m月%d日 (%a)'),
                        'start_time': slot_time.strftime('%H:%M'),
                        'end_time': (slot_time + duration_delta).strftime('%H:%M'),
                        'start_datetime': slot_time.isoformat(),
                        'end_datetime': (slot_time + duration_delta).isoformat()
                    })
                    slot_time += timedelta(minutes=30)  # 30分刻み
            
            current_time = max(current_time, busy_period['end'])
        
        # 最後の予定の後に空き時間があるかチェック
        if current_time + duration_delta <= day_end:
            slot_time = current_time
            while slot_time + duration_delta <= day_end:
                slots.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'date_str': date.strftime('%Y年%m月%d日 (%a)'),
                    'start_time': slot_time.strftime('%H:%M'),
                    'end_time': (slot_time + duration_delta).strftime('%H:%M'),
                    'start_datetime': slot_time.isoformat(),
                    'end_datetime': (slot_time + duration_delta).isoformat()
                })
                slot_time += timedelta(minutes=30)
        
        return slots
    
    def _merge_overlapping_periods(self, periods: List[Dict]) -> List[Dict]:
        """
        重複する時間帯をマージ
        """
        if not periods:
            return []
        
        # 開始時間でソート
        sorted_periods = sorted(periods, key=lambda x: x['start'])
        merged = [sorted_periods[0]]
        
        for current in sorted_periods[1:]:
            last_merged = merged[-1]
            
            # 重複または隣接している場合はマージ
            if current['start'] <= last_merged['end']:
                last_merged['end'] = max(last_merged['end'], current['end'])
            else:
                merged.append(current)
        
        return merged

    def validate_search_parameters(
        self,
        member_emails: List[str],
        start_date: str,
        end_date: str,
        start_time: str,
        end_time: str,
        duration_minutes: int
    ) -> bool:
        """検索パラメータの妥当性チェック"""
        try:
            # メンバー数チェック
            if not member_emails or len(member_emails) < 1:
                raise HTTPException(status_code=400, detail="参加者を選択してください")
            
            if len(member_emails) > 20:  # 最大20名まで
                raise HTTPException(status_code=400, detail="参加者は20名以下にしてください")
            
            # 日付フォーマットチェック
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="日付形式が正しくありません (YYYY-MM-DD)")
            
            # 日付範囲チェック
            if start_dt > end_dt:
                raise HTTPException(status_code=400, detail="開始日は終了日より前にしてください")
            
            # 期間制限（最大3ヶ月）
            if (end_dt - start_dt).days > 90:
                raise HTTPException(status_code=400, detail="検索期間は3ヶ月以内にしてください")
            
            # 時間フォーマットチェック
            try:
                start_h, start_m = map(int, start_time.split(':'))
                end_h, end_m = map(int, end_time.split(':'))
            except (ValueError, AttributeError):
                raise HTTPException(status_code=400, detail="時間形式が正しくありません (HH:MM)")
            
            # 時間範囲チェック
            if not (0 <= start_h <= 23 and 0 <= start_m <= 59):
                raise HTTPException(status_code=400, detail="開始時間が無効です")
            
            if not (0 <= end_h <= 23 and 0 <= end_m <= 59):
                raise HTTPException(status_code=400, detail="終了時間が無効です")
            
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            
            if start_minutes >= end_minutes:
                raise HTTPException(status_code=400, detail="開始時間は終了時間より前にしてください")
            
            # ミーティング時間チェック
            if not (15 <= duration_minutes <= 480):  # 15分〜8時間
                raise HTTPException(status_code=400, detail="ミーティング時間は15分〜8時間の範囲で指定してください")
            
            # 時間枠がミーティング時間より短い場合
            available_minutes = end_minutes - start_minutes
            if available_minutes < duration_minutes:
                raise HTTPException(status_code=400, detail="指定時間帯がミーティング時間より短すぎます")
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ パラメータ検証エラー: {e}")
            raise HTTPException(status_code=400, detail="検索パラメータが無効です")
    
    def get_member_schedule_summary(
        self,
        member_schedules: Dict[str, List[Dict]],
        date: str,
        start_time: str,
        duration_minutes: int
    ) -> Dict[str, Dict]:
        """指定時間の各メンバーの予定サマリーを取得"""
        try:
            # 指定時間の範囲を計算
            slot_start = datetime.strptime(f"{date} {start_time}", '%Y-%m-%d %H:%M')
            slot_end = slot_start + timedelta(minutes=duration_minutes)
            
            summary = {}
            
            for email, events in member_schedules.items():
                member_summary = {
                    'has_conflict': False,
                    'conflicting_events': [],
                    'status': 'available'
                }
                
                for event in events:
                    try:
                        event_start = datetime.fromisoformat(event['start_datetime'].replace('Z', '+00:00'))
                        event_end = datetime.fromisoformat(event['end_datetime'].replace('Z', '+00:00'))
                        
                        # 時間が重複するかチェック
                        if event_start < slot_end and event_end > slot_start:
                            member_summary['has_conflict'] = True
                            member_summary['status'] = 'busy'
                            member_summary['conflicting_events'].append({
                                'title': event['title'],
                                'start_time': event['start_time'],
                                'end_time': event['end_time']
                            })
                    except (KeyError, ValueError, TypeError) as e:
                        print(f"⚠️ イベント解析エラー ({email}): {e}")
                        continue
                
                summary[email] = member_summary
            
            return summary
            
        except Exception as e:
            print(f"❌ スケジュールサマリー取得エラー: {e}")
            return {}
    
    def format_meeting_slots(self, available_slots: List[Dict]) -> List[MeetingSlot]:
        """利用可能スロットをMeetingSlotエンティティに変換"""
        meeting_slots = []
        
        for slot in available_slots:
            try:
                meeting_slot = MeetingSlot(
                    date=slot['date'],
                    start_time=slot['start_time'],
                    end_time=slot['end_time'],
                    start_datetime=datetime.fromisoformat(slot['start_datetime'].replace('Z', '+00:00')),
                    end_datetime=datetime.fromisoformat(slot['end_datetime'].replace('Z', '+00:00')),
                    duration_minutes=slot.get('duration_minutes', 0),
                    available_members=slot.get('available_members', []),
                    busy_members=slot.get('busy_members', [])
                )
                
                meeting_slots.append(meeting_slot)
                
            except (KeyError, ValueError, TypeError) as e:
                print(f"⚠️ スロット変換エラー: {e}")
                continue
        
        return meeting_slots

# グローバルインスタンス
meeting_service = MeetingService()
