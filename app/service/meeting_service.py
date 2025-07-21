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
    
    def create_meeting_event(
        self,
        credentials: Dict,
        title: str,
        start_datetime: datetime,
        end_datetime: datetime,
        attendee_emails: List[str],
        description: str = ""
    ) -> Dict:
        """
        Google Calendarにミーティングイベントを作成
        
        Args:
            credentials: ユーザーのGoogle認証情報
            title: ミーティングタイトル
            start_datetime: 開始時刻
            end_datetime: 終了時刻
            attendee_emails: 参加者のメールアドレスリスト
            description: ミーティング説明
        
        Returns:
            作成されたイベント情報
        """
        try:
            print(f"🔍 ミーティングイベント作成開始:")
            print(f"   タイトル: {title}")
            print(f"   開始時刻: {start_datetime}")
            print(f"   終了時刻: {end_datetime}")
            print(f"   参加者: {len(attendee_emails)}名")
            
            # 認証情報の詳細をデバッグ出力
            print(f"🔍 認証情報確認:")
            print(f"   token: {'あり' if credentials.get('token') else 'なし'}")
            print(f"   refresh_token: {'あり' if credentials.get('refresh_token') else 'なし'}")
            print(f"   token_uri: {credentials.get('token_uri', 'なし')}")
            print(f"   client_id: {'あり' if credentials.get('client_id') else 'なし'}")
            print(f"   client_secret: {'あり' if credentials.get('client_secret') else 'なし'}")
            print(f"   scopes: {credentials.get('scopes', 'なし')}")
            
            # 必須フィールドの確認
            required_fields = ['token', 'client_id', 'client_secret']
            missing_fields = [field for field in required_fields if not credentials.get(field)]
            
            if missing_fields:
                error_msg = f"認証情報に必須フィールドが不足: {', '.join(missing_fields)}"
                print(f"❌ {error_msg}")
                raise HTTPException(status_code=401, detail=error_msg)
            
            # 認証情報からCredentialsオブジェクトを作成
            creds = Credentials(
                token=credentials['token'],
                refresh_token=credentials.get('refresh_token'),
                token_uri=credentials.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=credentials.get('client_id'),
                client_secret=credentials.get('client_secret'),
                scopes=credentials.get('scopes')
            )
            
            # Google Calendar APIサービスを構築
            service = build('calendar', 'v3', credentials=creds)
            
            # イベント作成用のボディを準備
            event_body = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
                'attendees': [{'email': email} for email in attendee_emails],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1日前
                        {'method': 'popup', 'minutes': 10},       # 10分前
                    ],
                },
                'sendNotifications': True,  # 参加者に通知を送信
            }
            
            # イベントを作成
            event = service.events().insert(
                calendarId='primary',
                body=event_body,
                sendNotifications=True
            ).execute()
            
            print(f"✅ ミーティングイベント作成成功:")
            print(f"   イベントID: {event['id']}")
            print(f"   HTMLリンク: {event.get('htmlLink', 'N/A')}")
            
            return {
                'event_id': event['id'],
                'html_link': event.get('htmlLink'),
                'status': 'created',
                'title': title,
                'start_datetime': start_datetime.isoformat(),
                'end_datetime': end_datetime.isoformat(),
                'attendees': attendee_emails
            }
            
        except Exception as e:
            print(f"❌ ミーティングイベント作成エラー: {e}")
            raise HTTPException(status_code=500, detail=f"ミーティングの作成に失敗しました: {str(e)}")
    
    def find_available_times(
        self,
        db: Session,
        member_emails: List[str],
        start_date: str,
        end_date: str,
        start_time: str,
        end_time: str,
        duration_minutes: int,
        member_credentials: Dict[str, dict] = None,
        current_user_email: str = None
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
            # メンバーの予定を取得（データベース + Google Calendar API）
            all_busy_times = self._get_member_busy_times_enhanced(
                member_emails,
                start_date,
                end_date,
                db,
                member_credentials,
                current_user_email
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
            
            # メンバーの予定情報を整理（UTC統一）
            member_schedules = {}
            for email, busy_times in all_busy_times.items():
                member_schedules[email] = [
                    {
                        'start_datetime': busy['start'].isoformat(),  # UTC
                        'end_datetime': busy['end'].isoformat(),      # UTC
                        'start_time': busy['start'].strftime('%H:%M'),  # UTC統一
                        'end_time': busy['end'].strftime('%H:%M'),      # UTC統一
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
            # ユーザー入力の日付をJST（日本時間）として解釈
            jst_start_date = datetime.strptime(start_date, '%Y-%m-%d')
            jst_end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
            # JSTの日付範囲を設定（その日の00:00から翌日の00:00まで）
            jst_start_datetime = self.timezone.localize(jst_start_date)
            jst_end_datetime = self.timezone.localize(jst_end_date + timedelta(days=1))
            
            # JSTからUTCに変換してDB検索用の範囲を作成
            start_datetime = jst_start_datetime.astimezone(pytz.UTC)
            end_datetime = jst_end_datetime.astimezone(pytz.UTC)
            
            print(f"📊 DB検索期間（UTC基準）: {start_datetime} 〜 {end_datetime}")
            print(f"📊 ユーザー指定期間（JST）: {jst_start_datetime} 〜 {jst_end_datetime}")
            
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
                        
                        # DBのUTCデータを確実にUTCとして扱う
                        if start_dt.tzinfo is None:
                            start_dt = pytz.UTC.localize(start_dt)
                        else:
                            start_dt = start_dt.astimezone(pytz.UTC)
                            
                        if end_dt.tzinfo is None:
                            end_dt = pytz.UTC.localize(end_dt)
                        else:
                            end_dt = end_dt.astimezone(pytz.UTC)
                        
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
    
    def _get_member_busy_times_enhanced(
        self,
        member_emails: List[str],
        start_date: str,
        end_date: str,
        db_session: Session,
        member_credentials: Dict = None,
        current_user_email: str = None
    ) -> Dict[str, List[Dict]]:
        """
        メンバーの予定を取得（Google Calendar API + データベース）
        現在ログインユーザーはGoogle Calendar APIから、他はデータベースから取得
        """
        try:
            # ユーザー入力の日付をJST（日本時間）として解釈
            jst_start_date = datetime.strptime(start_date, '%Y-%m-%d')
            jst_end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
            # JSTの日付範囲を設定（その日の00:00から翌日の00:00まで）
            jst_start_datetime = self.timezone.localize(jst_start_date)
            jst_end_datetime = self.timezone.localize(jst_end_date + timedelta(days=1))
            
            # JSTからUTCに変換
            start_datetime = jst_start_datetime.astimezone(pytz.UTC)
            end_datetime = jst_end_datetime.astimezone(pytz.UTC)
            
            print(f"🔍 Enhanced予定取得開始（UTC基準）: {start_datetime} 〜 {end_datetime}")
            print(f"🔍 ユーザー指定期間（JST）: {jst_start_datetime} 〜 {jst_end_datetime}")
            print(f"🔍 対象メンバー: {member_emails}")
            print(f"🔍 認証情報: {'あり' if member_credentials else 'なし'}")
            
            all_busy_times = {}
            
            # 現在ログインユーザーの認証情報がある場合、Google Calendar APIから直接取得
            if member_credentials and member_credentials.get('token') and current_user_email:
                current_user_data = self._get_current_user_busy_times_from_api(
                    start_datetime, end_datetime, member_credentials
                )
                if current_user_data and current_user_email in member_emails:
                    # 現在ログインユーザーのメールアドレスが対象メンバーに含まれている場合のみ適用
                    all_busy_times[current_user_email] = current_user_data
                    print(f"✅ {current_user_email}: Google Calendar APIから {len(current_user_data)}件の予定を取得")
            
            # データベースから他のメンバーの予定を取得
            db_events_by_email = calendar_repository.get_multiple_users_calendar_events(
                db_session, 
                member_emails, 
                start_datetime, 
                end_datetime
            )
            
            # データベースの結果をマージ
            for email in member_emails:
                if email not in all_busy_times:  # Google Calendar APIで取得済みでない場合
                    busy_times = []
                    db_events = db_events_by_email.get(email, [])
                    
                    for event in db_events:
                        # 終日イベントは除外
                        if not event.get('is_all_day', False):
                            start_dt = event['start_datetime']
                            end_dt = event['end_datetime']
                            
                            # DBのUTCデータを確実にUTCとして扱う
                            if start_dt.tzinfo is None:
                                start_dt = pytz.UTC.localize(start_dt)
                            else:
                                start_dt = start_dt.astimezone(pytz.UTC)
                                
                            if end_dt.tzinfo is None:
                                end_dt = pytz.UTC.localize(end_dt)
                            else:
                                end_dt = end_dt.astimezone(pytz.UTC)
                            
                            busy_times.append({
                                'start': start_dt,
                                'end': end_dt,
                                'title': event.get('title', '予定あり')
                            })
                    
                    all_busy_times[email] = busy_times
                    print(f"   📅 {email}: {len(busy_times)}件の予定をDBから取得")
            
            return all_busy_times
            
        except Exception as e:
            print(f"❌ Enhanced予定取得エラー: {e}")
            # エラーの場合は従来の方法にフォールバック
            return self._get_member_busy_times_from_db(member_emails, start_date, end_date, db_session)
    
    def _get_current_user_busy_times_from_api(
        self,
        start_datetime: datetime,
        end_datetime: datetime,
        credentials: Dict
    ) -> List[Dict]:
        """
        現在ログインユーザーのGoogle Calendar APIから予定を直接取得
        """
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            print(f"🔄 Google Calendar APIから予定取得開始...")
            
            # 認証情報からCredentialsオブジェクトを作成
            creds = Credentials(
                token=credentials['token'],
                refresh_token=credentials.get('refresh_token'),
                token_uri=credentials.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=credentials.get('client_id'),
                client_secret=credentials.get('client_secret'),
                scopes=credentials.get('scopes')
            )
            
            # Google Calendar APIサービスを構築
            service = build('calendar', 'v3', credentials=creds)
            
            # イベントを取得（UTC時刻で検索）
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_datetime.isoformat(),
                timeMax=end_datetime.isoformat(),
                maxResults=250,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            print(f"✅ Google Calendar APIから {len(events)}件のイベントを取得")
            
            # MeetingService形式に変換（UTC統一）
            busy_times = []
            for event in events:
                try:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    end = event['end'].get('dateTime', event['end'].get('date'))
                    
                    # 終日イベントは除外
                    if 'dateTime' not in event['start']:
                        continue
                    
                    # 日時をパース
                    if start.endswith('Z'):
                        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    else:
                        start_dt = datetime.fromisoformat(start)
                        end_dt = datetime.fromisoformat(end)
                    
                    # UTC統一で保持（JST変換はしない）
                    start_dt = start_dt.astimezone(pytz.UTC)
                    end_dt = end_dt.astimezone(pytz.UTC)
                    
                    busy_times.append({
                        'start': start_dt,
                        'end': end_dt,
                        'title': event.get('summary', '予定あり')
                    })
                    
                except Exception as e:
                    print(f"⚠️ イベント解析エラー: {e}")
                    continue
            
            print(f"✅ {len(busy_times)}件の有効な予定を変換完了（UTC統一）")
            return busy_times
            
        except Exception as e:
            print(f"❌ Google Calendar API取得エラー: {e}")
            return []
    
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
        空き時間は30分区切り（:00, :30）から開始
        """
        slots = []
        
        # ユーザー指定の時間をJSTとして解釈
        start_hour, start_minute = map(int, start_time.split(':'))
        end_hour, end_minute = map(int, end_time.split(':'))
        
        # JST基準での日時範囲を作成
        jst_day_start = datetime.combine(date, time(start_hour, start_minute))
        jst_day_end = datetime.combine(date, time(end_hour, end_minute))
        
        # JSTでローカライズしてからUTCに変換
        jst_day_start = self.timezone.localize(jst_day_start)
        jst_day_end = self.timezone.localize(jst_day_end)
        
        # UTC範囲に変換
        day_start = jst_day_start.astimezone(pytz.UTC)
        day_end = jst_day_end.astimezone(pytz.UTC)
        
        print(f"🕐 空き時間計算 {date}: JST {start_time}-{end_time} → UTC {day_start.strftime('%H:%M')}-{day_end.strftime('%H:%M')}")
        
        # その日の全メンバーの予定をマージ（UTC基準で処理）
        all_busy_periods = []
        for email, busy_times in all_busy_times.items():
            for busy in busy_times:
                # UTC基準で日付範囲内かチェック
                busy_start_utc = busy['start']
                busy_end_utc = busy['end']
                
                # その日のUTC範囲と重複する部分のみを抽出
                overlap_start = max(busy_start_utc, day_start)
                overlap_end = min(busy_end_utc, day_end)
                
                if overlap_start < overlap_end:
                    all_busy_periods.append({
                        'start': overlap_start,
                        'end': overlap_end
                    })
        
        # 重複する予定をマージ
        merged_busy = self._merge_overlapping_periods(all_busy_periods)
        
        # 空き時間を計算（UTC基準）
        current_time = day_start
        duration_delta = timedelta(minutes=duration_minutes)
        
        for busy_period in sorted(merged_busy, key=lambda x: x['start']):
            # 予定の前に空き時間があるかチェック
            if current_time + duration_delta <= busy_period['start']:
                # 30分区切りから開始するように調整（UTC基準）
                slot_time = self._round_to_next_30min_slot(current_time)
                
                # 30分刻みで空き時間スロットを生成
                while slot_time + duration_delta <= busy_period['start']:
                    # UTC統一：全ての時刻をUTCで返す
                    
                    slots.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'date_str': date.strftime('%Y年%m月%d日 (%a)'),
                        'start_time': slot_time.strftime('%H:%M'),  # UTC統一
                        'end_time': (slot_time + duration_delta).strftime('%H:%M'),  # UTC統一
                        'start_datetime': slot_time.isoformat(),  # UTC
                        'end_datetime': (slot_time + duration_delta).isoformat()  # UTC
                    })
                    slot_time += timedelta(minutes=30)  # 30分刻み
            
            current_time = max(current_time, busy_period['end'])
        
        # 最後の予定の後に空き時間があるかチェック
        if current_time + duration_delta <= day_end:
            # 30分区切りから開始するように調整（UTC基準）
            slot_time = self._round_to_next_30min_slot(current_time)
            
            while slot_time + duration_delta <= day_end:
                # UTC統一：全ての時刻をUTCで返す
                
                slots.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'date_str': date.strftime('%Y年%m月%d日 (%a)'),
                    'start_time': slot_time.strftime('%H:%M'),  # UTC統一
                    'end_time': (slot_time + duration_delta).strftime('%H:%M'),  # UTC統一
                    'start_datetime': slot_time.isoformat(),  # UTC
                    'end_datetime': (slot_time + duration_delta).isoformat()  # UTC
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

    def _round_to_next_30min_slot(self, dt: datetime) -> datetime:
        """
        時刻を次の30分区切り（:00, :30）に切り上げ
        例: 10:25 → 10:30, 10:55 → 11:00
        """
        minute = dt.minute
        if minute == 0 or minute == 30:
            return dt  # 既に30分区切りの場合はそのまま
        elif minute < 30:
            # 30分に切り上げ
            return dt.replace(minute=30, second=0, microsecond=0)
        else:
            # 次の時間の00分に切り上げ
            next_hour = dt + timedelta(hours=1)
            return next_hour.replace(minute=0, second=0, microsecond=0)

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
